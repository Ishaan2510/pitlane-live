from flask import Blueprint, jsonify, request
from app.models import db, Prediction, User, Race
from app.routes.users import token_required, optional_token

bp = Blueprint('predictions', __name__, url_prefix='/api')

VALID_ACTIONS = {'pit_soft', 'pit_medium', 'pit_hard', 'stay_out'}

@bp.route('/predictions', methods=['POST'])
@optional_token
def create_prediction(current_user):
    # Must be logged in to predict
    if not current_user:
        return jsonify({'error': 'Login required to make predictions'}), 401

    data = request.get_json(silent=True) or {}
    driver = (data.get('driver') or '').strip().upper()
    action = data.get('action')
    try:
        confidence = int(data.get('confidence'))
        lap        = int(data.get('lap') or 0)
    except (TypeError, ValueError):
        return jsonify({'error': 'confidence and lap must be integers'}), 400

    if not driver or action not in VALID_ACTIONS or not (1 <= confidence <= 100) or lap < 0:
        return jsonify({'error': 'driver, a valid action and confidence 1-100 are required'}), 400

    mode = data.get('mode') or 'sim'
    if mode not in ('sim', 'live'):
        return jsonify({'error': 'mode must be "sim" or "live"'}), 400
    try:
        year      = int(data['year'])  if data.get('year')  is not None else None
        round_num = int(data['round']) if data.get('round') is not None else None
    except (TypeError, ValueError):
        return jsonify({'error': 'year and round must be integers'}), 400
    if mode == 'live' and (year is None or round_num is None):
        return jsonify({'error': 'year and round are required for live predictions'}), 400

    race_id = data.get('raceId')
    race = Race.query.get(race_id) if race_id else None

    prediction = Prediction(
        user_id=current_user.id,
        race_id=race.id if race else None,
        year=year,
        round_num=round_num,
        mode=mode,
        driver_name=driver,
        action=action,
        predicted_lap=lap,
        confidence=confidence,
        status='pending'
    )

    db.session.add(prediction)
    db.session.commit()

    potential_points = int(confidence * 1.5)

    return jsonify({
        'success': True,
        'points': potential_points,
        'prediction': prediction.to_dict()
    }), 201

@bp.route('/predictions/race/<int:race_id>', methods=['GET'])
def get_race_predictions(race_id):
    predictions = Prediction.query.filter_by(race_id=race_id).all()
    return jsonify([p.to_dict() for p in predictions])

@bp.route('/predictions/mine', methods=['GET'])
@token_required
def get_my_predictions(current_user):
    predictions = Prediction.query.filter_by(user_id=current_user.id)\
        .order_by(Prediction.created_at.desc()).limit(50).all()
    return jsonify([p.to_dict() for p in predictions])