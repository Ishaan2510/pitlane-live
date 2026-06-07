"""
Seeds fake race predictions for 2025 R1, runs scoring, prints the breakdown.
Run with: python test_race_scoring.py
"""
from app import create_app
from app.models import db, User, RacePrediction
from app.services.race_prediction_scoring import (
    score_race_predictions,
    extract_finishing_order,
    extract_stint_sequences,
)
from app.services.fastf1_service import fastf1_service
import json

app = create_app()

with app.app_context():
    # ── First, show what the actual race data looks like ────────────────────
    cache_file = fastf1_service.processed_cache_dir / "2025_R1_processed.json"
    with open(cache_file) as f:
        race_data = json.load(f)

    actual_order  = extract_finishing_order(race_data)
    actual_stints = extract_stint_sequences(race_data)

    print("=" * 60)
    print("ACTUAL 2025 R1 RESULTS")
    print("=" * 60)
    print(f"Finishing order (top 10): {actual_order}")
    print(f"\nStint sequences:")
    for code in actual_order:
        print(f"  {code}: {actual_stints.get(code, [])}")
    print()

    # ── Get or create a test user ────────────────────────────────────────────
    test_user = User.query.filter_by(username='__test_scoring').first()
    if not test_user:
        test_user = User(
            username='__test_scoring',
            email='__test@scoring.local',
            password_hash='dummy',
        )
        db.session.add(test_user)
        db.session.commit()

    # Clear any existing test predictions for this race
    RacePrediction.query.filter_by(
        user_id=test_user.id, year=2025, round_num=1
    ).delete()
    db.session.commit()

    # ── Build three test predictions of varying quality ──────────────────────
    # 1. Perfect prediction (uses actual order)
    perfect = RacePrediction(
        user_id=test_user.id, year=2025, round_num=1,
        predicted_order=actual_order,
        tyre_strategies={code: actual_stints.get(code, []) for code in actual_order},
    )

    # 2. "Close but not perfect" — swap a few positions
    near_order = actual_order.copy()
    if len(near_order) >= 4:
        near_order[2], near_order[3] = near_order[3], near_order[2]  # swap P3 and P4
    near = RacePrediction(
        user_id=test_user.id, year=2025, round_num=1,
        predicted_order=near_order,
        tyre_strategies={code: actual_stints.get(code, []) for code in near_order[:5]},
    )

    # 3. Mostly wrong — reverse the order
    reversed_order = list(reversed(actual_order))
    wrong = RacePrediction(
        user_id=test_user.id, year=2025, round_num=1,
        predicted_order=reversed_order,
        tyre_strategies={code: ['SOFT', 'SOFT'] for code in reversed_order[:3]},
    )

    # Can't have 3 predictions for same user+race (unique constraint).
    # So we score one at a time.
    print("=" * 60)
    print("TEST 1: PERFECT PREDICTION")
    print("=" * 60)
    db.session.add(perfect)
    db.session.commit()
    result = score_race_predictions(2025, 1)
    p = RacePrediction.query.get(perfect.id)
    print(f"  Position points: {p.position_points}")
    print(f"  Tyre points:     {p.tyre_points}")
    print(f"  Total:           {p.total_points}")
    db.session.delete(p); db.session.commit()

    print()
    print("=" * 60)
    print("TEST 2: NEAR PREDICTION (P3/P4 swapped)")
    print("=" * 60)
    db.session.add(near)
    db.session.commit()
    score_race_predictions(2025, 1)
    p = RacePrediction.query.get(near.id)
    print(f"  Position points: {p.position_points}")
    print(f"  Tyre points:     {p.tyre_points}")
    print(f"  Total:           {p.total_points}")
    db.session.delete(p); db.session.commit()

    print()
    print("=" * 60)
    print("TEST 3: REVERSED ORDER (mostly wrong)")
    print("=" * 60)
    db.session.add(wrong)
    db.session.commit()
    score_race_predictions(2025, 1)
    p = RacePrediction.query.get(wrong.id)
    print(f"  Position points: {p.position_points}")
    print(f"  Tyre points:     {p.tyre_points}")
    print(f"  Total:           {p.total_points}")
    db.session.delete(p); db.session.commit()

    # Cleanup
    db.session.delete(test_user); db.session.commit()
    print("\nTest user cleaned up.")