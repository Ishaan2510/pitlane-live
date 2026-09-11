"""
Sanity check for the committed pre-built JSONs. Run after warm_cache.py, before pushing:
    python test_processed_data.py
Fails on the two things that have bitten before: a race with 0 laps, and a circuit
outline that belongs to a different race (e.g. Miami drawing Bahrain's track).
"""
import json, sys
from pathlib import Path

P = Path(__file__).parent / 'fastf1_cache' / 'processed'
bad = []

for f in sorted(P.glob('*_processed.json')):
    d = json.load(open(f))
    if not d.get('laps') or d.get('total_laps') != len(d['laps']):
        bad.append(f"{f.name}: {len(d.get('laps', []))} laps, total_laps={d.get('total_laps')}")
    if not d.get('weather'):
        bad.append(f"{f.name}: no weather")
    c = f.with_name(f.name.replace('_processed', '_circuit'))
    if c.exists() and json.load(open(c)).get('name') != d.get('name'):
        bad.append(f"{c.name}: circuit is '{json.load(open(c)).get('name')}' but race is '{d.get('name')}'")

for c in sorted(P.glob('*_circuit.json')):
    if not c.with_name(c.name.replace('_circuit', '_processed')).exists():
        bad.append(f"{c.name}: circuit without a processed race (stale?)")

print('\n'.join(bad) or f'ok — {len(list(P.glob("*_processed.json")))} races checked')
sys.exit(1 if bad else 0)
