import json
from collections import Counter
from pathlib import Path

from app.services.race_prediction_scoring import (
    extract_finishing_order,
    score_positions,
    score_tyres,
)

PROCESSED = Path(__file__).parent.parent / 'fastf1_cache' / 'processed'


def _old_top10_positions(race_data):
    """What the pre-fix extract_finishing_order did: last-seen position per driver."""
    last = {}
    for lap in reversed(race_data['laps']):
        for d in lap['drivers']:
            if d['driver'] not in last and d.get('position'):
                last[d['driver']] = d['position']
    return sorted(last.values())[:10]


def _races_with_duplicate_positions(n=3):
    found = []
    for f in sorted(PROCESSED.glob('*_processed.json')):
        data = json.loads(f.read_text())
        if 'results' in data:
            continue
        if any(c > 1 for c in Counter(_old_top10_positions(data)).values()):
            found.append(data)
            if len(found) == n:
                break
    return found


def test_fallback_has_unique_top10_on_races_that_used_to_duplicate():
    races = _races_with_duplicate_positions()
    assert len(races) == 3, 'expected at least 3 cached races with the old duplicate bug'
    for race in races:
        order = extract_finishing_order(race)
        assert len(order) == 10, race['name']
        assert len(set(order)) == 10, race['name']


def test_fallback_puts_retirement_behind_finishers():
    race = {'laps': [
        {'lap_number': 1, 'drivers': [{'driver': 'DNF', 'position': 1}, {'driver': 'FIN', 'position': 2}]},
        {'lap_number': 2, 'drivers': [{'driver': 'FIN', 'position': 1}]},
    ]}
    assert extract_finishing_order(race) == ['FIN', 'DNF']


def test_results_take_precedence():
    race = {
        'results': [
            {'driver': 'bbb', 'position': 2},
            {'driver': 'aaa', 'position': 1},
            {'driver': 'ccc', 'position': None},
        ],
        'laps': [{'lap_number': 1, 'drivers': [{'driver': 'CCC', 'position': 1}]}],
    }
    assert extract_finishing_order(race) == ['AAA', 'BBB']


def test_score_positions():
    actual = ['VER', 'NOR', 'LEC', 'PIA']
    assert score_positions(['VER', 'NOR', 'LEC'], actual) == 25 + 18 + 15
    # VER exact (25), LEC one slot off from slot 1 (18*0.5=9), NOR one off from slot 2 (15*0.5=7)
    assert score_positions(['VER', 'LEC', 'NOR'], actual) == 25 + 9 + 7
    # PIA two slots off from slot 1 (18*0.25=4), HAM not in top 10
    assert score_positions(['HAM', 'PIA'], actual) == int(18 * 0.25)
    assert score_positions(['XXX'], actual) == 0


def test_score_tyres():
    actual = {'VER': ['SOFT', 'MEDIUM'], 'NOR': ['MEDIUM', 'HARD']}
    # match +5, mismatch -2, extra segment 0
    assert score_tyres({'VER': ['SOFT', 'HARD', 'MEDIUM']}, actual) == 5 - 2
    assert score_tyres({'nor': ['MEDIUM', 'HARD']}, actual) == 10
    assert score_tyres({'HAM': ['SOFT']}, actual) == 0
    assert score_tyres({}, actual) == 0
