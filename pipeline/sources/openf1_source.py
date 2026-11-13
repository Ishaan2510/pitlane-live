"""
OpenF1 source (https://openf1.org): free historical REST API, no login.

Free tier: 3 requests/second and 30 requests/minute. Data is "live" (not free) from 30
minutes before a session until 30 minutes after it; the pipeline only looks 3 hours after
the start. Every response for a session is cached under .openf1-cache/<session_key>/.

The module is split in two: an HTTP client (throttle, retries, disk cache) and pure
functions that turn OpenF1 rows into the frames described in base.py. The pure functions
are what the fixture tests exercise.
"""
import hashlib
import json
import os
import re
import shutil
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from .base import (DRIVER_COLUMNS, GRID_COLUMNS, LAP_COLUMNS, PIT_COLUMNS, POSITION_COLUMNS,
                   RACE_CONTROL_COLUMNS, RESULT_COLUMNS, STINT_COLUMNS, TRACK_STATUS_COLUMNS,
                   WEATHER_COLUMNS)

BASE = 'https://api.openf1.org/v1'
JOLPICA = 'https://api.jolpi.ca/ergast/f1'
ROOT = Path(__file__).resolve().parents[2]

SESSION_NAMES = {'R': ('Race',), 'Q': ('Qualifying',), 'S': ('Sprint',),
                 'SQ': ('Sprint Qualifying', 'Sprint Shootout')}
GRID_SESSION = {'R': 'Q', 'S': 'SQ'}     # the starting grid is published under this session

# Stay under 3 req/s and 30 req/min: 2 burst tokens refilled at 26 per minute.
RATE_PER_SECOND = 26 / 60
BURST = 2
TIMEOUT = 45
MAX_TRIES = 6
READY_RATIO = 0.9                        # share of the finishers' laps that must be present
POSITION_TOLERANCE_S = 1.0               # position messages can trail the timing line slightly


# ── HTTP client ───────────────────────────────────────────────────────────────

class TokenBucket:
    def __init__(self, rate, capacity, clock=time.monotonic, sleep=time.sleep):
        self.rate, self.capacity = rate, capacity
        self.clock, self.sleep = clock, sleep
        self.tokens, self.stamp = capacity, clock()

    def take(self):
        now = self.clock()
        self.tokens = min(self.capacity, self.tokens + (now - self.stamp) * self.rate)
        self.stamp = now
        if self.tokens < 1:
            wait = (1 - self.tokens) / self.rate
            self.sleep(wait)
            self.stamp += wait
            self.tokens = 1
        self.tokens -= 1


class OpenF1Client:
    def __init__(self, cache_dir=None, http=None, bucket=None, sleep=time.sleep):
        self.cache_dir = Path(cache_dir or os.getenv('OPENF1_CACHE') or ROOT / '.openf1-cache')
        self.http = http or requests.Session()
        self.bucket = bucket or TokenBucket(RATE_PER_SECOND, BURST)
        self.sleep = sleep

    def get(self, endpoint, *filters, session_key=None):
        """
        Rows of an endpoint ([] when OpenF1 has none). `filters` are raw query terms such as
        'driver_number=4' or 'date>=2025-05-25T14:20:00'. Responses for a session_key are
        cached on disk; queries without one (the session list) always hit the network.
        """
        terms = ([f'session_key={session_key}'] if session_key else []) + list(filters)
        query = '&'.join(terms)
        path = None
        if session_key:
            digest = hashlib.sha1(query.encode()).hexdigest()[:12]
            path = self.cache_dir / str(session_key) / f'{endpoint}_{digest}.json'
            if path.exists():
                return json.loads(path.read_text(encoding='utf-8'))
        rows = self._request(f'{BASE}/{endpoint}?{query}')
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_name(path.name + '.tmp')
            tmp.write_text(json.dumps(rows, separators=(',', ':')), encoding='utf-8')
            os.replace(tmp, path)
        return rows

    def _request(self, url):
        problem = None
        for attempt in range(MAX_TRIES):
            self.bucket.take()
            try:
                res = self.http.get(url, timeout=TIMEOUT)
            except requests.RequestException as e:
                problem = e
                self.sleep(2 ** attempt)
                continue
            if res.status_code == 404:               # OpenF1's "No results found."
                return []
            if res.status_code == 429 or res.status_code >= 500:
                problem = f'HTTP {res.status_code}'
                retry_after = res.headers.get('Retry-After', '')
                self.sleep(float(retry_after) if retry_after.isdigit() else 2 ** (attempt + 1))
                continue
            res.raise_for_status()
            data = res.json()
            return data if isinstance(data, list) else []
        raise RuntimeError(f'OpenF1 gave up after {MAX_TRIES} tries ({problem}): {url}')

    def forget(self, session_key):
        """Drop a session's cached responses (it was incomplete; the next run refetches)."""
        shutil.rmtree(self.cache_dir / str(session_key), ignore_errors=True)


_client = None


def default_client():
    global _client
    if _client is None:
        _client = OpenF1Client()
    return _client


# ── pure transforms: OpenF1 rows -> base.py frames ────────────────────────────

def _when(values):
    return pd.to_datetime(pd.Series(values, dtype='object'), utc=True, format='ISO8601')


def driver_frame(drivers):
    rows = [{'Driver': d['name_acronym'], 'DriverNumber': str(d['driver_number']),
             'Team': d.get('team_name'), 'TeamColor': d.get('team_colour')} for d in drivers]
    return pd.DataFrame(rows, columns=DRIVER_COLUMNS)


def pit_in_laps(laps, pit):
    """{(driver_number, lap)} of every in-lap: the pit endpoint names it, and an out-lap
    implies the lap before it (covers stops the pit endpoint missed)."""
    found = {(p['driver_number'], p['lap_number']) for p in pit if p.get('lap_number')}
    found |= {(lap['driver_number'], lap['lap_number'] - 1) for lap in laps
              if lap.get('is_pit_out_lap') and lap['lap_number'] > 1}
    return found


def stint_frame(stints, codes, in_laps=frozenset()):
    """
    codes: driver_number -> acronym.
    OpenF1 counts the in-lap as the first lap of the new stint (lap_start = in-lap, the
    previous stint's lap_end = in-lap - 1). The frame follows FastF1 instead: the in-lap
    still belongs to the old tyres and the new stint starts on the out-lap.
    """
    rows = []
    for s in sorted(stints, key=lambda s: (s['driver_number'], s['stint_number'])):
        number, start = s['driver_number'], s.get('lap_start')
        if number not in codes or start is None:
            continue
        first = not rows or rows[-1]['Driver'] != codes[number]
        if not first and (number, start) in in_laps:
            start += 1
        if not first:
            rows[-1]['LapEnd'] = start - 1                    # a stint runs until the next one starts
        # LapEnd of the last stint stays empty = "until the driver's last lap" (OpenF1's
        # lap_end leaves out the lap a car retires on).
        rows.append({'Driver': codes[number], 'Stint': s['stint_number'], 'Compound': s.get('compound'),
                     'LapStart': start, 'LapEnd': None,
                     'TyreAgeAtStart': s.get('tyre_age_at_start') or 0})
    return pd.DataFrame(rows, columns=STINT_COLUMNS)


def tyre_life(tyre_age_at_start, lap, lap_start):
    """Laps on the tyre at the END of `lap`: a new set shows 1 on its first lap, the same
    convention FastF1's TyreLife uses."""
    return tyre_age_at_start + (lap - lap_start) + 1


def deleted_laps(race_control, laps):
    """
    {(driver_number, lap)} of laps deleted by race control, e.g.
    'CAR 22 (TSU) TIME 1:23.351 DELETED - TRACK LIMITS AT TURN 10 LAP 8 15:14:56'.
    The lap is found by its TIME, because the message's lap number is one ahead of
    OpenF1's lap numbers in qualifying. 'LAP DELETED' messages carry no time and use the number.
    """
    by_driver = {}
    for lap in laps:
        if lap.get('lap_duration') is not None:
            by_driver.setdefault(lap['driver_number'], []).append((lap['lap_duration'], lap['lap_number']))
    found = set()
    for m in race_control:
        text = m.get('message') or ''
        hit = re.search(r'CAR (\d+) .*DELETED.*\bLAP (\d+)', text)
        if not hit or 'REINSTATED' in text:
            continue
        number, lap_number = int(hit.group(1)), int(hit.group(2))
        timed = re.search(r'TIME (\d+):(\d+\.\d+) DELETED', text)
        if timed:
            seconds = int(timed.group(1)) * 60 + float(timed.group(2))
            match = [n for duration, n in by_driver.get(number, []) if abs(duration - seconds) < 0.0015]
            lap_number = match[-1] if match else lap_number
        found.add((number, lap_number))
    return found


def quali_phase_starts(race_control):
    """[(start Timestamp, 'Q1'), ...] from the qualifying_phase field of race control messages."""
    first = {}
    for m in sorted(race_control, key=lambda m: m['date']):
        phase = m.get('qualifying_phase')
        if phase in (1, 2, 3) and phase not in first:
            first[phase] = pd.Timestamp(m['date'])
    return sorted((start, f'Q{phase}') for phase, start in first.items())


def track_status_frame(race_control, t0):
    """
    Rebuild F1's track status stream from race control messages.
    Codes: 1 green, 2 yellow (any sector), 4 SC, 5 red, 6 VSC, 7 VSC ending.
    'TRACK CLEAR' / a green track flag ends everything.
    """
    names = {'1': 'AllClear', '2': 'Yellow', '4': 'SCDeployed', '5': 'Red',
             '6': 'VSCDeployed', '7': 'VSCEnding'}
    yellow, neutral, red = set(), None, False
    rows = [{'Time': pd.Timedelta(0), 'Status': '1', 'Message': 'AllClear'}]
    for m in sorted(race_control, key=lambda m: m['date']):
        text = (m.get('message') or '').upper()
        flag, scope = m.get('flag'), m.get('scope')
        if m.get('category') == 'SafetyCar':
            if 'VIRTUAL' in text and 'DEPLOYED' in text:
                neutral = '6'
            elif 'VIRTUAL' in text and 'ENDING' in text:
                neutral = '7'
            elif 'DEPLOYED' in text:
                neutral = '4'
        elif scope == 'Sector' and flag in ('YELLOW', 'DOUBLE YELLOW'):
            yellow.add(m.get('sector'))
        elif scope == 'Sector' and flag == 'CLEAR':
            yellow.discard(m.get('sector'))
        elif scope == 'Track' and flag == 'RED':
            red = True
        elif scope == 'Track' and flag in ('CLEAR', 'GREEN'):
            yellow, neutral, red = set(), None, False
        else:
            continue
        code = '5' if red else neutral or ('2' if yellow else '1')
        if code != rows[-1]['Status']:
            rows.append({'Time': pd.Timestamp(m['date']) - t0, 'Status': code, 'Message': names[code]})
    return pd.DataFrame(rows, columns=TRACK_STATUS_COLUMNS)


def race_control_frame(race_control, t0):
    rows = [{'Time': pd.Timestamp(m['date']) - t0, 'Message': m.get('message') or '',
             'Lap': m.get('lap_number')} for m in sorted(race_control, key=lambda m: m['date'])]
    return pd.DataFrame(rows, columns=RACE_CONTROL_COLUMNS)


def weather_frame(weather, t0):
    rows = [{'Time': pd.Timestamp(w['date']) - t0, 'TrackTemp': w.get('track_temperature'),
             'AirTemp': w.get('air_temperature'), 'Humidity': w.get('humidity'),
             'WindSpeed': w.get('wind_speed'), 'WindDirection': w.get('wind_direction'),
             'Rainfall': bool(w.get('rainfall'))} for w in sorted(weather, key=lambda w: w['date'])]
    return pd.DataFrame(rows, columns=WEATHER_COLUMNS)


def lap_times(laps):
    """Raw laps with parsed start and end timestamps. End = start + duration, or the next
    lap's start when the duration is missing."""
    df = pd.DataFrame(laps).sort_values(['driver_number', 'lap_number']).reset_index(drop=True)
    df['start'] = _when(df['date_start'])
    duration = pd.to_timedelta(pd.to_numeric(df['lap_duration']), unit='s')
    next_start = df.groupby('driver_number')['start'].shift(-1)
    df['end'] = (df['start'] + duration).fillna(next_start)
    # A lap with no end is the one a car retired on. For "what happened during this lap"
    # (position, track status) it is taken to last until the field finished that lap.
    df['window_end'] = df['end'].fillna(df['lap_number'].map(df.groupby('lap_number')['end'].max()))
    return df


def positions_at_lap_end(position, timed_laps, codes):
    """Position of every driver at the end of each lap: the last position sample at or
    before the lap's end (plus a small tolerance for messages that trail the line)."""
    samples = {}
    for p in sorted(position, key=lambda p: p['date']):
        samples.setdefault(p['driver_number'], ([], []))
        samples[p['driver_number']][0].append(pd.Timestamp(p['date']).value)
        samples[p['driver_number']][1].append(p['position'])
    tolerance = int(POSITION_TOLERANCE_S * 1e9)
    rows = []
    for lap in timed_laps.itertuples():
        times, places = samples.get(lap.driver_number, ([], []))
        end = lap.window_end
        if pd.isna(end) or lap.driver_number not in codes or not times:
            continue
        i = int(np.searchsorted(times, end.value + tolerance, side='right')) - 1
        if i >= 0:
            rows.append({'Driver': codes[lap.driver_number], 'LapNumber': lap.lap_number,
                         'Position': places[i]})
    return pd.DataFrame(rows, columns=POSITION_COLUMNS)


def lap_frame(timed_laps, drivers, stints, in_laps, positions, track_status, deleted, t0):
    """The LAP_COLUMNS frame: OpenF1 laps merged with stints, pit stops, positions and track status."""
    codes = dict(zip(drivers['DriverNumber'].astype(int), drivers['Driver']))
    teams = dict(zip(drivers['Driver'], drivers['Team']))
    df = timed_laps[timed_laps['driver_number'].isin(codes)].copy()

    def seconds(col):
        return pd.to_timedelta(pd.to_numeric(df[col]), unit='s')

    out = pd.DataFrame({
        'Driver':      df['driver_number'].map(codes),
        'LapNumber':   df['lap_number'].astype(float),
        'LapTime':     seconds('lap_duration'),
        'Sector1Time': seconds('duration_sector_1'),
        'Sector2Time': seconds('duration_sector_2'),
        'Sector3Time': seconds('duration_sector_3'),
        'Time':        df['end'] - t0,
        'SpeedI1':     pd.to_numeric(df['i1_speed']),
        'SpeedI2':     pd.to_numeric(df['i2_speed']),
        'SpeedFL':     np.nan,
        'SpeedST':     pd.to_numeric(df['st_speed']),
    })
    out['Team'] = out['Driver'].map(teams)
    start = df['start'] - t0

    out_lap = df['is_pit_out_lap'].fillna(False).astype(bool)
    key = list(zip(df['driver_number'], df['lap_number']))
    marker = pd.Timedelta(0)
    out['PitOutTime'] = [marker if is_out else pd.NaT for is_out in out_lap]
    out['PitInTime'] = [marker if k in in_laps else pd.NaT for k in key]

    # Tyres
    tyres = {}
    for s in stints.itertuples():
        last = s.LapEnd if pd.notna(s.LapEnd) else df['lap_number'].max()   # trimmed to real laps below
        for n in range(int(s.LapStart), int(last) + 1):
            tyres[(s.Driver, n)] = (s.Stint, s.Compound, tyre_life(s.TyreAgeAtStart, n, s.LapStart),
                                    s.TyreAgeAtStart == 0)
    tyre_rows = [tyres.get((d, int(n)), (np.nan, None, np.nan, False))
                 for d, n in zip(out['Driver'], out['LapNumber'])]
    out['Stint'] = [t[0] for t in tyre_rows]
    out['Compound'] = [t[1] for t in tyre_rows]
    out['TyreLife'] = [t[2] for t in tyre_rows]
    out['FreshTyre'] = [t[3] for t in tyre_rows]

    # Position at the end of the lap
    place = {(p.Driver, p.LapNumber): p.Position for p in positions.itertuples()}
    out['Position'] = [place.get((d, int(n)), np.nan) for d, n in zip(out['Driver'], out['LapNumber'])]

    # Every track status seen between the start and the end of the lap
    times = track_status['Time'].dt.total_seconds().to_numpy()
    status_codes = track_status['Status'].tolist()

    def seen(lap_start, lap_end):
        if pd.isna(lap_start) or pd.isna(lap_end):
            return ''
        first = max(int(np.searchsorted(times, lap_start.total_seconds(), side='right')) - 1, 0)
        last = int(np.searchsorted(times, lap_end.total_seconds(), side='right'))
        return ''.join(dict.fromkeys(status_codes[first:last]))

    out['TrackStatus'] = [seen(s, e) for s, e in zip(start, df['window_end'] - t0)]
    out['Deleted'] = [k in deleted for k in key]
    out['IsAccurate'] = (out['LapTime'].notna() & out['Sector1Time'].notna()
                         & out['Sector2Time'].notna() & out['Sector3Time'].notna()
                         & out['PitInTime'].isna() & out['PitOutTime'].isna()
                         & ~out['TrackStatus'].str.contains('[4567]') & (out['TrackStatus'] != '')
                         & (out['LapNumber'] > 1))
    return out[LAP_COLUMNS].reset_index(drop=True)


def result_frame(results, drivers, grid, quali=False):
    """
    OpenF1 session_result rows (or rows normalised from Jolpica) -> RESULT_COLUMNS.
    A row may carry 'status' and 'grid' (Jolpica does); otherwise they are derived.
    """
    info = drivers.set_index(drivers['DriverNumber'].astype(int))
    grid = dict(zip(grid['Driver'], grid['GridPosition'])) if len(grid) else {}
    ordered = sorted(results, key=lambda r: (r.get('position') is None, r.get('position') or 0,
                                             -(r.get('number_of_laps') or 0)))
    most_laps = max((r.get('number_of_laps') or 0 for r in results), default=0)
    winner_time = next((r.get('duration') for r in ordered if isinstance(r.get('duration'), (int, float))), None)
    rows = []
    for place, r in enumerate(ordered, start=1):
        if r['driver_number'] not in info.index:
            continue
        d = info.loc[r['driver_number']]
        out = r.get('dsq') and 'D' or r.get('dns') and 'W' or r.get('dnf') and 'R'
        laps = r.get('number_of_laps')
        status = r.get('status') or {'D': 'Disqualified', 'W': 'Did not start', 'R': 'Retired'}.get(out)
        if not status and not quali:
            status = 'Finished' if laps == most_laps else 'Lapped'
        duration, gap = r.get('duration'), r.get('gap_to_leader')
        times = duration if isinstance(duration, list) else [None, None, None]
        if quali or out:
            race_time = None
        elif place == 1:
            race_time = duration
        elif isinstance(gap, (int, float)) and not isinstance(gap, bool):
            race_time = gap
        elif isinstance(duration, (int, float)) and winner_time:
            race_time = duration - winner_time       # lapped car: OpenF1's gap is the text "+1 LAP"
        else:
            race_time = None
        rows.append({
            'Abbreviation': d['Driver'], 'DriverNumber': d['DriverNumber'], 'TeamName': d['Team'],
            'TeamColor': d['TeamColor'], 'Position': r.get('position') or place,
            'ClassifiedPosition': out or str(r.get('position') or place),
            'GridPosition': r.get('grid', grid.get(d['Driver'])), 'Status': status,
            'Points': r.get('points'), 'Laps': laps,
            'Time': pd.to_timedelta(race_time, unit='s') if race_time is not None else pd.NaT,
            'Q1': pd.to_timedelta(times[0], unit='s') if times[0] else pd.NaT,
            'Q2': pd.to_timedelta(times[1], unit='s') if len(times) > 1 and times[1] else pd.NaT,
            'Q3': pd.to_timedelta(times[2], unit='s') if len(times) > 2 and times[2] else pd.NaT,
        })
    return pd.DataFrame(rows, columns=RESULT_COLUMNS)


def jolpica_results(payload, key, numbers):
    """Jolpica/Ergast results -> rows shaped like OpenF1 session_result. numbers: acronym -> driver_number."""
    races = payload.get('MRData', {}).get('RaceTable', {}).get('Races', [])
    rows = []
    for r in (races[0].get(key, []) if races else []):
        code = r.get('Driver', {}).get('code')
        if code not in numbers:
            continue
        text = r.get('positionText', '')
        millis = r.get('Time', {}).get('millis')
        rows.append({
            'driver_number': numbers[code], 'position': int(r['position']),
            'number_of_laps': int(r.get('laps') or 0), 'points': float(r.get('points') or 0),
            'dnf': text == 'R', 'dns': text == 'W', 'dsq': text == 'D',
            'duration': int(millis) / 1000 if millis and r['position'] == '1' else None,
            'gap_to_leader': None, 'status': r.get('status'), 'grid': int(r.get('grid') or 0) or None,
        })
    return rows


def laps_ready(results, laps):
    """Share of the classified finishers' laps that OpenF1 already has (0..1)."""
    finishers = {r['driver_number']: r.get('number_of_laps') or 0 for r in results
                 if not (r.get('dnf') or r.get('dns') or r.get('dsq'))}
    expected = sum(finishers.values())
    have = sum(1 for lap in laps if lap['driver_number'] in finishers)
    return min(have / expected, 1.0) if expected else 0.0


def telemetry_frame(car_data, start):
    """car_data rows of one lap -> Distance (m, speed integrated over time) plus channels.
    OpenF1 car data arrives at about 3.7 Hz."""
    df = pd.DataFrame([c for c in car_data if c.get('speed') is not None])
    if df.empty:
        return pd.DataFrame(columns=['t', 'Distance', 'Speed', 'Throttle', 'Brake', 'nGear', 'DRS'])
    df['t'] = (_when(df['date']) - start).dt.total_seconds()
    df = df.sort_values('t').drop_duplicates('t').reset_index(drop=True)
    t, v = df['t'].to_numpy(), df['speed'].to_numpy(dtype=float) / 3.6
    steps = (v[1:] + v[:-1]) / 2 * np.diff(t)
    distance = max(t[0], 0) * v[0] + np.concatenate([[0.0], np.cumsum(steps)])
    return pd.DataFrame({
        't': t, 'Distance': distance, 'Speed': df['speed'].astype(float),
        'Throttle': df['throttle'].astype(float), 'Brake': (df['brake'] > 0).astype(int),
        'nGear': df['n_gear'].astype(int), 'DRS': df['drs'].astype(int),
    })


def outline_frame(location, telemetry, start):
    """location rows + the lap's telemetry -> Distance, X, Y, Speed (distance and speed
    interpolated onto the position samples)."""
    loc = pd.DataFrame([p for p in location if p.get('x') or p.get('y')])
    if loc.empty or telemetry.empty:
        return pd.DataFrame(columns=['Distance', 'X', 'Y', 'Speed'])
    loc['t'] = (_when(loc['date']) - start).dt.total_seconds()
    loc = loc.sort_values('t')
    return pd.DataFrame({
        'Distance': np.interp(loc['t'], telemetry['t'], telemetry['Distance']),
        'X': loc['x'].astype(float).to_numpy(), 'Y': loc['y'].astype(float).to_numpy(),
        'Speed': np.interp(loc['t'], telemetry['t'], telemetry['Speed']),
    })


# ── the source ────────────────────────────────────────────────────────────────

def _stamp(ts):
    return ts.tz_convert('UTC').strftime('%Y-%m-%dT%H:%M:%S.%f')


class OpenF1Source:
    name = 'openf1'

    def __init__(self, year, round_num, code, start_utc, log=print, client=None):
        self.year, self.round_num, self.code = year, round_num, code
        self.start_utc = pd.Timestamp(start_utc)       # scheduled start, used to find the session
        self.log = log
        self.client = client or default_client()
        self.tag = f'{year} R{round_num} {code}'

    # ── loading ───────────────────────────────────────────────────────────────
    def load(self):
        try:
            return self._load()
        except Exception as e:
            self.log(f'  {self.tag}: OpenF1 request failed ({type(e).__name__}: {e}) - skipped, next run retries')
            return False

    def _session_meta(self, code):
        """The OpenF1 session of this weekend with the given code: same name, start within a day."""
        if not hasattr(self, '_sessions'):
            self._sessions = self.client.get('sessions', f'year={self.year}')
        for s in self._sessions:
            start = pd.Timestamp(s['date_start'])
            if s.get('session_name') in SESSION_NAMES[code] and abs(start - self.start_utc) < pd.Timedelta(days=4):
                if code == self.code and abs(start - self.start_utc) > pd.Timedelta(hours=12):
                    continue
                return s
        return None

    def _load(self):
        meta = self._session_meta(self.code)
        if not meta:
            self.log(f'  {self.tag}: OpenF1 does not list this session yet - skipped')
            return False
        self.meta, key = meta, meta['session_key']
        self.t0 = pd.Timestamp(meta['date_start'])
        raw = {name: self.client.get(name, session_key=key)
               for name in ('drivers', 'laps', 'session_result', 'stints', 'pit',
                            'race_control', 'position', 'weather')}
        self._drivers = driver_frame(raw['drivers'])
        self.codes = dict(zip(self._drivers['DriverNumber'].astype(int), self._drivers['Driver']))

        results = raw['session_result']
        if not results and self.code in ('R', 'S'):
            results = self._jolpica()
        ready = laps_ready(results, raw['laps']) if results else 0.0
        if ready < READY_RATIO:
            self.client.forget(key)
            why = 'no classification yet' if not results else f'only {ready:.0%} of the finishers\' laps'
            self.log(f'  {self.tag}: OpenF1 data is incomplete ({why}) - skipped, next run retries')
            return False

        self._raw = raw
        self._timed = lap_times(raw['laps'])
        in_laps = pit_in_laps(raw['laps'], raw['pit'])
        self._stints = stint_frame(raw['stints'], self.codes, in_laps)
        self._track_status = track_status_frame(raw['race_control'], self.t0)
        self._positions = positions_at_lap_end(raw['position'], self._timed, self.codes)
        self._deleted = deleted_laps(raw['race_control'], raw['laps'])
        self._laps = lap_frame(self._timed, self._drivers, self._stints, in_laps, self._positions,
                               self._track_status, self._deleted, self.t0)
        self._results = result_frame(results, self._drivers, self._grid_rows(results),
                                     quali=self.code in ('Q', 'SQ'))
        return True

    def _jolpica(self):
        kind, key = ('sprint', 'SprintResults') if self.code == 'S' else ('results', 'Results')
        try:
            res = requests.get(f'{JOLPICA}/{self.year}/{self.round_num}/{kind}.json', timeout=TIMEOUT)
            res.raise_for_status()
            numbers = {code: number for number, code in self.codes.items()}
            rows = jolpica_results(res.json(), key, numbers)
        except Exception as e:
            self.log(f'    Jolpica fallback failed: {e}')
            return []
        if rows:
            self.log(f'    {self.tag}: classification from Jolpica (OpenF1 session_result is empty)')
        return rows

    def _grid_rows(self, results):
        """Starting grid: OpenF1 publishes it under the qualifying session of the weekend."""
        rows = []
        grid_code = GRID_SESSION.get(self.code)
        meta = self._session_meta(grid_code) if grid_code else None
        if meta:
            for g in self.client.get('starting_grid', session_key=meta['session_key']):
                if g['driver_number'] in self.codes:
                    rows.append({'Driver': self.codes[g['driver_number']], 'GridPosition': g['position']})
        if not rows:                                   # Jolpica rows carry their own grid
            rows = [{'Driver': self.codes[r['driver_number']], 'GridPosition': r['grid']}
                    for r in results if r.get('grid') and r['driver_number'] in self.codes]
        return pd.DataFrame(rows, columns=GRID_COLUMNS)

    # ── frames ────────────────────────────────────────────────────────────────
    def event(self):
        total = int(self._laps['LapNumber'].max()) if len(self._laps) else 0
        return pd.Series({'circuit': self.meta.get('circuit_short_name'), 'total_laps': total})

    def drivers(self):
        return self._drivers

    def laps(self):
        return self._laps

    def stints(self):
        return self._stints

    def pits(self):
        laps = self._laps
        return laps[laps['PitInTime'].notna()][PIT_COLUMNS].reset_index(drop=True)

    def results(self):
        return self._results

    def grid(self):
        return self._results.rename(columns={'Abbreviation': 'Driver'})[GRID_COLUMNS]

    def track_status(self):
        return self._track_status

    def race_control(self):
        return race_control_frame(self._raw['race_control'], self.t0)

    def weather(self):
        return weather_frame(self._raw['weather'], self.t0)

    def positions_at_lap_end(self):
        return self._positions

    # ── telemetry ─────────────────────────────────────────────────────────────
    def _fastest_laps(self, number=None):
        """Timed, not deleted, not pit laps, fastest first (one driver or everyone)."""
        laps = self._timed
        ok = laps['lap_duration'].notna() & laps['start'].notna() & ~laps['is_pit_out_lap'].fillna(False).astype(bool)
        ok &= np.array([(d, n) not in self._deleted
                        for d, n in zip(laps['driver_number'], laps['lap_number'])], dtype=bool)
        if number is not None:
            ok &= laps['driver_number'] == number
        return laps[ok].sort_values('lap_duration')

    def _lap_telemetry(self, lap):
        window = (f'driver_number={lap.driver_number}', f'date>={_stamp(lap.start)}', f'date<={_stamp(lap.end)}')
        car = self.client.get('car_data', *window, session_key=self.meta['session_key'])
        return telemetry_frame(car, lap.start), window

    def fastest_lap_telemetry(self, driver):
        number = next((n for n, code in self.codes.items() if code == driver), None)
        laps = self._fastest_laps(number)
        if number is None or laps.empty:
            return None
        lap = next(laps.itertuples())
        tel, _ = self._lap_telemetry(lap)
        if tel.empty:
            return None
        segment = None
        for phase_start, name in quali_phase_starts(self._raw['race_control']):
            if lap.start >= phase_start:
                segment = name
        mine = self._laps[(self._laps['Driver'] == driver) & (self._laps['LapNumber'] == lap.lap_number)]
        info = {'team': self._drivers.set_index('Driver')['Team'].get(driver),
                'lap_time': pd.Timedelta(seconds=lap.lap_duration), 'segment': segment,
                'compound': mine['Compound'].iloc[0] if len(mine) else None}
        return info, tel

    def circuit_outline(self):
        best = self._fastest_laps().drop_duplicates('driver_number').head(3)
        for lap in best.itertuples():
            tel, window = self._lap_telemetry(lap)
            location = self.client.get('location', *window, session_key=self.meta['session_key'])
            outline = outline_frame(location, tel, lap.start)
            if len(outline) >= 100 and outline['Distance'].max() >= 1000:
                outline.attrs = {'driver': self.codes.get(lap.driver_number),
                                 'lap_time': pd.Timedelta(seconds=lap.lap_duration)}
                return outline
        raise ValueError('no lap with position data')

    def circuit_info(self):
        # Corner markers come from MultiViewer through FastF1 (public, not the F1 archive).
        from fastf1 import mvapi
        info = mvapi.get_circuit_info(year=self.year, circuit_key=self.meta['circuit_key'])
        return info.corners, info.rotation
