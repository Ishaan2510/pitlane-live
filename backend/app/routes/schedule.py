from flask import Blueprint, jsonify, request
import fastf1
import pandas as pd
from datetime import datetime, date, timedelta

bp = Blueprint('schedule', __name__, url_prefix='/api')


def _race_status(race_date: date, race_date_end: date = None) -> str:
    """
    Determine whether a race is completed, live, or upcoming.
    'live'      — race day (race_date itself, or within 4 hours after)
    'completed' — race date is in the past
    'upcoming'  — race date is in the future
    """
    today = date.today()

    if race_date > today:
        return 'upcoming'
    if race_date == today:
        return 'live'
    return 'completed'


@bp.route('/schedule', methods=['GET'])
def get_schedule():
    """
    Return the full F1 race calendar for a given year.
    Uses FastF1's event schedule — no database required.
    Status is computed dynamically from today's date.

    Query params:
        year  — defaults to current year
    """
    year = request.args.get('year', date.today().year, type=int)

    try:
        schedule = fastf1.get_event_schedule(year, include_testing=False)
    except Exception as e:
        return jsonify({'error': f'Could not fetch schedule: {e}'}), 500

    races = []
    next_race_set = False

    for _, event in schedule.iterrows():
        if event.get('EventFormat') == 'testing':
            continue

        round_num  = int(event['RoundNumber'])
        event_date = event['EventDate']

        if pd.isna(event_date):
            continue

        race_date = event_date.date() if hasattr(event_date, 'date') else event_date
        status    = _race_status(race_date)

        # Mark the first upcoming race as 'next'
        is_next = False
        if status == 'upcoming' and not next_race_set:
            is_next       = True
            next_race_set = True

        # Sprint weekend detection
        is_sprint = event.get('EventFormat', '') in ('sprint', 'sprint_qualifying')

        # ── Exact race start time ──────────────────────────────────────────────
        # FastF1 provides Session5DateUtc for the race session.
        # Fall back to Session5Date (local) → EventDate if not available.
        race_time_utc = None
        for col in ('Session5DateUtc', 'Session5Date'):
            val = event.get(col)
            if val is not None and not (isinstance(val, float) and pd.isna(val)):
                try:
                    if hasattr(val, 'isoformat'):
                        race_time_utc = val.isoformat()
                    else:
                        race_time_utc = str(val)
                    break
                except Exception:
                    continue

        races.append({
            'round':     round_num,
            'name':      event['EventName'],
            'location':  event['Location'],
            'country':   event['Country'],
            'date':      race_date.isoformat(),
            'race_time_utc':  race_time_utc,   # NEW — exact race start UTC
            'year':      year,
            'status':    status,
            'is_next':   is_next,
            'is_sprint': bool(is_sprint),
        })

    # If no 'next' was found (all completed), mark the last one
    if races and not any(r['is_next'] for r in races):
        for r in reversed(races):
            if r['status'] == 'completed':
                r['is_next'] = True
                break

    return jsonify(races)