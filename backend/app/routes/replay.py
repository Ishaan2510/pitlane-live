from flask import Blueprint, jsonify, request
from app.services.fastf1_service import fastf1_service

bp = Blueprint('replay', __name__, url_prefix='/api/replay')

@bp.route('/available', methods=['GET'])
def get_available_races():
    """Get list of available races for replay"""
    year = request.args.get('year', 2024, type=int)
    races = fastf1_service.get_available_races(year)
    return jsonify(races)

@bp.route('/race/<int:year>/<int:race_round>', methods=['GET'])
def get_race_data(year, race_round):
    """Get full race telemetry data for replay"""
    data = fastf1_service.process_race_telemetry(year, race_round)
    if data:
        return jsonify(data)
    return jsonify({'error': 'Race not found or failed to load'}), 404

@bp.route('/summary/<int:year>/<int:race_round>', methods=['GET'])
def get_race_summary(year, race_round):
    """Get quick race summary"""
    summary = fastf1_service.get_race_summary(year, race_round)
    if summary:
        return jsonify(summary)
    return jsonify({'error': 'Race not found'}), 404

@bp.route('/lap/<int:year>/<int:race_round>/<int:lap_number>', methods=['GET'])
def get_lap_data(year, race_round, lap_number):
    """Get specific lap data"""
    race_data = fastf1_service.process_race_telemetry(year, race_round)
    if not race_data:
        return jsonify({'error': 'Race not found'}), 404
    
    if lap_number < 1 or lap_number > len(race_data['laps']):
        return jsonify({'error': 'Invalid lap number'}), 400
    
    return jsonify(race_data['laps'][lap_number - 1])
