from flask import Blueprint, jsonify, request
from app.models import db, Prediction, User, Race
from datetime import datetime

bp = Blueprint('predictions', __name__, url_prefix='/api')

@bp.route('/predictions', methods=['POST'])
def create_prediction():
    """Submit a new prediction"""
    data = request.json
    
    # For now, use a default user (we'll add auth later)
    user = User.query.first()
    if not user:
        # Create default user if none exists
        user = User(username='demo_user', email='demo@pitlane.live')
        db.session.add(user)
        db.session.commit()
    
    # Validate race exists
    race = Race.query.get(data.get('raceId'))
    if not race:
        return jsonify({'error': 'Race not found'}), 404
    
    prediction = Prediction(
        user_id=user.id,
        race_id=data['raceId'],
        driver_name=data['driver'],
        action=data['action'],
        predicted_lap=data['lap'],
        confidence=data['confidence'],
        status='pending'
    )
    
    db.session.add(prediction)
    db.session.commit()
    
    # Calculate potential points based on confidence
    potential_points = int(data['confidence'] * 1.5)
    
    return jsonify({
        'success': True,
        'points': potential_points,
        'prediction': prediction.to_dict()
    }), 201

@bp.route('/predictions/race/<int:race_id>', methods=['GET'])
def get_race_predictions(race_id):
    """Get all predictions for a race"""
    predictions = Prediction.query.filter_by(race_id=race_id).all()
    return jsonify([p.to_dict() for p in predictions])
