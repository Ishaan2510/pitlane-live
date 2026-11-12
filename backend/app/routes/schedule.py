from flask import Blueprint, jsonify, request
import pandas as pd
from app.services.fastf1_service import get_event_schedule
from datetime import datetime, date, timedelta, timezone, time as dtime

bp = Blueprint('schedule', __name__, url_prefix='/api')

RACE_LIVE_HOURS = 3


def _race_start_utc(event, race_date: date) -> datetime:
    """Race start (Session5DateUtc) as aware UTC; noon UTC on race day if FastF1 has no time yet."""
    val = event.get('Session5DateUtc')
    if val is not None and pd.notna(val):
        ts = pd.Timestamp(val)
        ts = ts.tz_localize('UTC') if ts.tzinfo is None else ts.tz_convert('UTC')
        return ts.to_pydatetime()
    return datetime.combine(race_date, dtime(12, 0), tzinfo=timezone.utc)


def _race_status(race_start: datetime) -> str:
    """
    'upcoming'  — before race start (UTC)
    'live'      — race start to start + RACE_LIVE_HOURS
    'completed' — after that
    """
    now = datetime.now(timezone.utc)
    if now < race_start:
        return 'upcoming'
    if now < race_start + timedelta(hours=RACE_LIVE_HOURS):
        return 'live'
    return 'completed'


@bp.route('/schedule', methods=['GET'])
def get_schedule():
    """
    Return the full F1 race calendar for a given year.
    Uses FastF1's event schedule — no database required.
    Status is computed dynamically from the race start time (UTC).

    Query params:
        year  — defaults to current year
    """
    year = request.args.get('year', datetime.now(timezone.utc).year, type=int)

    try:
        schedule = get_event_schedule(year)
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
        status    = _race_status(_race_start_utc(event, race_date))

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
                    # FastF1 gives naive UTC; without a 'Z' JS parses it as local time
                    if not race_time_utc.endswith(('Z', '+00:00')):
                        race_time_utc += 'Z'
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