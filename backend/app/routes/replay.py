from flask import Blueprint, jsonify, request, Response
from app.services.fastf1_service import fastf1_service
import json, time

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

@bp.route('/circuit/<int:year>/<int:race_round>', methods=['GET'])
def get_circuit_data(year, race_round):
    """Get circuit coordinates and track layout"""
    data = fastf1_service.get_circuit_data(year, race_round)
    if data:
        return jsonify(data)
    return jsonify({'error': 'Circuit data not found'}), 404

@bp.route('/weather/<int:year>/<int:race_round>', methods=['GET'])
def get_weather_data(year, race_round):
    """Get weather information"""
    data = fastf1_service.get_weather_data(year, race_round)
    if data:
        return jsonify(data)
    return jsonify({'error': 'Weather data not found'}), 404

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

@bp.route('/telemetry/<int:year>/<int:race_round>/<driver>/<int:lap_number>', methods=['GET'])
def get_driver_telemetry(year, race_round, driver, lap_number):
    """
    On-demand speed telemetry for ONE driver/lap.
    Call this when user selects a driver in the replay UI.
    Fills avg_speed / max_speed without blocking the initial load.
    """
    data = fastf1_service.get_driver_lap_telemetry(year, race_round, driver.upper(), lap_number)
    if data:
        return jsonify(data)
    return jsonify({'error': 'Telemetry not available'}), 404

@bp.route('/available-years', methods=['GET'])
def get_available_years():
    """Which years have F1 data available."""
    return jsonify({
        'years':   [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
        'default': 2024,
        'note':    '2025 data available after each race weekend concludes'
    })

# ─── Live race (OpenF1) ───────────────────────────────────────────────────────

@bp.route('/live/state', methods=['GET'])
def get_live_state():
    """
    Full live race state: positions, gaps, compounds, race control.
    Frontend polls this every 3 seconds during live mode.
    OpenF1 data is ~3-10s delayed from broadcast.
    """
    state = fastf1_service.get_live_full_state()
    return jsonify(state)

@bp.route('/live/positions', methods=['GET'])
def get_live_positions():
    session_key = request.args.get('session_key', type=int)
    return jsonify(fastf1_service.get_live_positions(session_key))

@bp.route('/live/car/<int:driver_number>', methods=['GET'])
def get_live_car_data(driver_number):
    """Live telemetry for a single driver: speed, gear, DRS, throttle, brake."""
    session_key = request.args.get('session_key', type=int)
    data = fastf1_service.get_live_car_data(session_key, driver_number)
    if data:
        return jsonify(data)
    return jsonify({'error': 'No live data'}), 404

@bp.route('/live/race-control', methods=['GET'])
def get_live_race_control():
    """Safety car, yellow flags, VSC, red flags, track limits."""
    session_key = request.args.get('session_key', type=int)
    return jsonify(fastf1_service.get_live_race_control(session_key))

@bp.route('/live/pit-stops', methods=['GET'])
def get_live_pit_stops():
    """All pit stops so far in the current session."""
    session_key = request.args.get('session_key', type=int)
    return jsonify(fastf1_service.get_live_pit_stops(session_key))

@bp.route('/live/stream', methods=['GET'])
def live_stream():
    """
    Server-Sent Events stream — frontend connects ONCE, gets updates every 3s.

    Frontend usage:
        const es = new EventSource('/api/replay/live/stream')
        es.onmessage = (e) => { const state = JSON.parse(e.data); ... }
    """
    def generate():
        while True:
            state = fastf1_service.get_live_full_state()
            yield f"data: {json.dumps(state)}\n\n"
            time.sleep(3)

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control':     'no-cache',
            'X-Accel-Buffering': 'no',    # disables nginx buffering
        }
    )
