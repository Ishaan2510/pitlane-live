from flask import Blueprint, jsonify, request
from app.services.fastf1_service import fastf1_service

bp = Blueprint('replay', __name__, url_prefix='/api/replay')

# DEPRECATED: the race, circuit, weather, summary, lap, telemetry, available*, and simulate/*
# routes below are superseded by the static files the data pipeline publishes under /data/
# (see pipeline/SCHEMA.md and frontend/src/services/data.js). The frontend no longer calls
# them. They stay until the static data is verified in production, then go away together
# with backend/fastf1_cache/processed/. The live/* routes (OpenF1) are NOT deprecated.

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
    """On-demand speed telemetry for ONE driver/lap."""
    data = fastf1_service.get_driver_lap_telemetry(year, race_round, driver.upper(), lap_number)
    if data:
        return jsonify(data)
    return jsonify({'error': 'Telemetry not available'}), 404

@bp.route('/available-years', methods=['GET'])
def get_available_years():
    """Which years have processed race data, from the processed file names."""
    years = sorted({r['year'] for r in fastf1_service.get_race_index()})
    return jsonify({
        'years':   years,
        'default': years[-1] if years else None,
    })

# ─── Live race (OpenF1) ───────────────────────────────────────────────────────

@bp.route('/live/state', methods=['GET'])
def get_live_state():
    """Full live race state, or {"status": "unavailable"}. Frontend polls this every 5 seconds."""
    state = fastf1_service.get_live_full_state()
    return jsonify(state)

@bp.route('/live/positions', methods=['GET'])
def get_live_positions():
    session_key = request.args.get('session_key', type=int)
    return jsonify(fastf1_service.get_live_positions(session_key))

@bp.route('/live/car/<int:driver_number>', methods=['GET'])
def get_live_car_data(driver_number):
    """Live telemetry for a single driver."""
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

# ─── Simulation mode ──────────────────────────────────────────────────────────

def _lap_to_live_state(race_data: dict, lap_number: int) -> dict:
    """
    Convert a cached FastF1 lap into the exact same shape that
    get_live_full_state() returns, so LiveRace.vue needs zero changes.
    """
    from datetime import datetime

    laps = race_data.get('laps', [])
    total_laps = race_data.get('total_laps', len(laps))

    # Clamp lap to valid range
    lap_number = max(1, min(lap_number, total_laps))
    lap_data   = laps[lap_number - 1] if lap_number <= len(laps) else {}
    drivers_raw = lap_data.get('drivers', [])

    drivers = []
    for i, d in enumerate(drivers_raw):
        # Detect pit stop on this lap for race_control message
        pitted = d.get('pit_in') or d.get('pit_out')

        drivers.append({
            'driver_number': i + 1,          # fake number, not needed by UI
            'driver':        d.get('driver', '???'),
            'team':          d.get('team', 'Unknown'),
            'position':      d.get('position') or (i + 1),
            'gap':           d.get('gap', 'LEADER'),
            'interval':      None,            # not in FastF1 lap data
            'compound':      d.get('compound', 'UNKNOWN'),
            'tire_age':      d.get('tire_life', 0),
        })

    # Build a fake race_control message for pit events
    pit_drivers = [
        d.get('driver') for d in drivers_raw
        if d.get('pit_in') or d.get('pit_out')
    ]
    race_control = None
    if pit_drivers:
        race_control = {
            'flag':    'PIT',
            'message': f"PIT STOP: {', '.join(pit_drivers)}"
        }

    return {
        'session_key':  f'SIM_{race_data.get("year")}_{race_data.get("round")}',
        'drivers':      drivers,
        'race_control': race_control,
        'timestamp':    datetime.utcnow().isoformat(),
        # Extra fields the frontend can use to show simulation status
        'simulated':    True,
        'sim_lap':      lap_number,
        'sim_total_laps': total_laps,
        'sim_race_name':  race_data.get('name', ''),
    }


@bp.route('/simulate/state', methods=['GET'])
def simulate_live_state():
    """
    Simulate a live race using a cached FastF1 race.
    Returns data in the exact same shape as /live/state.

    Query params:
        year   — e.g. 2025
        round  — e.g. 3
        lap    — current lap to show (frontend increments this)

    Frontend usage:
        Instead of polling /api/replay/live/state,
        poll /api/replay/simulate/state?year=2025&round=3&lap=20
    """
    year       = request.args.get('year',  2025, type=int)
    race_round = request.args.get('round', 1,    type=int)
    lap        = request.args.get('lap',   1,    type=int)

    race_data = fastf1_service.load_processed(year, race_round)
    if race_data is None:
        return jsonify({
            'error':     f'Race not cached: {year} R{race_round}',
            'simulated': True,
        }), 404

    state = _lap_to_live_state(race_data, lap)
    return jsonify(state)


@bp.route('/simulate/races', methods=['GET'])
def get_simulatable_races():
    """
    Returns list of races available for simulation
    (i.e. races that are cached and ready).
    Used by the frontend to populate the simulation picker.
    """
    return jsonify(fastf1_service.get_race_index())