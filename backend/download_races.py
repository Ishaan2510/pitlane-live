"""
Run this script to pre-download race data for all 2024 rounds.
Usage:  python download_races.py
        python download_races.py --rounds 2 3 6   (specific rounds only)
"""
import sys
import fastf1
from pathlib import Path

CACHE_DIR = Path(__file__).parent / 'fastf1_cache'
CACHE_DIR.mkdir(exist_ok=True)
fastf1.Cache.enable_cache(str(CACHE_DIR))

def download_race(year, race_round):
    try:
        print(f"\n⬇️  Downloading {year} Round {race_round}...")
        session = fastf1.get_session(year, race_round, 'Race')
        session.load()
        print(f"✅  Round {race_round} — {session.event['EventName']} done")
        return True
    except Exception as e:
        print(f"❌  Round {race_round} failed: {e}")
        return False

if __name__ == '__main__':
    year = 2024

    if '--rounds' in sys.argv:
        idx = sys.argv.index('--rounds')
        rounds = [int(r) for r in sys.argv[idx + 1:]]
    else:
        # All 24 rounds
        rounds = list(range(1, 25))

    print(f"Downloading {len(rounds)} races for {year}...")
    ok  = 0
    fail = 0
    for r in rounds:
        if download_race(year, r):
            ok += 1
        else:
            fail += 1

    print(f"\n{'='*40}")
    print(f"Done — {ok} succeeded, {fail} failed")