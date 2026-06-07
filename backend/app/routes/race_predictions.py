"""
race_predictions.py — Post-qualifying race outcome prediction endpoints.

Endpoints:
    GET  /api/race-predictions/window/<year>/<round>     Window state + countdown
    GET  /api/race-predictions/mine/<year>/<round>       Current user's prediction
    POST /api/race-predictions/<year>/<round>            Create or update prediction
    GET  /api/race-predictions/all/<year>/<round>        All predictions (post-race only)
"""

from flask import Blueprint, jsonify, request
from datetime import datetime
from app.models import db, RacePrediction
from app.routes.users import token_required
from app.services.prediction_window_service import (
    get_window_state,
    can_accept_predictions,
)

bp = Blueprint('race_predictions', __name__, url_prefix='/api/race-predictions')


VALID_COMPOUNDS = {'SOFT', 'MEDIUM', 'HARD', 'INTERMEDIATE', 'WET'}


# ── Validation ────────────────────────────────────────────────────────────────

def _validate_payload(data: dict) -> tuple[bool, str]:
    """
    Returns (ok, error_message). Caller returns 400 on failure.

    Rules:
        - predicted_order: list of 1-10 distinct driver codes (uppercase 3-letter strings).
        - tyre_strategies: dict keyed by driver code, values are non-empty lists of
          valid compounds. Drivers MUST appear in predicted_order — no orphans.
    """
    order = data.get('predicted_order')
    if not isinstance(order, list) or not (1 <= len(order) <= 10):
        return False, 'predicted_order must be a list of 1 to 10 driver codes.'

    if len(set(order)) != len(order):
        return False, 'predicted_order contains duplicate drivers.'

    for code in order:
        if not isinstance(code, str) or len(code) != 3 or not code.isalpha():
            return False, f'Invalid driver code: {code!r}. Must be 3-letter alphabetic.'

    strategies = data.get('tyre_strategies', {})
    if not isinstance(strategies, dict):
        return False, 'tyre_strategies must be an object keyed by driver code.'

    order_set = {c.upper() for c in order}
    for code, stints in strategies.items():
        if code.upper() not in order_set:
            return False, f'Strategy for {code} but driver not in predicted_order.'
        if not isinstance(stints, list) or not stints:
            return False, f'Strategy for {code} must be a non-empty list of compounds.'
        for compound in stints:
            if compound not in VALID_COMPOUNDS:
                return False, f'Invalid compound {compound!r} for {code}.'

    return True, ''


def _normalize_payload(data: dict) -> dict:
    """Uppercase everything so storage is canonical."""
    return {
        'predicted_order': [c.upper() for c in data['predicted_order']],
        'tyre_strategies': {
            k.upper(): [s.upper() for s in v]
            for k, v in data.get('tyre_strategies', {}).items()
        },
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@bp.route('/window/<int:year>/<int:round_num>', methods=['GET'])
def get_window(year, round_num):
    """Public — anyone can check the window state."""
    return jsonify(get_window_state(year, round_num))


@bp.route('/mine/<int:year>/<int:round_num>', methods=['GET'])
@token_required
def get_my_prediction(current_user, year, round_num):
    """Returns the current user's prediction for this race, or 404 if none."""
    pred = RacePrediction.query.filter_by(
        user_id=current_user.id, year=year, round_num=round_num
    ).first()
    if not pred:
        return jsonify({'prediction': None})
    return jsonify({'prediction': pred.to_dict()})


@bp.route('/<int:year>/<int:round_num>', methods=['POST'])
@token_required
def submit_prediction(current_user, year, round_num):
    """
    Create OR update the user's prediction for this race.
    Same endpoint handles both — UPSERT semantics. Window must be open.
    """
    allowed, reason = can_accept_predictions(year, round_num)
    if not allowed:
        return jsonify({'error': reason}), 403

    data = request.get_json(silent=True) or {}
    ok, err = _validate_payload(data)
    if not ok:
        return jsonify({'error': err}), 400

    clean = _normalize_payload(data)

    pred = RacePrediction.query.filter_by(
        user_id=current_user.id, year=year, round_num=round_num
    ).first()

    if pred:
        pred.predicted_order = clean['predicted_order']
        pred.tyre_strategies = clean['tyre_strategies']
        pred.updated_at      = datetime.utcnow()
        action = 'updated'
    else:
        pred = RacePrediction(
            user_id         = current_user.id,
            year            = year,
            round_num       = round_num,
            predicted_order = clean['predicted_order'],
            tyre_strategies = clean['tyre_strategies'],
        )
        db.session.add(pred)
        action = 'created'

    db.session.commit()
    return jsonify({'action': action, 'prediction': pred.to_dict()}), 200 if action == 'updated' else 201


@bp.route('/all/<int:year>/<int:round_num>', methods=['GET'])
def get_all_predictions(year, round_num):
    """
    Public — all predictions for this race, but ONLY after lockout.
    Prevents users from copying others' predictions during the open window.
    """
    info = get_window_state(year, round_num)
    if info['state'] in ('pre_quali', 'window_open'):
        return jsonify({'error': 'Predictions are private until lockout.'}), 403

    preds = RacePrediction.query.filter_by(year=year, round_num=round_num).all()
    return jsonify([
        {
            'username':        p.user.username,
            'predicted_order': p.predicted_order,
            'tyre_strategies': p.tyre_strategies,
            'status':          p.status,
            'total_points':    p.total_points,
        }
        for p in preds
    ])

import os

ADMIN_KEY = os.getenv('ADMIN_KEY', 'pitlane-admin-2026')


@bp.route('/score/<int:year>/<int:round_num>', methods=['POST'])
def score_race(year, round_num):
    """
    Admin — score all pending race predictions for a completed race.
    Requires X-Admin-Key header.
    """
    if request.headers.get('X-Admin-Key', '') != ADMIN_KEY:
        return jsonify({'error': 'Unauthorized — X-Admin-Key required'}), 401

    from app.services.race_prediction_scoring import score_race_predictions
    result = score_race_predictions(year, round_num)

    if 'error' in result:
        return jsonify(result), 422
    return jsonify(result)