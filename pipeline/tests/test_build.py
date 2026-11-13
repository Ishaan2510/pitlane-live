"""Unit tests on small hand-built DataFrames. No network, no FastF1 import."""
import json

import numpy as np
import pandas as pd

import build


def td(seconds):
    return pd.Timedelta(seconds=seconds)


def lap(driver, n, t, stint=1, status='1', pit_in=False, pit_out=False, **extra):
    return {
        'Driver': driver, 'Team': 'Team ' + driver, 'LapNumber': float(n),
        'LapTime': td(t) if t is not None else pd.NaT,
        'Stint': float(stint), 'TrackStatus': status,
        'PitInTime': td(1) if pit_in else pd.NaT,
        'PitOutTime': td(1) if pit_out else pd.NaT,
        **extra,
    }


# ── pit loss ──────────────────────────────────────────────────────────────────

def test_pit_loss_green_stop():
    rows = [lap('AAA', n, 90.0) for n in range(1, 6)]
    rows += [lap('AAA', 6, 95.0, pit_in=True), lap('AAA', 7, 107.0, stint=2, pit_out=True)]
    rows += [lap('AAA', n, 88.0, stint=2) for n in range(8, 12)]
    out = build.build_pit_loss(pd.DataFrame(rows))

    assert out['green_stops'] == 1 and out['sc_stops'] == 0
    stop = out['stops'][0]
    assert (stop['driver'], stop['lap'], stop['condition']) == ('AAA', 6, 'green')
    assert stop['ref_lap_s'] == 90.0                       # median of the stint that ended
    assert stop['loss_s'] == 95.0 + 107.0 - 2 * 90.0 == out['median_loss_s']
    assert out['median_loss_sc_s'] is None


def test_pit_loss_sc_stops_measured_against_cars_that_stayed_out():
    rows = []
    for d in ('AAA', 'BBB'):                               # pit under SC on laps 5/6
        rows += [lap(d, n, 90.0) for n in range(1, 5)]
        rows += [lap(d, 5, 130.0, status='14', pit_in=True),
                 lap(d, 6, 150.0, stint=2, status='4', pit_out=True)]
    for d in ('CCC', 'DDD'):                               # stay out
        rows += [lap(d, n, 90.0) for n in range(1, 5)]
        rows += [lap(d, 5, 125.0, status='14'), lap(d, 6, 140.0, status='4')]
    out = build.build_pit_loss(pd.DataFrame(rows))

    assert out['green_stops'] == 0 and out['sc_stops'] == 2
    assert out['median_loss_s'] is None
    assert out['median_loss_sc_s'] == (130.0 + 150.0) - (125.0 + 140.0)


def test_pit_loss_ignores_red_flag_and_untimed_stops():
    rows = [lap('AAA', n, 90.0) for n in range(1, 5)]
    rows += [lap('AAA', 5, 95.0, status='5', pit_in=True),
             lap('AAA', 6, 900.0, stint=2, status='5', pit_out=True)]
    rows += [lap('BBB', n, 90.0) for n in range(1, 5)]
    rows += [lap('BBB', 5, None, pit_in=True), lap('BBB', 6, 110.0, stint=2, pit_out=True)]
    out = build.build_pit_loss(pd.DataFrame(rows))
    assert out['stops'] == []


# ── track status ──────────────────────────────────────────────────────────────

def test_track_status_mapping_and_laps():
    assert build.TRACK_STATUS == {
        '1': 'green', '2': 'yellow', '4': 'sc', '5': 'red', '6': 'vsc', '7': 'vsc_ending',
    }
    lap_ends = np.array([100.0, 200.0, 300.0, 400.0])      # leader finishes lap N at N*100 s
    ts = pd.DataFrame({
        'Time':    [td(0), td(150), td(250), td(390)],
        'Status':  ['1', '4', '6', '3'],
        'Message': ['AllClear', 'SCDeployed', 'VSCDeployed', 'Whatever'],
    })
    periods = build.build_track_status(ts, lap_ends)

    assert [p['status'] for p in periods] == ['green', 'sc', 'vsc', 'unknown']
    assert [(p['start_lap'], p['end_lap']) for p in periods] == [(1, 2), (2, 3), (3, 4), (4, 4)]
    assert periods[0]['end_time_s'] == 150.0 and periods[-1]['end_time_s'] is None


def test_sc_periods_from_race_control():
    rcm = pd.DataFrame({
        'Message': ['GREEN LIGHT - PIT EXIT OPEN', 'VIRTUAL SAFETY CAR DEPLOYED',
                    'VIRTUAL SAFETY CAR ENDING', 'SAFETY CAR DEPLOYED',
                    'SAFETY CAR IN THIS LAP', 'SAFETY CAR DEPLOYED', 'RED FLAG',
                    'VSC DEPLOYED', 'VSC ENDING', 'SAFETY CAR DEPLOYED'],
        'Lap':     [1, 2, 4, 20, 24, 30, 31, 40, 41, 50],
    })
    assert build.build_sc_periods(rcm, last_lap=52) == [
        {'type': 'vsc', 'start_lap': 2,  'end_lap': 4},
        {'type': 'sc',  'start_lap': 20, 'end_lap': 24},
        {'type': 'sc',  'start_lap': 30, 'end_lap': 31},    # ended by the red flag
        {'type': 'vsc', 'start_lap': 40, 'end_lap': 41},    # 2026 wording
        {'type': 'sc',  'start_lap': 50, 'end_lap': 52},    # never withdrawn: runs to the flag
    ]


# ── laps.json ─────────────────────────────────────────────────────────────────

def test_laps_table_is_columnar_and_json_safe(tmp_path):
    extra = dict(Sector1Time=td(30.1234), Sector2Time=td(30), Sector3Time=td(30),
                 Compound='SOFT', TyreLife=3.0, FreshTyre=True, Position=2.0,
                 IsAccurate=True, Deleted=False)
    nans = dict(Sector1Time=pd.NaT, Sector2Time=pd.NaT, Sector3Time=pd.NaT,
                Compound=np.nan, TyreLife=np.nan, FreshTyre=np.nan, Position=np.nan,
                IsAccurate=False, Deleted=None)
    df = pd.DataFrame([lap('AAA', 2, 90.12345, status='12', pit_in=True, **extra),
                       lap('BBB', 1, None, **nans)])
    table = build.build_laps_table(df)

    assert table['columns'] == build.LAPS_COLUMNS
    assert all(len(r) == len(table['columns']) for r in table['rows'])
    assert table['rows'][0][:4] == ['BBB', 'Team BBB', 1, None]          # sorted by lap
    row = dict(zip(table['columns'], table['rows'][1]))
    assert row == {
        'driver': 'AAA', 'team': 'Team AAA', 'lap': 2, 'lap_time_s': 90.123,
        'sector1_s': 30.123, 'sector2_s': 30.0, 'sector3_s': 30.0, 'compound': 'SOFT',
        'tyre_life': 3, 'stint': 1, 'fresh_tyre': True, 'pit_in': True, 'pit_out': False,
        'position': 2, 'track_status': '12', 'is_accurate': True, 'deleted': False,
    }

    path = tmp_path / 'race' / 'laps.json'
    build.write_json(path, table)                       # NaN would raise (allow_nan=False)
    assert json.loads(path.read_text()) == table
    assert ', ' not in path.read_text() and not path.with_name('laps.json.tmp').exists()


# ── distance resampling ───────────────────────────────────────────────────────

def test_resample_by_distance():
    tel = pd.DataFrame({
        'Distance': [0.0, 4.0, 4.0, 12.0, 23.0],          # uneven, one duplicate sample
        'Speed':    [100.0, 140.0, 140.0, 220.0, 110.0],
        'nGear':    [3, 4, 4, 6, 2],
    })
    out = build.resample_by_distance(tel, 5, linear=('Speed',), nearest=('nGear',))

    assert list(out['distance']) == [0, 5, 10, 15, 20]
    assert list(np.round(out['Speed'], 6)) == [100.0, 150.0, 200.0, 190.0, 140.0]
    assert list(out['nGear']) == [3, 4, 6, 6, 2]          # nearest sample, never interpolated


def test_resample_handles_empty_telemetry():
    tel = pd.DataFrame({'Distance': [np.nan], 'Speed': [1.0]})
    assert build.resample_by_distance(tel, 5, linear=('Speed',)) == {'distance': [], 'Speed': []}


# ── schedule + workflow helpers ───────────────────────────────────────────────

def test_completed_sessions_uses_start_plus_three_hours():
    event = pd.Series({
        'Session4': 'Qualifying', 'Session4DateUtc': pd.Timestamp('2026-03-07 05:00'),
        'Session5': 'Race',       'Session5DateUtc': pd.Timestamp('2026-03-08 04:00'),
    })

    def at(s):
        return pd.Timestamp(s, tz='UTC').to_pydatetime()

    assert build.completed_sessions(event, at('2026-03-07 07:59')) == []
    assert build.completed_sessions(event, at('2026-03-08 06:59')) == ['Q']
    assert build.completed_sessions(event, at('2026-03-08 07:01')) == ['Q', 'R']


def test_describe_changes():
    message, new_races = build.describe_changes([
        'A\tfrontend/public/data/2026/14/race/results.json',
        'A\tfrontend/public/data/2026/14/race/laps.json',
        'A\tfrontend/public/data/2026/14/quali/fastest/VER.json',
        'A\tfrontend/public/data/2026/14/event.json',
        'M\tfrontend/public/data/2026/13/race/results.json',
        'M\tfrontend/public/data/manifest.json',
    ])
    assert message == 'data: 2026 R13 R; 2026 R14 Q,R'
    assert new_races == ['2026/14']                      # R13 was only modified
    assert build.describe_changes(['M\tfrontend/public/data/manifest.json']) == (
        'data: refresh manifest', [])
