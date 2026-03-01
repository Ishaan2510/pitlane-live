"""
scoring_service.py — Prediction scoring engine for Pitlane Live.

Called after a race weekend ends to:
  1. Build a pit stop registry from the cached FastF1 processed JSON
  2. Evaluate every pending prediction as correct / wrong
  3. Award points and update user total_score / accuracy_rate

Usage (from Flask shell or a cron job):
    from app.services.scoring_service import score_race
    result = score_race(2026, 1)   # year, round
    print(result)

Or via the API endpoint:
    curl -X POST https://pitlane-live-three.vercel.app/api/scoring/score-race \\
         -H "Content-Type: application/json" \\
         -H "X-Admin-Key: <ADMIN_KEY from .env>" \\
         -d '{"year": 2026, "round": 1}'
"""

import json
import os
from pathlib import Path

# These imports work when called inside a Flask app context
from app.models import db, Prediction, User
from app.services.fastf1_service import fastf1_service

# ─── Constants ────────────────────────────────────────────────────────────────

LAP_WINDOW = 2   # ±N laps tolerance for pit stop predictions

COMPOUND_MAP = {
    'pit_soft':   'SOFT',
    'pit_medium': 'MEDIUM',
    'pit_hard':   'HARD',
}

POINTS_EXACT_LAP   = 1.25   # multiplier for exact lap prediction
POINTS_CLOSE_LAP   = 1.10   # multiplier for 1 lap off
POINTS_BASE_FACTOR = 1.5    # confidence × this = base points


# ─── Pit stop registry ────────────────────────────────────────────────────────

def build_pit_registry(race_data: dict) -> dict:
    """
    Scan the processed race JSON and return a per-driver pit stop log.

    FastF1 semantics:
        pit_in  = True on lap N  → driver entered pits at the end of lap N
        pit_out = True on lap N  → driver exited pits and started lap N on new tyres

    Returns:
        {
            'VER': [{'lap_in': 20, 'new_compound': 'MEDIUM'}, ...],
            'HAM': [...],
            ...
        }
    """
    # First pass: collect all pit_in laps and pit_out laps per driver
    pit_ins  = {}   # driver -> [lap_number, ...]
    pit_outs = {}   # driver -> {lap_number: new_compound}

    for lap in race_data.get('laps', []):
        lap_num = lap['lap_number']
        for driver in lap.get('drivers', []):
            code = driver['driver'].upper()

            if driver.get('pit_in'):
                pit_ins.setdefault(code, []).append(lap_num)

            if driver.get('pit_out'):
                compound = (driver.get('compound') or 'UNKNOWN').upper()
                pit_outs.setdefault(code, {})[lap_num] = compound

    # Second pass: pair each pit_in with the new compound from the pit_out lap
    registry = {}
    for code, laps_in in pit_ins.items():
        registry[code] = []
        driver_pit_outs = pit_outs.get(code, {})

        for lap_in in laps_in:
            # pit_out is normally lap_in + 1, but can be +2 on very slow stops
            new_compound = (
                driver_pit_outs.get(lap_in + 1)
                or driver_pit_outs.get(lap_in + 2)
                or driver_pit_outs.get(lap_in)      # same-lap edge case
                or 'UNKNOWN'
            )
            registry[code].append({
                'lap_in':       lap_in,
                'new_compound': new_compound,
            })

    return registry


def get_race_drivers(race_data: dict) -> set:
    """Return the set of all driver codes that appear in the race."""
    drivers = set()
    for lap in race_data.get('laps', []):
        for driver in lap.get('drivers', []):
            drivers.add(driver['driver'].upper())
    return drivers


# ─── Prediction evaluation ────────────────────────────────────────────────────

def evaluate_prediction(pred: 'Prediction', pit_registry: dict) -> dict:
    """
    Returns {'correct': bool, 'lap_diff': int|None}

    lap_diff is the absolute difference between the predicted lap and the actual
    pit lap — used for the accuracy bonus. None if lap was unspecified (lap=0).
    """
    driver     = pred.driver_name.upper()
    action     = pred.action
    pred_lap   = pred.predicted_lap   # 0 means "no specific lap"
    driver_pits = pit_registry.get(driver, [])

    # ── Pit stop predictions ──────────────────────────────────────────────────
    if action in COMPOUND_MAP:
        target = COMPOUND_MAP[action]

        if pred_lap == 0:
            # No lap specified: just check if the driver pitted on this compound at all
            for pit in driver_pits:
                if pit['new_compound'] == target:
                    return {'correct': True, 'lap_diff': None}
            return {'correct': False, 'lap_diff': None}

        else:
            # Check within the lap window
            for pit in driver_pits:
                diff = abs(pit['lap_in'] - pred_lap)
                if diff <= LAP_WINDOW and pit['new_compound'] == target:
                    return {'correct': True, 'lap_diff': diff}
            return {'correct': False, 'lap_diff': None}

    # ── Stay-out predictions ──────────────────────────────────────────────────
    elif action == 'stay_out':
        if pred_lap == 0:
            # Correct if driver made ZERO pit stops during the whole race
            return {'correct': len(driver_pits) == 0, 'lap_diff': None}
        else:
            # Correct if driver did NOT pit within the window around predicted_lap
            for pit in driver_pits:
                if abs(pit['lap_in'] - pred_lap) <= LAP_WINDOW:
                    return {'correct': False, 'lap_diff': None}
            return {'correct': True, 'lap_diff': None}

    # Unknown action type
    return {'correct': False, 'lap_diff': None}


def calculate_points(confidence: int, lap_diff) -> int:
    """
    Points = confidence × 1.5, adjusted for how close the lap prediction was.

    lap_diff = None  → base points (no lap bonus/penalty)
    lap_diff = 0     → +25% (exact lap)
    lap_diff = 1     → +10% (one lap off)
    lap_diff = 2     → base points (within window but no bonus)
    """
    base = confidence * POINTS_BASE_FACTOR

    if lap_diff is None:
        multiplier = 1.0
    elif lap_diff == 0:
        multiplier = POINTS_EXACT_LAP
    elif lap_diff == 1:
        multiplier = POINTS_CLOSE_LAP
    else:
        multiplier = 1.0

    return int(base * multiplier)


# ─── User score aggregation ───────────────────────────────────────────────────

def update_user_scores():
    """
    Recompute total_score and accuracy_rate for every user from their predictions.
    Called after all predictions have been marked correct/wrong.
    """
    users = User.query.all()
    for user in users:
        all_preds    = user.predictions
        scored       = [p for p in all_preds if p.status in ('correct', 'wrong')]
        correct      = [p for p in scored    if p.status == 'correct']

        user.total_score   = sum(p.points_earned for p in all_preds)
        user.accuracy_rate = (
            round(len(correct) / len(scored) * 100, 1)
            if scored else 0.0
        )

    db.session.commit()
    return len(users)


# ─── Main entry point ─────────────────────────────────────────────────────────

def score_race(year: int, round_num: int) -> dict:
    """
    Score all pending predictions against a completed FastF1 race.

    Args:
        year:      e.g. 2026
        round_num: e.g. 1  (Australian GP)

    Returns:
        Summary dict with counts and race name.
    """
    cache_file = fastf1_service.processed_cache_dir / f"{year}_R{round_num}_processed.json"

    if not cache_file.exists():
        return {
            'error': f'Race not cached yet: {year} R{round_num}. '
                     f'Run warm_cache.py --year {year} --round {round_num} first.'
        }

    with open(cache_file) as f:
        race_data = json.load(f)

    pit_registry  = build_pit_registry(race_data)
    race_drivers  = get_race_drivers(race_data)
    race_name     = race_data.get('name', f'{year} R{round_num}')

    pending = Prediction.query.filter_by(status='pending').all()

    if not pending:
        return {
            'race':    race_name,
            'message': 'No pending predictions found.',
            'scored':  0,
        }

    tally = {'correct': 0, 'wrong': 0, 'skipped': 0}

    for pred in pending:
        driver_code = pred.driver_name.upper()

        # If the driver didn't race at all, skip (don't score)
        # This handles predictions made for a different race or a DNQ driver.
        if race_drivers and driver_code not in race_drivers:
            tally['skipped'] += 1
            continue

        result = evaluate_prediction(pred, pit_registry)

        if result['correct']:
            pred.status        = 'correct'
            pred.points_earned = calculate_points(pred.confidence, result['lap_diff'])
            tally['correct'] += 1
        else:
            pred.status        = 'wrong'
            pred.points_earned = 0
            tally['wrong'] += 1

    db.session.commit()

    users_updated = update_user_scores()

    return {
        'race':          race_name,
        'total_pending': len(pending),
        'scored':        tally['correct'] + tally['wrong'],
        'correct':       tally['correct'],
        'wrong':         tally['wrong'],
        'skipped':       tally['skipped'],
        'users_updated': users_updated,
    }