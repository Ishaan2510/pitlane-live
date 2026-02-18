from flask import Blueprint, jsonify
from app.models import db, Race

bp = Blueprint('races', __name__, url_prefix='/api')

@bp.route('/races', methods=['GET'])
def get_races():
    """Get all races"""
    races = Race.query.order_by(Race.date).all()
    return jsonify([race.to_dict() for race in races])

@bp.route('/races/<int:race_id>', methods=['GET'])
def get_race(race_id):
    """Get single race with drivers"""
    race = Race.query.get_or_404(race_id)
    return jsonify(race.to_dict(include_drivers=True))
