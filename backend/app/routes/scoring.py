"""
scoring.py — Flask routes for the prediction scoring engine.

Endpoints:
    POST /api/scoring/score-race      Trigger scoring for a completed race
    GET  /api/scoring/status          Check pending/scored prediction counts
    GET  /api/scoring/preview/<year>/<round>   Dry run — see what would be scored
"""

import os
from flask import Blueprint, jsonify, request
from app.services.scoring_service import score_race as _score_race, build_pit_registry
from app.models import Prediction
import json

bp = Blueprint('scoring', __name__, url_prefix='/api/scoring')

ADMIN_KEY = os.getenv('ADMIN_KEY', 'pitlane-admin-2026')


def _check_admin(req):
    """Return True if the request carries the correct admin key."""
    return req.headers.get('X-Admin-Key', '') == ADMIN_KEY


# ── Score a race ──────────────────────────────────────────────────────────────

@bp.route('/score-race', methods=['POST'])
def score_race():
    """
    Trigger scoring for a completed race.

    Body JSON: { "year": 2026, "round": 1 }
    Header:    X-Admin-Key: <value of ADMIN_KEY in .env>

    Example curl:
        curl -X POST https://pitlane-live-three.vercel.app/api/scoring/score-race \\
             -H "Content-Type: application/json" \\
             -H "X-Admin-Key: pitlane-admin-2026" \\
             -d '{"year": 2026, "round": 1}'
    """
    if not _check_admin(request):
        return jsonify({'error': 'Unauthorized — X-Admin-Key header required'}), 401

    data      = request.json or {}
    year      = data.get('year')
    round_num = data.get('round')

    if not year or not round_num:
        return jsonify({'error': 'Both "year" and "round" are required in the request body'}), 400

    try:
        result = _score_race(int(year), int(round_num))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    if 'error' in result:
        return jsonify(result), 422

    return jsonify(result)


# ── Status overview ───────────────────────────────────────────────────────────

@bp.route('/status', methods=['GET'])
def scoring_status():
    """
    Returns a count of predictions by status.
    Useful for checking before triggering scoring.
    No auth required — counts only, no personal data.
    """
    pending = Prediction.query.filter_by(status='pending').count()
    correct = Prediction.query.filter_by(status='correct').count()
    wrong   = Prediction.query.filter_by(status='wrong').count()

    return jsonify({
        'pending': pending,
        'correct': correct,
        'wrong':   wrong,
        'total':   pending + correct + wrong,
    })


# ── Dry-run preview ───────────────────────────────────────────────────────────

@bp.route('/preview/<int:year>/<int:round_num>', methods=['GET'])
def preview_scoring(year, round_num):
    """
    Preview what scoring would do WITHOUT committing anything to the DB.
    Shows the pit stop registry extracted from FastF1 data — useful for debugging.

    No auth required (read-only, no PII).
    """
    from app.services.fastf1_service import fastf1_service

    cache_file = fastf1_service.processed_cache_dir / f"{year}_R{round_num}_processed.json"

    if not cache_file.exists():
        return jsonify({'error': f'Race not cached: {year} R{round_num}'}), 404

    with open(cache_file) as f:
        race_data = json.load(f)

    pit_registry = build_pit_registry(race_data)
    pending_count = Prediction.query.filter_by(status='pending').count()

    return jsonify({
        'race':            race_data.get('name'),
        'total_laps':      race_data.get('total_laps'),
        'pending_to_score': pending_count,
        'pit_stops':       pit_registry,   # driver -> [{lap_in, new_compound}]
    })