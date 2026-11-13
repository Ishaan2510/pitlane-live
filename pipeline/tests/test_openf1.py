"""
OpenF1 source logic against recorded responses (fixtures/openf1/: 2025 Monaco GP race,
drivers NOR, TSU, GAS, first laps). No network.
"""
import json
from pathlib import Path

import pandas as pd
import pytest

import build
from sources import openf1_source as o
from sources.base import LAP_COLUMNS

FIXTURES = Path(__file__).parent / 'fixtures' / 'openf1'
T0 = pd.Timestamp('2025-05-25T13:00:00+00:00')          # scheduled session start


@pytest.fixture(scope='module')
def raw():
    return {p.stem: json.loads(p.read_text(encoding='utf-8')) for p in FIXTURES.glob('*.json')}


@pytest.fixture(scope='module')
def frames(raw):
    drivers = o.driver_frame(raw['drivers'])
    codes = dict(zip(drivers['DriverNumber'].astype(int), drivers['Driver']))
    timed = o.lap_times(raw['laps'])
    in_laps = o.pit_in_laps(raw['laps'], raw['pit'])
    stints = o.stint_frame(raw['stints'], codes, in_laps)
    status = o.track_status_frame(raw['race_control'], T0)
    positions = o.positions_at_lap_end(raw['position'], timed, codes)
    deleted = o.deleted_laps(raw['race_control'], raw['laps'])
    laps = o.lap_frame(timed, drivers, stints, in_laps, positions, status, deleted, T0)
    return {'drivers': drivers, 'codes': codes, 'timed': timed, 'stints': stints,
            'status': status, 'positions': positions, 'laps': laps}


def lap(frames, driver, number):
    laps = frames['laps']
    return laps[(laps['Driver'] == driver) & (laps['LapNumber'] == number)].iloc[0]


# ── laps ──────────────────────────────────────────────────────────────────────

def test_lap_frame_has_the_contract_columns(frames):
    laps = frames['laps']
    assert list(laps.columns) == LAP_COLUMNS
    assert len(laps) == 21 + 10 + 8                      # NOR 1-21, TSU 1-10, GAS 1-8 (retired)
    assert set(laps['Team']) == {'McLaren', 'Red Bull Racing', 'Alpine'}


def test_lap_times_and_end_of_lap(frames):
    nor2 = lap(frames, 'NOR', 2)
    assert nor2['LapTime'].total_seconds() == 104.634
    assert nor2['Sector1Time'].total_seconds() == 34.072
    # end of lap 2 = start of lap 3, measured from the session start
    assert abs(nor2['Time'].total_seconds() - (6 * 60 + 17.67)) < 0.2
    assert (nor2['SpeedI1'], nor2['SpeedST']) == (97, 252)


def test_retirement_lap_has_no_time_but_keeps_position_and_status(frames):
    gas8 = lap(frames, 'GAS', 8)
    assert pd.isna(gas8['LapTime']) and pd.isna(gas8['Time'])
    assert gas8['Position'] == 19 and gas8['TrackStatus'] == '12'
    assert gas8['Compound'] == 'MEDIUM' and gas8['Stint'] == 2


def test_pit_in_and_out_laps(frames):
    def pits(driver):
        mine = frames['laps'][frames['laps']['Driver'] == driver]
        return (mine[mine['PitInTime'].notna()]['LapNumber'].tolist(),
                mine[mine['PitOutTime'].notna()]['LapNumber'].tolist())

    assert pits('NOR') == ([19], [20])
    assert pits('TSU') == ([1], [2])
    assert pits('GAS') == ([1], [2])                     # the retirement on lap 8 is not a stop


# ── stints and tyre life ──────────────────────────────────────────────────────

def test_stints_start_on_the_out_lap(frames):
    stints = frames['stints']

    def of(driver):
        mine = stints[stints['Driver'] == driver]
        return list(zip(mine['Stint'], mine['Compound'], mine['LapStart']))

    # OpenF1 says lap_start 19 (the in-lap) for NOR's second stint and 1 for TSU's
    assert of('NOR')[:2] == [(1, 'MEDIUM', 1), (2, 'HARD', 20)]
    assert of('TSU')[:2] == [(1, 'SOFT', 1), (2, 'HARD', 2)]
    assert of('GAS') == [(1, 'MEDIUM', 1), (2, 'MEDIUM', 2)]


def test_compound_and_stint_per_lap(frames):
    assert (lap(frames, 'NOR', 19)['Compound'], lap(frames, 'NOR', 19)['Stint']) == ('MEDIUM', 1)
    assert (lap(frames, 'NOR', 20)['Compound'], lap(frames, 'NOR', 20)['Stint']) == ('HARD', 2)
    assert lap(frames, 'TSU', 1)['Compound'] == 'SOFT'
    assert lap(frames, 'TSU', 2)['Compound'] == 'HARD'


def test_tyre_life_counts_from_one_like_fastf1(frames):
    assert o.tyre_life(0, 1, 1) == 1 and o.tyre_life(6, 1, 1) == 7 and o.tyre_life(0, 25, 20) == 6
    assert lap(frames, 'NOR', 1)['TyreLife'] == 1
    assert lap(frames, 'NOR', 19)['TyreLife'] == 19
    assert lap(frames, 'NOR', 20)['TyreLife'] == 1       # new hards on the out-lap
    gas1 = lap(frames, 'GAS', 1)
    assert gas1['TyreLife'] == 7 and not gas1['FreshTyre']   # started on a 6-lap-old set
    assert lap(frames, 'GAS', 7)['TyreLife'] == 6 and lap(frames, 'GAS', 7)['FreshTyre']


# ── position at the end of the lap ────────────────────────────────────────────

def test_position_at_lap_end(frames):
    expected = {('NOR', 1): 1, ('NOR', 18): 1, ('NOR', 19): 4, ('NOR', 20): 3,
                ('TSU', 1): 17, ('TSU', 2): 17, ('GAS', 1): 18, ('GAS', 7): 18}
    got = {k: lap(frames, *k)['Position'] for k in expected}
    assert got == expected                                # same values FastF1 gives for these laps


def test_position_ignores_samples_after_the_lap(raw, frames):
    late = raw['position'] + [{'date': '2025-05-25T13:04:40+00:00', 'driver_number': 4, 'position': 9}]
    positions = o.positions_at_lap_end(late, frames['timed'], frames['codes'])
    nor = positions[positions['Driver'] == 'NOR'].set_index('LapNumber')['Position']
    assert nor[1] == 1 and nor[2] == 9                    # lap 1 ended at 13:04:32.9, before the sample


# ── track status and Safety Car mapping ───────────────────────────────────────

def test_track_status_rebuilt_from_race_control(frames):
    status = frames['status']
    assert status['Status'].tolist() == ['1', '2', '1', '2', '1', '6', '7', '1', '2', '1']
    assert status['Message'].tolist()[5:8] == ['VSCDeployed', 'VSCEnding', 'AllClear']
    vsc = status[status['Status'] == '6'].iloc[0]
    assert vsc['Time'] == pd.Timedelta(minutes=4, seconds=43)   # 13:04:43, session started 13:00
    # Sector 13 went yellow on lap 8 and sector 16 came and went: still one yellow period
    assert (status['Status'] == '2').sum() == 3


def test_track_status_per_lap(frames):
    assert lap(frames, 'NOR', 2)['TrackStatus'] == '16'   # green, then the VSC came out
    assert lap(frames, 'NOR', 3)['TrackStatus'] == '6'
    assert lap(frames, 'NOR', 4)['TrackStatus'] == '671'
    assert lap(frames, 'NOR', 5)['TrackStatus'] == '1'
    assert lap(frames, 'TSU', 8)['TrackStatus'] == '12'


def test_sc_periods_and_named_periods_through_the_builders(raw, frames):
    messages = o.race_control_frame(raw['race_control'], T0)
    assert build.build_sc_periods(messages, last_lap=78) == [{'type': 'vsc', 'start_lap': 2, 'end_lap': 4}]
    periods = build.build_track_status(frames['status'], build.leader_lap_ends(frames['laps']))
    assert [(p['status'], p['start_lap'], p['end_lap']) for p in periods][4:8] == [
        ('green', 1, 2), ('vsc', 2, 4), ('vsc_ending', 4, 4), ('green', 4, 8)]


def test_safety_car_and_red_flag_mapping():
    def message(time, category, text, flag=None, scope=None, sector=None):
        return {'date': f'2025-01-01T13:{time}+00:00', 'category': category, 'message': text,
                'flag': flag, 'scope': scope, 'sector': sector, 'lap_number': 1}

    race_control = [
        message('10:00', 'Flag', 'YELLOW IN TRACK SECTOR 3', 'YELLOW', 'Sector', 3),
        message('10:20', 'SafetyCar', 'SAFETY CAR DEPLOYED'),
        message('10:40', 'Flag', 'CLEAR IN TRACK SECTOR 3', 'CLEAR', 'Sector', 3),
        message('15:00', 'SafetyCar', 'SAFETY CAR IN THIS LAP'),       # still SC until the track is clear
        message('16:30', 'Flag', 'TRACK CLEAR', 'CLEAR', 'Track'),
        message('20:00', 'Flag', 'BLUE FLAG FOR CAR 5', 'BLUE', 'Driver'),
        message('30:00', 'Flag', 'RED FLAG', 'RED', 'Track'),
        message('32:00', 'Flag', 'TRACK CLEAR', 'CLEAR', 'Track'),       # still red: session is suspended
        message('45:00', 'Flag', 'GREEN LIGHT - PIT EXIT OPEN', 'GREEN', 'Track'),
        message('50:00', 'SessionStatus', 'SESSION STARTED'),            # the restart
        message('55:00', 'SafetyCar', 'VSC DEPLOYED'),                   # 2026 wording
        message('56:00', 'SafetyCar', 'VSC ENDING'),
        message('56:10', 'Flag', 'TRACK CLEAR', 'CLEAR', 'Track'),
        message('58:00', 'SafetyCar', 'SAFETY CAR DEPLOYED'),
        message('58:30', 'Other', 'RED FLAG - RACE SUSPENDED'),          # 2026 wording
    ]
    status = o.track_status_frame(race_control, pd.Timestamp('2025-01-01T13:00:00+00:00'))
    assert [build.TRACK_STATUS[c] for c in status['Status']] == [
        'green', 'yellow', 'sc', 'green', 'red', 'green', 'vsc', 'vsc_ending', 'green', 'sc', 'red']
    assert status['Time'].dt.total_seconds().tolist()[:6] == [0, 600, 620, 990, 1800, 3000]
    # the race start itself is not a restart
    start = [message('03:00', 'SessionStatus', 'SESSION STARTED')]
    assert o.track_status_frame(start, pd.Timestamp('2025-01-01T13:00:00+00:00'))['Status'].tolist() == ['1']


# ── deleted laps ──────────────────────────────────────────────────────────────

def test_deleted_lap_is_found_by_its_time(raw, frames):
    assert o.deleted_laps(raw['race_control'], raw['laps']) == {(22, 8)}
    assert lap(frames, 'TSU', 8)['Deleted'] and not lap(frames, 'TSU', 7)['Deleted']
    # qualifying: race control's lap number runs one ahead of OpenF1's; the time decides
    laps = [{'driver_number': 63, 'lap_number': 5, 'lap_duration': 93.247}]
    message = [{'message': 'CAR 63 (RUS) TIME 1:33.247 DELETED - TRACK LIMITS AT TURN 10 LAP 6 16:10:29'}]
    assert o.deleted_laps(message, laps) == {(63, 5)}
    no_time = [{'message': 'CAR 10 (GAS) LAP DELETED - TRACK LIMITS AT TURN 10 LAP 7 16:08:37 (PIT)'}]
    assert o.deleted_laps(no_time, laps) == {(10, 7)}


# ── results and readiness ─────────────────────────────────────────────────────

def test_result_frame(raw, frames):
    grid = pd.DataFrame({'Driver': ['NOR', 'TSU'], 'GridPosition': [1, 12]})
    results = o.result_frame(raw['session_result'], frames['drivers'], grid)
    assert results['Abbreviation'].tolist() == ['NOR', 'TSU', 'GAS']
    assert results['ClassifiedPosition'].tolist() == ['1', '17', 'R']
    assert results['Status'].tolist() == ['Finished', 'Lapped', 'Retired']
    assert results['Position'].tolist() == [1, 17, 3]     # no position for a DNF: placed after the rest
    assert results['Time'].iloc[0].total_seconds() == 6033.843 and results['Time'].iloc[1:].isna().all()
    assert results['GridPosition'].tolist()[:2] == [1, 12] and pd.isna(results['GridPosition'].iloc[2])
    built = build.build_results(results)
    assert built[0]['team_color'] == '#F47600' and built[2]['time_s'] is None


def test_qualifying_result_times():
    drivers = pd.DataFrame([{'Driver': 'NOR', 'DriverNumber': '4', 'Team': 'McLaren', 'TeamColor': 'F47600'}])
    row = [{'position': 1, 'driver_number': 4, 'number_of_laps': 27, 'dnf': False, 'dns': False,
            'dsq': False, 'duration': [71.285, 70.57, None], 'gap_to_leader': [0.056, 0.0, None]}]
    out = build.build_results(o.result_frame(row, drivers, pd.DataFrame(), quali=True), quali=True)
    assert (out[0]['q1_s'], out[0]['q2_s'], out[0]['q3_s'], out[0]['time_s']) == (71.285, 70.57, None, None)
    assert out[0]['status'] is None
    # a text position ('RT') sorts last and counts as retired
    rows = [dict(row[0], position='RT', duration=[None, None, None]), row[0]]
    two = pd.concat([drivers, drivers.assign(Driver='LIN', DriverNumber='6')])
    rows[0]['driver_number'] = 6
    frame = o.result_frame(rows, two, pd.DataFrame(), quali=True)
    assert frame[['Abbreviation', 'Position', 'ClassifiedPosition']].values.tolist() == [['NOR', 1, '1'], ['LIN', 2, 'R']]


def test_session_is_ready_only_with_most_of_the_finishers_laps(raw):
    # The fixture holds 21 of NOR's 78 laps and 10 of TSU's 76: far from complete
    assert o.laps_ready(raw['session_result'], raw['laps']) < 0.25
    done = [dict(r, number_of_laps={4: 21, 22: 10}.get(r['driver_number'], 0)) for r in raw['session_result']]
    assert o.laps_ready(done, raw['laps']) == 1.0
    assert o.laps_ready(done, raw['laps'][:25]) < o.READY_RATIO
    assert o.laps_ready([], raw['laps']) == 0.0           # no classification yet


def test_jolpica_fallback_rows():
    payload = {'MRData': {'RaceTable': {'Races': [{'Results': [
        {'position': '1', 'positionText': '1', 'points': '25', 'grid': '1', 'laps': '78', 'status': 'Finished',
         'Driver': {'code': 'NOR'}, 'Time': {'millis': '6033843'}},
        {'position': '20', 'positionText': 'R', 'points': '0', 'grid': '17', 'laps': '7', 'status': 'Collision',
         'Driver': {'code': 'GAS'}},
        {'position': '5', 'positionText': '5', 'points': '10', 'grid': '4', 'laps': '78', 'status': 'Finished',
         'Driver': {'code': 'XXX'}},
    ]}]}}}
    rows = o.jolpica_results(payload, 'Results', {'NOR': 4, 'GAS': 10})
    assert [(r['driver_number'], r['position'], r['dnf'], r['grid'], r['status']) for r in rows] == [
        (4, 1, False, 1, 'Finished'), (10, 20, True, 17, 'Collision')]
    assert rows[0]['duration'] == 6033.843
    assert o.jolpica_results({}, 'Results', {}) == []


# ── telemetry ─────────────────────────────────────────────────────────────────

def test_distance_is_speed_integrated_over_time():
    start = pd.Timestamp('2025-05-25T14:00:00+00:00')
    car = [{'date': f'2025-05-25T14:00:0{i}.000000+00:00', 'speed': 180, 'throttle': 100, 'brake': 100 * (i == 3),
            'n_gear': 7, 'drs': 12, 'rpm': 11000} for i in range(1, 5)]
    tel = o.telemetry_frame(car + [dict(car[0], speed=None)], start)
    assert tel['Distance'].tolist() == [50.0, 100.0, 150.0, 200.0]     # 180 km/h = 50 m/s, first sample at 1 s
    assert tel['Brake'].tolist() == [0, 0, 1, 0]
    location = [{'date': '2025-05-25T14:00:02.500000+00:00', 'x': 10, 'y': 20},
                {'date': '2025-05-25T14:00:03.000000+00:00', 'x': 0, 'y': 0}]   # 0/0 = no fix
    outline = o.outline_frame(location, tel, start)
    assert outline[['Distance', 'X', 'Y', 'Speed']].values.tolist() == [[125.0, 10.0, 20.0, 180.0]]


# ── HTTP client: throttle, retries, cache ─────────────────────────────────────

class FakeResponse:
    def __init__(self, status, data=None, headers=None):
        self.status_code, self._data, self.headers = status, data, headers or {}

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


class FakeHttp:
    def __init__(self, responses):
        self.responses, self.urls = list(responses), []

    def get(self, url, timeout):
        self.urls.append(url)
        return self.responses.pop(0)


def client(tmp_path, responses):
    naps = []
    http = FakeHttp(responses)
    bucket = o.TokenBucket(1000, 1000)
    return o.OpenF1Client(cache_dir=tmp_path, http=http, bucket=bucket, sleep=naps.append), http, naps


def test_client_caches_session_responses_on_disk(tmp_path):
    c, http, _ = client(tmp_path, [FakeResponse(200, [{'lap_number': 1}])])
    assert c.get('laps', 'driver_number=4', session_key=9979) == [{'lap_number': 1}]
    assert c.get('laps', 'driver_number=4', session_key=9979) == [{'lap_number': 1}]   # no second request
    assert http.urls == ['https://api.openf1.org/v1/laps?session_key=9979&driver_number=4']
    c.forget(9979)
    assert not (tmp_path / '9979').exists()


def test_client_retries_429_and_5xx_then_gives_up(tmp_path):
    c, http, naps = client(tmp_path, [FakeResponse(429, headers={'Retry-After': '7'}), FakeResponse(503),
                                      FakeResponse(200, [1])])
    assert c.get('sessions', 'year=2026') == [1]
    assert naps == [7.0, 4] and len(http.urls) == 3
    c, http, _ = client(tmp_path, [FakeResponse(500)] * o.MAX_TRIES)
    with pytest.raises(RuntimeError, match='gave up'):
        c.get('sessions', 'year=2026')


def test_client_treats_no_results_as_empty(tmp_path):
    c, _, _ = client(tmp_path, [FakeResponse(404, {'detail': 'No results found.'}),
                                FakeResponse(200, {'detail': 'No results found.'})])
    assert c.get('starting_grid', session_key=1) == []
    assert c.get('sessions', 'year=1999') == []


def test_token_bucket_stays_under_the_free_tier_limits():
    now = [0.0]

    def sleep(seconds):
        now[0] += seconds

    bucket = o.TokenBucket(o.RATE_PER_SECOND, o.BURST, clock=lambda: now[0], sleep=sleep)
    stamps = []
    for _ in range(90):
        bucket.take()
        stamps.append(now[0])
    for i, t in enumerate(stamps):
        assert sum(1 for s in stamps[i:] if s < t + 1) <= 3          # 3 per second
        assert sum(1 for s in stamps[i:] if s < t + 60) <= 30        # 30 per minute
