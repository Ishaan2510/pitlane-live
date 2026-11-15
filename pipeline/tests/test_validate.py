"""The validation gate: one test per rule, on a minimal hand-built session folder."""
import json

import pytest

import build
from validate import main, validate_session

COLS = build.LAPS_COLUMNS


def row(driver, lap, position, compound='SOFT'):
    r = dict.fromkeys(COLS)
    r.update(driver=driver, lap=lap, position=position, compound=compound)
    return [r[c] for c in COLS]


def session(tmp_path, **changes):
    files = {
        'laps.json': {'columns': COLS, 'rows': [row('AAA', 1, 1), row('BBB', 1, 2), row('AAA', 2, 1), row('BBB', 2, 2)]},
        'track_status.json': {'periods': [{'status': 'green', 'start_time_s': 0.0, 'end_time_s': 60.0},
                                          {'status': 'yellow', 'start_time_s': 60.0, 'end_time_s': 60.0}],
                              'sc_periods': []},
        'pit_loss.json': {'median_loss_s': 21.5, 'median_loss_sc_s': 12.0, 'median_loss_vsc_s': None, 'stops': []},
        'results.json': [{'driver': 'AAA', 'laps': 2}, {'driver': 'BBB', 'laps': 1}],
    }
    files.update({name.replace('_json', '.json'): content for name, content in changes.items()})
    for name, content in files.items():
        (tmp_path / name).write_text(json.dumps(content), encoding='utf-8')
    return tmp_path


def laps(*rows):
    return {'columns': COLS, 'rows': list(rows)}


def test_valid_session_has_no_problems(tmp_path):
    assert validate_session(session(tmp_path)) == []
    assert main([str(tmp_path)]) == 0


@pytest.mark.parametrize('periods', [
    [{'start_time_s': 10.0, 'end_time_s': 5.0}],          # ends before it starts
    [{'start_time_s': -94628.0, 'end_time_s': 5.0}],      # before lights out
    [{'start_time_s': 10.0, 'end_time_s': None}],         # never closed
])
def test_bad_track_status_period_fails(tmp_path, periods):
    problems = validate_session(session(tmp_path, track_status_json={'periods': periods, 'sc_periods': []}))
    assert len(problems) == 1 and 'track status period 0' in problems[0]


@pytest.mark.parametrize('compound', ['nan', 'None', None, 'TEST'])
def test_compound_outside_the_canonical_set_fails(tmp_path, compound):
    bad = laps(row('AAA', 1, 1, compound), row('AAA', 2, 1))
    problems = validate_session(session(tmp_path, laps_json=bad))
    assert len(problems) == 1 and 'compound' in problems[0]


@pytest.mark.parametrize('loss, ok', [(9.9, False), (10, True), (45, True), (652.148, False), (None, True)])
def test_pit_loss_must_be_between_10_and_45_seconds(tmp_path, loss, ok):
    problems = validate_session(session(tmp_path, pit_loss_json={'median_loss_s': loss}))
    assert (problems == []) is ok


@pytest.mark.parametrize('sc', [-15.057, 0, 30.0])
def test_safety_car_loss_must_be_positive_and_below_green(tmp_path, sc):
    problems = validate_session(session(tmp_path, pit_loss_json={'median_loss_s': 21.5, 'median_loss_sc_s': sc}))
    assert len(problems) == 1 and 'median_loss_sc_s' in problems[0]


def test_repeated_position_fails(tmp_path):
    bad = laps(row('AAA', 1, 1), row('BBB', 1, 1), row('AAA', 2, 1))
    assert validate_session(session(tmp_path, laps_json=bad)) == ['positions on lap 1 are not a permutation']
    out_of_range = laps(row('AAA', 1, 1), row('BBB', 1, 4), row('AAA', 2, 1))
    assert validate_session(session(tmp_path, laps_json=out_of_range)) == ['positions on lap 1 are not a permutation']
    # a third entry that never started may hold a place: P3 is fine with three cars in the results
    three = [{'driver': 'AAA', 'laps': 2}, {'driver': 'BBB', 'laps': 1}, {'driver': 'CCC', 'laps': 0}]
    ok = laps(row('AAA', 1, 1), row('BBB', 1, 3), row('AAA', 2, 1))
    assert validate_session(session(tmp_path, laps_json=ok, results_json=three)) == []


def test_lap_count_must_match_results(tmp_path, capsys):
    problems = validate_session(session(tmp_path, results_json=[{'driver': 'AAA', 'laps': 3}]))
    assert problems == ['laps.json has 2 laps, results.json says 3']
    assert main([str(tmp_path)]) == 1
    assert 'INVALID' in capsys.readouterr().out            # one line with the reason


def test_missing_file_fails(tmp_path):
    assert 'unreadable' in validate_session(tmp_path)[0]
