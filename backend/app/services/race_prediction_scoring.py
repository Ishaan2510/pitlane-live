"""
race_prediction_scoring.py — Scores post-qualifying race predictions.

Reads the cached FastF1 processed JSON for a finished race, extracts:
  - Actual top-10 finishing order
  - Actual stint sequence per driver

Then scores every pending RacePrediction against the truth.

Position scoring (F1-style points with exact/partial credit):
    slot points       = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1]
    exact slot match  = full slot points
    ±1 slot           = 50% of slot points
    ±2 slot           = 25% of slot points
    >±2 or not in top10 = 0

Tyre scoring (segment-by-segment):
    Each segment in the user's stint list is compared positionally to the
    actual stint list for that driver:
        match    → +5
        mismatch → -2
        missing or extra segments → 0 contribution
"""

import json
from app.models import db, RacePrediction
from app.services.fastf1_service import fastf1_service

# Position scoring constants
SLOT_POINTS = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1]
EXACT_MULT  = 1.0
ONE_OFF_MULT = 0.5
TWO_OFF_MULT = 0.25

# Tyre scoring constants
TYRE_CORRECT = 5
TYRE_WRONG   = -2


# ── Extracting truth from processed race JSON ─────────────────────────────────

def extract_finishing_order(race_data: dict) -> list[str]:
    """
    Returns the top-10 finishing order as a list of driver codes.

    The processed JSON sorts drivers by position within each lap. The final
    lap's driver list is the finishing order — drivers who DNF'd drop out of
    later laps automatically.
    """
    laps = race_data.get('laps', [])
    if not laps:
        return []

    # Walk backwards from final lap to find the most complete classification.
    # The last lap a driver appears in is their final position.
    final_positions = {}
    for lap in reversed(laps):
        for driver in lap.get('drivers', []):
            code = driver['driver'].upper()
            if code not in final_positions and driver.get('position'):
                final_positions[code] = int(driver['position'])

    sorted_drivers = sorted(final_positions.items(), key=lambda kv: kv[1])
    return [code for code, _ in sorted_drivers[:10]]


def extract_stint_sequences(race_data: dict) -> dict[str, list[str]]:
    """
    Returns {driver_code: [compound1, compound2, ...]} where each compound is
    one stint. A new stint starts after a pit_out event.

    Logic:
        - Walk laps in order.
        - For each driver, the first compound seen is stint 1.
        - On pit_out=True, the compound on that lap (or the next) is the new stint.
    """
    stints = {}                # code -> list of compounds
    last_compound = {}         # code -> compound last seen (for dedup)

    for lap in race_data.get('laps', []):
        for driver in lap.get('drivers', []):
            code     = driver['driver'].upper()
            compound = (driver.get('compound') or 'UNKNOWN').upper()

            if compound == 'UNKNOWN':
                continue

            # First time we see this driver: record opening compound
            if code not in stints:
                stints[code] = [compound]
                last_compound[code] = compound
                continue

            # New stint on pit_out OR compound change without pit_in (data quirk)
            if driver.get('pit_out') and compound != last_compound[code]:
                stints[code].append(compound)
                last_compound[code] = compound
            elif compound != last_compound[code]:
                # Compound changed but no pit_out flag — treat as new stint anyway
                stints[code].append(compound)
                last_compound[code] = compound

    return stints


# ── Scoring a single prediction ───────────────────────────────────────────────

def score_positions(predicted_order: list[str], actual_order: list[str]) -> int:
    """
    For each (slot_index, predicted_driver):
        - Find where actual_order has predicted_driver
        - If found at same slot:     full slot points
        - If found 1 slot away:      50% of slot_index points
        - If found 2 slots away:     25% of slot_index points
        - Else:                      0

    Points are taken from the slot the user PREDICTED, not where the driver
    finished. This rewards correctly identifying that a driver belongs in
    a high-value slot.
    """
    total = 0
    actual_index = {code: i for i, code in enumerate(actual_order)}

    for predicted_slot, code in enumerate(predicted_order):
        if predicted_slot >= len(SLOT_POINTS):
            break

        actual_slot = actual_index.get(code)
        if actual_slot is None:
            continue   # Driver not in actual top 10

        diff = abs(predicted_slot - actual_slot)
        slot_value = SLOT_POINTS[predicted_slot]

        if diff == 0:
            total += int(slot_value * EXACT_MULT)
        elif diff == 1:
            total += int(slot_value * ONE_OFF_MULT)
        elif diff == 2:
            total += int(slot_value * TWO_OFF_MULT)
        # diff > 2: 0

    return total


def score_tyres(predicted_strategies: dict[str, list[str]],
                actual_stints: dict[str, list[str]]) -> int:
    """
    Per-driver, positional segment comparison.
        predicted[i] == actual[i]  → +5
        predicted[i] != actual[i]  → -2
        i beyond either list       → 0 (no contribution)
    """
    total = 0
    for code, predicted_stints in predicted_strategies.items():
        actual = actual_stints.get(code.upper(), [])

        # Compare only positions that exist in BOTH lists.
        # Extra/missing segments score 0 — neither punished nor rewarded.
        compare_len = min(len(predicted_stints), len(actual))
        for i in range(compare_len):
            if predicted_stints[i] == actual[i]:
                total += TYRE_CORRECT
            else:
                total += TYRE_WRONG

    return total


# ── Aggregate user scoring (mirrors existing pattern) ─────────────────────────

def update_user_aggregate_scores():
    """
    Recomputes User.total_score and User.accuracy_rate to include
    BOTH the in-race pit-call predictions AND the race predictions.

    accuracy_rate stays based on the in-race game only — race predictions
    are graded on partial credit so a binary correct/wrong doesn't fit.
    Race-prediction totals are simply added to total_score.
    """
    from app.models import User, Prediction

    users = User.query.all()
    for user in users:
        # In-race game (unchanged logic from existing scoring_service.py)
        in_race_preds = [p for p in user.predictions]
        scored        = [p for p in in_race_preds if p.status in ('correct', 'wrong')]
        correct       = [p for p in scored if p.status == 'correct']

        in_race_points = sum(p.points_earned for p in in_race_preds)
        accuracy       = round(len(correct) / len(scored) * 100, 1) if scored else 0.0

        # Race predictions (new)
        race_preds   = RacePrediction.query.filter_by(user_id=user.id, status='scored').all()
        race_points  = sum(p.total_points for p in race_preds)

        user.total_score   = in_race_points + race_points
        user.accuracy_rate = accuracy

    db.session.commit()
    return len(users)


# ── Main entry point ──────────────────────────────────────────────────────────

def score_race_predictions(year: int, round_num: int) -> dict:
    """
    Score every pending RacePrediction for the given race.
    """
    cache_file = fastf1_service.processed_cache_dir / f"{year}_R{round_num}_processed.json"
    if not cache_file.exists():
        return {
            'error': f'Race not cached: {year} R{round_num}. '
                     f'Run warm_cache.py --year {year} --round {round_num} first.'
        }

    with open(cache_file) as f:
        race_data = json.load(f)

    actual_order  = extract_finishing_order(race_data)
    actual_stints = extract_stint_sequences(race_data)

    if not actual_order:
        return {'error': 'Could not extract finishing order from cached data.'}

    pending = RacePrediction.query.filter_by(
        year=year, round_num=round_num, status='pending'
    ).all()

    if not pending:
        return {
            'race':    race_data.get('name'),
            'message': 'No pending race predictions to score.',
            'scored':  0,
        }

    for pred in pending:
        pos_pts  = score_positions(pred.predicted_order, actual_order)
        tyre_pts = score_tyres(pred.tyre_strategies, actual_stints)

        pred.position_points = pos_pts
        pred.tyre_points     = tyre_pts
        pred.total_points    = pos_pts + tyre_pts
        pred.status          = 'scored'

    db.session.commit()
    users_updated = update_user_aggregate_scores()

    return {
        'race':           race_data.get('name'),
        'year':           year,
        'round':          round_num,
        'actual_order':   actual_order,
        'actual_stints':  actual_stints,
        'scored':         len(pending),
        'users_updated':  users_updated,
    }