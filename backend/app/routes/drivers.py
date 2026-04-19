from flask import Blueprint, jsonify
import requests
import time

bp = Blueprint('drivers', __name__, url_prefix='/api')

# Cache season stats for 30 minutes — Jolpica updates after each race
_cache = {'data': {}, 'ts': 0}
CACHE_TTL = 1800

JOLPICA_STANDINGS = 'https://api.jolpi.ca/ergast/f1/2026/driverStandings/'


def _fetch_season_stats() -> dict:
    """
    Fetch current 2026 driver standings from Jolpica.
    Returns dict keyed by driver code:
    {
      'VER': {'season_wins': 3, 'season_points': 75, 'season_position': 1},
      ...
    }
    """
    try:
        resp = requests.get(JOLPICA_STANDINGS, timeout=8, headers={
            'User-Agent': 'PitLaneLive/1.0'
        })
        resp.raise_for_status()
        data = resp.json()

        standings_lists = (
            data.get('MRData', {})
                .get('StandingsTable', {})
                .get('StandingsLists', [])
        )

        if not standings_lists:
            return {}

        result = {}
        for entry in standings_lists[0].get('DriverStandings', []):
            code = entry.get('Driver', {}).get('code', '').upper()
            if not code:
                continue
            result[code] = {
                'season_wins':     int(entry.get('wins', 0)),
                'season_points':   float(entry.get('points', 0)),
                'season_position': int(entry.get('position', 0)),
            }

        return result

    except Exception as e:
        print(f'[drivers] Jolpica fetch error: {e}')
        return {}


@bp.route('/drivers/season-stats', methods=['GET'])
def get_season_stats():
    """
    Return current 2026 season stats for all drivers.
    Cached for 30 minutes. Frontend overlays these on hardcoded career stats.
    """
    global _cache
    now = time.time()

    if now - _cache['ts'] > CACHE_TTL or not _cache['data']:
        fresh = _fetch_season_stats()
        if fresh:
            _cache = {'data': fresh, 'ts': now}

    if not _cache['data']:
        return jsonify({'error': 'Could not load season stats'}), 503

    return jsonify(_cache['data'])