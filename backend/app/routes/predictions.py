from flask import Blueprint, jsonify, request
from app.models import db, Prediction, User, Race
from app.routes.users import token_required, optional_token

bp = Blueprint('predictions', __name__, url_prefix='/api')

@bp.route('/predictions', methods=['POST'])
@optional_token
def create_prediction(current_user):
    data = request.json

    # Must be logged in to predict
    if not current_user:
        return jsonify({'error': 'Login required to make predictions'}), 401

    race_id = data.get('raceId')
    race = Race.query.get(race_id) if race_id else None

    prediction = Prediction(
        user_id=current_user.id,
        race_id=race.id if race else None,
        driver_name=data['driver'],
        action=data['action'],
        predicted_lap=data.get('lap', 0),
        confidence=data['confidence'],
        status='pending'
    )

    db.session.add(prediction)
    db.session.commit()

    potential_points = int(data['confidence'] * 1.5)

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