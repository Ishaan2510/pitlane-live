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
    assert periods[0]['end_time_s'] == 150.0 and periods[-1]['end_time_s'] == 400.0


def test_track_status_times_count_from_lights_out():
    # FastF1's clock starts with the timing feed; lights out here is at 1000 s
    lap_ends = np.array([1100.0, 1200.0, 1300.0])
    ts = pd.DataFrame({
        'Time':    [td(0), td(400), td(420), td(950), td(1150), td(1250), td(1500)],
        'Status':  ['1', '2', '1', '2', '4', '1', '2'],
        'Message': ['AllClear', 'Yellow', 'AllClear', 'Yellow', 'SCDeployed', 'AllClear', 'Yellow'],
    })
    periods = build.build_track_status(ts, lap_ends, start_s=1000.0, end_s=1320.0)
    # the pre-race green and yellow are gone, the yellow shown at the start begins at 0,
    # and the yellow shown after the last car finished is gone too
    assert [(p['status'], p['start_time_s'], p['end_time_s']) for p in periods] == [
        ('yellow', 0.0, 150.0), ('sc', 150.0, 250.0), ('green', 250.0, 320.0)]
    assert [(p['start_lap'], p['end_lap']) for p in periods] == [(1, 2), (2, 3), (3, 3)]


# ── compounds and pit stops (prepare_laps) ────────────────────────────────────

def test_compounds_are_canonical_and_filled_from_the_stint():
    assert [build.canon_compound(v) for v in ('soft', 'HARD', 'nan', 'None', None, np.nan, 'TEST_UNKNOWN', 'UNKNOWN')] \
        == ['SOFT', 'HARD', 'UNKNOWN', 'UNKNOWN', 'UNKNOWN', 'UNKNOWN', 'UNKNOWN', 'UNKNOWN']
    rows = [lap('AAA', 1, 90, Compound='MEDIUM'), lap('AAA', 2, 90, Compound='nan'), lap('AAA', 3, 90, Compound=None),
            lap('AAA', 4, 90, stint=2, Compound='None'), lap('AAA', 5, 90, stint=2, Compound=np.nan),
            lap('BBB', 1, 90, Compound='UNKNOWN'), lap('BBB', 2, 90, Compound=None)]
    out = build.prepare_laps(pd.DataFrame(rows))
    assert out['Compound'].tolist() == ['MEDIUM', 'MEDIUM', 'MEDIUM', 'UNKNOWN', 'UNKNOWN', 'UNKNOWN', 'UNKNOWN']
    # another source knows the rest
    out = build.prepare_laps(pd.DataFrame(rows), extra_compounds={('AAA', 4): 'HARD', ('BBB', 2): 'soft', ('AAA', 1): 'WET'})
    assert out['Compound'].tolist() == ['MEDIUM', 'MEDIUM', 'MEDIUM', 'HARD', 'HARD', 'SOFT', 'SOFT']
    assert set(out['Compound']) <= set(build.COMPOUNDS)


def test_pit_stop_is_an_in_lap_followed_by_an_out_lap_or_a_new_stint():
    rows = [
        lap('AAA', 1, 95, pit_in=True),                        # flag only (2026 Mexico City): not a stop
        lap('AAA', 2, 90), lap('AAA', 3, 95, pit_in=True),     # in-lap + out-lap
        lap('AAA', 4, 105, stint=2, pit_out=True),
        lap('AAA', 5, 95, stint=2, pit_in=True),               # in-lap + new stint, out flag missing
        lap('AAA', 6, 105, stint=3),
        lap('AAA', 7, 90, stint=3),                            # out-lap + new stint, in flag missing
        lap('AAA', 8, 105, stint=4, pit_out=True),
        lap('AAA', 9, 95, stint=4, pit_in=True),               # retired in the pits: no lap after it
        lap('BBB', 1, 95, stint=1), lap('BBB', 2, 90, stint=2),   # new stint, no flag: a data glitch
        lap('BBB', 3, 95, stint=2, pit_in=True), lap('BBB', 5, 105, stint=3, pit_out=True),   # lap 4 missing
    ]
    out = build.prepare_laps(pd.DataFrame(rows))
    stops = out[out['PitStop']]
    assert list(zip(stops['Driver'], stops['LapNumber'])) == [('AAA', 3), ('AAA', 5), ('AAA', 7)]


def test_lap_one_pit_entry_before_lights_out_is_dropped():
    rows = [lap('AAA', 1, 95, pit_in=True), lap('AAA', 2, 105, stint=2, pit_out=True),
            lap('BBB', 1, 95, pit_in=True), lap('BBB', 2, 105, stint=2, pit_out=True)]
    df = pd.DataFrame(rows)
    df.loc[0, 'PitInTime'] = td(3000)                          # in the pit lane before the start at 3600 s
    df.loc[2, 'PitInTime'] = td(3690)                          # really pitted at the end of lap 1
    out = build.prepare_laps(df, start=td(3600))
    assert out['PitInTime'].notna().tolist() == [False, False, True, False]
    assert out['PitStop'].tolist() == [True, False, True, False]   # AAA: still an out-lap on a new stint


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
        'pit_stop': False,
    }
    assert table['rows'][0][table['columns'].index('compound')] == 'UNKNOWN'   # never null or 'nan'

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


# ── Safety Car / VSC pit loss ─────────────────────────────────────────────────

def neutralised_race(pit_in, pit_out, stay_in, stay_out, status=('4', '4'), pitters=('AAA', 'BBB')):
    """Green stops on lap 10/11 for four cars (loss 20 s), then `pitters` stop on lap 20/21."""
    rows = []
    for d in ('AAA', 'BBB', 'CCC', 'DDD'):
        rows += [lap(d, n, 90.0) for n in range(1, 10)]
        rows += [lap(d, 10, 95.0, pit_in=True), lap(d, 11, 105.0, stint=2, pit_out=True)]
        rows += [lap(d, n, 90.0, stint=2) for n in range(12, 20)]
        if d in pitters:
            rows += [lap(d, 20, pit_in, stint=2, status=status[0], pit_in=True),
                     lap(d, 21, pit_out, stint=3, status=status[1], pit_out=True)]
        else:
            rows += [lap(d, 20, stay_in, stint=2, status=status[0]), lap(d, 21, stay_out, stint=2, status=status[1])]
    return build.build_pit_loss(pd.DataFrame(rows))


def test_pit_loss_sc_and_vsc_are_reported_separately():
    sc = neutralised_race(130.0, 150.0, 125.0, 143.0, status=('14', '4'))
    assert (sc['median_loss_s'], sc['median_loss_sc_s'], sc['median_loss_vsc_s']) == (20.0, 12.0, None)
    assert (sc['green_stops'], sc['sc_stops'], sc['vsc_stops']) == (4, 2, 0)
    vsc = neutralised_race(120.0, 125.0, 115.0, 116.0, status=('16', '67'))
    assert (vsc['median_loss_sc_s'], vsc['median_loss_vsc_s'], vsc['vsc_stops']) == (None, 14.0, 2)
    assert {s['condition'] for s in vsc['stops']} == {'green', 'vsc'}


def test_pit_loss_sc_needs_both_laps_under_the_same_neutralisation():
    # in-lap green, out-lap under the Safety Car: neither a green stop nor a Safety Car stop
    out = neutralised_race(95.0, 150.0, 90.0, 140.0, status=('1', '4'))
    assert (out['green_stops'], out['sc_stops'], out['median_loss_sc_s']) == (4, 0, None)
    # a VSC that became a full Safety Car on the out-lap counts as neither
    out = neutralised_race(120.0, 150.0, 115.0, 140.0, status=('6', '64'))
    assert (out['sc_stops'], out['vsc_stops']) == (0, 0)


def test_pit_loss_sc_is_null_when_implausible():
    # the cars that stayed out were still catching the Safety Car: the "loss" is negative
    assert neutralised_race(130.0, 150.0, 150.0, 150.0)['median_loss_sc_s'] is None
    # more than a green stop costs
    assert neutralised_race(140.0, 160.0, 125.0, 143.0)['median_loss_sc_s'] is None
    # only one stop to go on
    one = neutralised_race(130.0, 150.0, 125.0, 143.0, pitters=('AAA',))
    assert (one['sc_stops'], one['median_loss_sc_s']) == (1, None)


def test_pit_loss_leaves_repair_stops_out_of_the_green_median():
    rows = [lap('AAA', n, 90.0) for n in range(1, 6)]
    rows += [lap('AAA', 6, 95.0, pit_in=True), lap('AAA', 7, 737.0, stint=2, pit_out=True)]   # ten minutes in the garage
    rows += [lap('AAA', n, 90.0, stint=2) for n in range(8, 12)]
    out = build.build_pit_loss(pd.DataFrame(rows))
    assert out['median_loss_s'] is None and out['green_stops'] == 0
    assert out['stops'][0]['condition'] == 'slow'
