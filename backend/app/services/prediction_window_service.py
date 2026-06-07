"""
prediction_window_service.py — Determines whether the post-qualifying
prediction window is open for a given race.

States:
    pre_quali     — Quali hasn't ended yet. Window not open.
    window_open   — Quali ended, race lockout not reached. Predictions accepted.
    locked        — Within 6h of race start, or race has started. No writes.
    race_finished — Race is over. Read-only, awaiting scoring.

Notes on FastF1 schedule columns:
    Session4DateUtc = qualifying session START time
    Session5DateUtc = race START time

    We add QUALI_DURATION_MIN to Session4 to estimate quali END.
    Lockout threshold = race_start - LOCKOUT_HOURS.
"""

from datetime import datetime, timedelta, timezone
import fastf1
import pandas as pd

QUALI_DURATION_MIN = 75    # 60 min session + 15 min buffer for delays
LOCKOUT_HOURS      = 6     # Lock predictions 6h before race start
RACE_DURATION_MIN  = 150   # 2h race + 30 min buffer for end-of-race state


def _parse_utc(value) -> datetime | None:
    """Convert a FastF1 schedule timestamp to a tz-aware UTC datetime."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if hasattr(value, 'to_pydatetime'):
        value = value.to_pydatetime()
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    return None


def get_window_state(year: int, round_num: int) -> dict:
    """
    Returns a dict describing the current prediction window state.

    {
        'state':         'pre_quali' | 'window_open' | 'locked' | 'race_finished',
        'quali_end':     ISO string or None,
        'lockout_at':    ISO string or None,
        'race_start':    ISO string or None,
        'seconds_until_open':   int or None,
        'seconds_until_lock':   int or None,
        'race_name':     str or None,
        'error':         str (only if something went wrong),
    }
    """
    try:
        schedule = fastf1.get_event_schedule(year, include_testing=False)
    except Exception as e:
        return {'state': 'pre_quali', 'error': f'Schedule unavailable: {e}'}

    event_row = schedule[schedule['RoundNumber'] == round_num]
    if event_row.empty:
        return {'state': 'pre_quali', 'error': f'Round {round_num} not in {year} schedule'}

    event = event_row.iloc[0]

    quali_start = _parse_utc(event.get('Session4DateUtc'))
    race_start  = _parse_utc(event.get('Session5DateUtc'))

    if not quali_start or not race_start:
        return {'state': 'pre_quali', 'error': 'Session times not available yet'}

    quali_end  = quali_start + timedelta(minutes=QUALI_DURATION_MIN)
    lockout_at = race_start  - timedelta(hours=LOCKOUT_HOURS)
    race_end   = race_start  + timedelta(minutes=RACE_DURATION_MIN)
    now        = datetime.now(timezone.utc)

    if now < quali_end:
        state = 'pre_quali'
    elif now < lockout_at:
        state = 'window_open'
    elif now < race_end:
        state = 'locked'
    else:
        state = 'race_finished'

    return {
        'state':              state,
        'quali_end':          quali_end.isoformat(),
        'lockout_at':         lockout_at.isoformat(),
        'race_start':         race_start.isoformat(),
        'seconds_until_open': max(0, int((quali_end  - now).total_seconds())) if state == 'pre_quali'   else 0,
        'seconds_until_lock': max(0, int((lockout_at - now).total_seconds())) if state == 'window_open' else 0,
        'race_name':          event.get('EventName'),
    }


def can_accept_predictions(year: int, round_num: int) -> tuple[bool, str]:
    """
    Convenience for routes — returns (allowed, reason_if_blocked).
    """
    info = get_window_state(year, round_num)

    if info.get('error'):
        return False, info['error']

    state = info['state']
    if state == 'window_open':
        return True, ''
    if state == 'pre_quali':
        return False, 'Predictions open after qualifying ends.'
    if state == 'locked':
        return False, 'Predictions are locked. Race lockout reached.'
    return False, 'Race has finished. Predictions are no longer accepted.'