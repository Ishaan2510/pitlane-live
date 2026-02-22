"""
warm_cache.py — Pre-process and cache all F1 race data so users never hit a cold load.

Usage:
    # Warm current year only (run after each race weekend)
    python warm_cache.py

    # Warm a specific year
    python warm_cache.py --year 2024

    # Warm multiple years
    python warm_cache.py --year 2024 --year 2025

    # Warm a specific race only (e.g. after a new race completes)
    python warm_cache.py --year 2025 --round 5

    # Force re-process even if cache already exists
    python warm_cache.py --force

Deploy tip:
    Add this to your startup script or a cron job:
        python warm_cache.py --year 2025
    It's safe to run repeatedly — it skips races that are already cached
    unless you pass --force.
"""

import sys
import time
import argparse
import datetime
from pathlib import Path

# Make sure Flask app context is available
sys.path.insert(0, str(Path(__file__).parent))

from app.services.fastf1_service import fastf1_service
import fastf1


def warm_race(year: int, race_round: int, race_name: str, force: bool = False) -> bool:
    """
    Process and cache a single race. Returns True if processed, False if skipped.
    """
    cache_file = fastf1_service.processed_cache_dir / f"{year}_R{race_round}_processed.json"

    if cache_file.exists() and not force:
        size_kb = cache_file.stat().st_size // 1024
        print(f"  ✓ Already cached ({size_kb} KB) — skipping. Use --force to reprocess.")
        return False

    print(f"  Processing...", flush=True)
    t0 = time.time()

    try:
        data = fastf1_service.process_race_telemetry(year, race_round)
        elapsed = time.time() - t0

        if data:
            size_kb = cache_file.stat().st_size // 1024
            print(f"  ✓ Done in {elapsed:.1f}s — {len(data['laps'])} laps cached ({size_kb} KB)")
            return True
        else:
            print(f"  ✗ Failed — no data returned (race may not exist yet)")
            return False

    except Exception as e:
        elapsed = time.time() - t0
        print(f"  ✗ Error after {elapsed:.1f}s: {e}")
        return False


def warm_circuit(year: int, race_round: int, force: bool = False) -> bool:
    """Cache circuit coordinate data for a race."""
    cache_file = fastf1_service.processed_cache_dir / f"{year}_R{race_round}_circuit.json"

    if cache_file.exists() and not force:
        return False  # silent skip, already cached

    try:
        data = fastf1_service.get_circuit_data(year, race_round)
        if data:
            print(f"  ✓ Circuit data cached ({len(data.get('coordinates', []))} points)")
            return True
    except Exception as e:
        print(f"  ✗ Circuit cache failed: {e}")
    return False


def get_completed_races(year: int):
    """
    Return list of (round, name) for races that have already happened.
    Filters out future races and testing sessions.
    """
    try:
        schedule = fastf1.get_event_schedule(year, include_testing=False)
        today    = datetime.date.today()
        completed = []

        for _, event in schedule.iterrows():
            import pandas as pd
            if pd.isna(event['EventDate']):
                continue

            race_date = event['EventDate']
            if hasattr(race_date, 'date'):
                race_date = race_date.date()

            if race_date <= today and event['EventFormat'] != 'testing':
                completed.append((int(event['RoundNumber']), event['EventName']))

        return completed

    except Exception as e:
        print(f"Warning: could not fetch schedule — {e}")
        return []


def main():
    parser = argparse.ArgumentParser(
        description='Pre-warm FastF1 race cache for Pitlane Live'
    )
    parser.add_argument(
        '--year', type=int, action='append', dest='years',
        help='Year to warm (can specify multiple times). Defaults to current year.'
    )
    parser.add_argument(
        '--round', type=int, dest='race_round', default=None,
        help='Specific round number to warm (optional). Requires a single --year.'
    )
    parser.add_argument(
        '--force', action='store_true',
        help='Force reprocessing even if cache exists.'
    )
    args = parser.parse_args()

    # Default to current year if none specified
    years = args.years or [datetime.date.today().year]

    print("=" * 60)
    print("  Pitlane Live — Cache Warmer")
    print("=" * 60)
    print(f"  Years:  {', '.join(str(y) for y in years)}")
    print(f"  Force:  {args.force}")
    if args.race_round:
        print(f"  Round:  {args.race_round} only")
    print("=" * 60)
    print()

    total_processed = 0
    total_skipped   = 0
    total_failed    = 0
    grand_start     = time.time()

    for year in years:
        print(f"── {year} Season ──────────────────────────────────────")

        if args.race_round:
            # Single race mode
            races_to_process = [(args.race_round, f"Round {args.race_round}")]
        else:
            races_to_process = get_completed_races(year)

        if not races_to_process:
            print(f"  No completed races found for {year}.")
            print()
            continue

        print(f"  Found {len(races_to_process)} race(s) to process.\n")

        for race_round, race_name in races_to_process:
            print(f"  Round {race_round:2d}: {race_name}")

            # Warm circuit data first (fast, needed for track rendering)
            warm_circuit(year, race_round, force=args.force)

            # Warm full race telemetry
            success = warm_race(year, race_round, race_name, force=args.force)

            if success is True:
                total_processed += 1
            elif success is False:
                # Distinguish skipped vs failed by checking cache file
                cache_file = fastf1_service.processed_cache_dir / f"{year}_R{race_round}_processed.json"
                if cache_file.exists():
                    total_skipped += 1
                else:
                    total_failed += 1

            print()

    elapsed = time.time() - grand_start
    print("=" * 60)
    print(f"  Complete in {elapsed:.0f}s")
    print(f"  Processed : {total_processed}")
    print(f"  Skipped   : {total_skipped} (already cached)")
    print(f"  Failed    : {total_failed}")
    print("=" * 60)

    if total_failed > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()