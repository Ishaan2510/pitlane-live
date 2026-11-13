"""
Pitlane Live race data pipeline.

Builds compact static JSON for every race weekend into frontend/public/data/
(served by Vercel's CDN). Standalone: imports nothing from backend/.
File shapes are documented in pipeline/SCHEMA.md.

    python pipeline/build.py --year 2026 --round 14      # one event
    python pipeline/build.py --year 2026                 # every completed event not built yet
    python pipeline/build.py --year 2024 --year 2025 --year 2026 --skip-existing   # backfill
    python pipeline/build.py --manifest-only             # rebuild manifest.json from disk

    --force            rebuild sessions that are already on disk
    --sessions R,Q     limit sessions (R Race, Q Qualifying, S Sprint, SQ Sprint Qualifying)

FastF1's raw cache lives in $FASTF1_CACHE (default .fastf1-cache/).
"""

import argparse
import json
import os
import sys
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / 'frontend' / 'public' / 'data'
SCHEMA_VERSION = 1
COMPLETED_AFTER = timedelta(hours=3)   # session start + 3h = data should be published

# code -> (FastF1 session name, output folder)
SESSIONS = {
    'Q':  ('Qualifying',        'quali'),
    'SQ': ('Sprint Qualifying', 'sprint_quali'),
    'S':  ('Sprint',            'sprint'),
    'R':  ('Race',              'race'),
}
# 2023 called Sprint Qualifying the "Sprint Shootout"
SESSION_ALIASES = {'Sprint Shootout': 'Sprint Qualifying'}

TRACK_STATUS = {
    '1': 'green', '2': 'yellow', '4': 'sc', '5': 'red', '6': 'vsc', '7': 'vsc_ending',
}

LAPS_COLUMNS = [
    'driver', 'team', 'lap', 'lap_time_s', 'sector1_s', 'sector2_s', 'sector3_s',
    'compound', 'tyre_life', 'stint', 'fresh_tyre', 'pit_in', 'pit_out', 'position',
    'track_status', 'is_accurate', 'deleted',
]


def log(msg):
    print(msg, flush=True)


# ── small value helpers ───────────────────────────────────────────────────────

def rnd(v, digits):
    """Rounded float, or None for NaN/None."""
    if v is None or pd.isna(v):
        return None
    return round(float(v), digits)


def secs(v):
    """Timedelta -> seconds (3 decimals), or None."""
    if v is None or pd.isna(v):
        return None
    return round(v.total_seconds(), 3)


def as_int(v):
    return None if v is None or pd.isna(v) else int(v)


def as_bool(v):
    return False if v is None or pd.isna(v) else bool(v)


def as_str(v):
    return None if v is None or pd.isna(v) else str(v)


def utc_iso(v):
    """Naive-UTC or aware timestamp -> '2025-06-01T13:00:00Z', or None."""
    if v is None or pd.isna(v):
        return None
    ts = pd.Timestamp(v)
    ts = ts.tz_localize('UTC') if ts.tzinfo is None else ts.tz_convert('UTC')
    return ts.strftime('%Y-%m-%dT%H:%M:%SZ')


def now_iso():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def write_json(path, obj):
    """Compact JSON, written to .tmp then atomically moved into place."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(obj, f, separators=(',', ':'), allow_nan=False)
    os.replace(tmp, path)


def read_json(path):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return None


# ── lap <-> session time ──────────────────────────────────────────────────────

def leader_lap_ends(laps):
    """Session time (s) at which the first car completed each lap, in lap order."""
    ends = laps.dropna(subset=['Time', 'LapNumber']).groupby('LapNumber')['Time'].min()
    return ends.sort_index().dt.total_seconds().to_numpy()


def lap_at(t, lap_ends):
    """Lap the leader was on at session time t (seconds). Clamped to the race distance."""
    if len(lap_ends) == 0:
        return 1
    return min(int(np.searchsorted(lap_ends, t)) + 1, len(lap_ends))


# ── replay.json ───────────────────────────────────────────────────────────────

SPEED_COLS = ['SpeedI1', 'SpeedI2', 'SpeedFL', 'SpeedST']


def build_replay_laps(laps, total_laps):
    """Lap-by-lap leaderboard, same shape the old process_race_telemetry produced
    (lap_time is seconds as a number here, not a pandas timedelta string)."""
    by_lap = {int(n): g for n, g in laps.dropna(subset=['LapNumber']).groupby('LapNumber')}
    out = []
    for n in range(1, total_laps + 1):
        rows = []
        for lap in (by_lap[n].to_dict('records') if n in by_lap else []):
            # LapTime is NaN on lap 1 and on SC/red-flag laps; the driver still has a position.
            if pd.isna(lap['Position']) and pd.isna(lap['Time']):
                continue
            speeds = [float(lap[c]) for c in SPEED_COLS if pd.notna(lap.get(c)) and float(lap[c]) > 0]
            rows.append({
                'driver':    lap['Driver'],
                'team':      lap['Team'],
                'position':  as_int(lap['Position']),
                'lap_time':  secs(lap['LapTime']),
                'compound':  lap['Compound'] if pd.notna(lap['Compound']) else 'UNKNOWN',
                'tire_life': as_int(lap['TyreLife']) or 0,
                'pit_out':   pd.notna(lap.get('PitOutTime')),
                'pit_in':    pd.notna(lap.get('PitInTime')),
                'avg_speed': round(sum(speeds) / len(speeds), 1) if speeds else None,
                'max_speed': round(max(speeds), 1) if speeds else None,
                '_end':      lap['Time'] if pd.notna(lap['Time']) else None,
            })
        rows.sort(key=lambda d: d['position'] or 999)
        leader_end = rows[0]['_end'] if rows else None
        for i, d in enumerate(rows):
            end = d.pop('_end')
            gap = (end - leader_end).total_seconds() if i and end is not None and leader_end is not None else -1
            d['gap'] = f'+{gap:.3f}s' if gap >= 0 else 'LEADER'
        out.append({'lap_number': n, 'drivers': rows})
    return out


# ── laps.json ─────────────────────────────────────────────────────────────────

def build_laps_table(laps):
    """One row per driver per lap, columnar: {"columns": [...], "rows": [[...], ...]}."""
    rows = []
    for lap in laps.sort_values(['LapNumber', 'Position']).to_dict('records'):
        if pd.isna(lap['LapNumber']):
            continue
        rows.append([
            lap['Driver'],
            lap['Team'],
            int(lap['LapNumber']),
            secs(lap['LapTime']),
            secs(lap.get('Sector1Time')),
            secs(lap.get('Sector2Time')),
            secs(lap.get('Sector3Time')),
            as_str(lap.get('Compound')),
            as_int(lap.get('TyreLife')),
            as_int(lap.get('Stint')),
            as_bool(lap.get('FreshTyre')),
            pd.notna(lap.get('PitInTime')),
            pd.notna(lap.get('PitOutTime')),
            as_int(lap.get('Position')),
            as_str(lap.get('TrackStatus')),
            as_bool(lap.get('IsAccurate')),
            as_bool(lap.get('Deleted')),
        ])
    return {'columns': LAPS_COLUMNS, 'rows': rows}


# ── results.json ──────────────────────────────────────────────────────────────

def build_results(results, quali=False):
    out = []
    for r in results.to_dict('records'):
        color = as_str(r.get('TeamColor'))
        row = {
            'driver':              r['Abbreviation'],
            'number':              as_str(r.get('DriverNumber')),
            'team':                as_str(r.get('TeamName')),
            'team_color':          f'#{color}' if color else None,
            'position':            as_int(r.get('Position')),
            'classified_position': as_str(r.get('ClassifiedPosition')),
            'grid_position':       as_int(r.get('GridPosition')),
            'status':              as_str(r.get('Status')),
            'points':              rnd(r.get('Points'), 1),
            'laps':                as_int(r.get('Laps')),
            'time_s':              secs(r.get('Time')),
        }
        if quali:
            row.update(q1_s=secs(r.get('Q1')), q2_s=secs(r.get('Q2')), q3_s=secs(r.get('Q3')))
        out.append(row)
    return out


# ── track_status.json ─────────────────────────────────────────────────────────

def build_track_status(track_status, lap_ends):
    """Consecutive track status periods; each runs until the next status change."""
    times = [t.total_seconds() for t in track_status['Time']]
    periods = []
    for i, (t, status, message) in enumerate(zip(times, track_status['Status'], track_status['Message'])):
        end = times[i + 1] if i + 1 < len(times) else None
        periods.append({
            'status':       TRACK_STATUS.get(str(status), 'unknown'),
            'message':      as_str(message),
            'start_lap':    lap_at(t, lap_ends),
            'end_lap':      lap_at(end, lap_ends) if end is not None else max(len(lap_ends), 1),
            'start_time_s': round(t, 3),
            'end_time_s':   round(end, 3) if end is not None else None,
        })
    return periods


def build_sc_periods(messages, last_lap):
    """Safety Car / VSC deployments from race control messages, with start and end lap."""
    periods, current = [], None
    for m in messages.to_dict('records'):
        text = str(m.get('Message', '')).upper()
        if 'SAFETY CAR' not in text:
            continue
        lap = as_int(m.get('Lap'))
        virtual = 'VIRTUAL' in text
        if 'DEPLOYED' in text:
            if current is None:
                current = {'type': 'vsc' if virtual else 'sc', 'start_lap': lap, 'end_lap': None}
                periods.append(current)
            elif not virtual:
                current['type'] = 'sc'          # VSC upgraded to a full Safety Car
        elif current and ('IN THIS LAP' in text or 'ENDING' in text):
            current['end_lap'] = lap
            current = None
    for p in periods:
        if p['end_lap'] is None:                # still out at the flag
            p['end_lap'] = last_lap
    return periods


# ── weather.json ──────────────────────────────────────────────────────────────

def weather_summary(weather):
    """The block the old processed JSON carried: conditions at the end of the session."""
    if weather is None or weather.empty:
        return None
    w = weather.iloc[-1]
    return {
        'track_temp':     rnd(w['TrackTemp'], 1),
        'air_temp':       rnd(w['AirTemp'], 1),
        'humidity':       rnd(w['Humidity'], 1),
        'wind_speed':     rnd(w['WindSpeed'], 1),
        'wind_direction': as_int(w['WindDirection']),
        'rainfall':       as_bool(w['Rainfall']),
    }


def build_weather(weather, lap_ends):
    """Per-lap weather: the sample nearest to the moment the leader finished each lap."""
    rows = []
    if weather is not None and not weather.empty:
        times = weather['Time'].dt.total_seconds().to_numpy()
        for i, end in enumerate(lap_ends):
            w = weather.iloc[int(np.abs(times - end).argmin())]
            rows.append([i + 1, rnd(w['TrackTemp'], 1), rnd(w['AirTemp'], 1),
                         rnd(w['Humidity'], 1), as_bool(w['Rainfall'])])
    return {
        'summary': weather_summary(weather),
        'laps': {'columns': ['lap', 'track_temp', 'air_temp', 'humidity', 'rainfall'], 'rows': rows},
    }


# ── pit_loss.json ─────────────────────────────────────────────────────────────

MIN_STINT_GREEN_LAPS = 3


def build_pit_loss(laps):
    """
    Measured cost of a pit stop: (in-lap + out-lap) - 2 x the driver's median green lap
    of the stint that ended with the stop. "Green" = TrackStatus is exactly '1' for the
    whole lap. Stops where either lap saw SC/VSC are reported separately, measured against
    the cars that stayed out on the same two laps; anything else (yellow only, red flag)
    is left out.
    """
    laps = laps.dropna(subset=['LapNumber']).copy()
    laps['_s'] = laps['LapTime'].dt.total_seconds()
    laps['_status'] = laps['TrackStatus'].fillna('').astype(str)
    clean = laps[(laps['_status'] == '1') & laps['PitInTime'].isna()
                 & laps['PitOutTime'].isna() & laps['_s'].notna()]

    # lap N -> (lap N + lap N+1) time of every driver who pitted on neither lap
    on_track = laps[laps['PitInTime'].isna() & laps['PitOutTime'].isna() & laps['_s'].notna()]
    t = on_track.set_index(['Driver', 'LapNumber'])['_s']
    nxt = t.copy()
    nxt.index = nxt.index.set_levels(nxt.index.levels[1] - 1, level=1)
    pair_sums = (t + nxt).dropna()
    stayed_out = {int(n): g for n, g in pair_sums.groupby(level=1)}

    stops = []
    for driver, dl in laps.groupby('Driver'):
        by_lap = {int(l['LapNumber']): l for l in dl.to_dict('records')}
        driver_clean = clean[clean['Driver'] == driver]
        for n, in_lap in sorted(by_lap.items()):
            out_lap = by_lap.get(n + 1)
            if pd.isna(in_lap['PitInTime']) or out_lap is None or pd.isna(out_lap['PitOutTime']):
                continue
            if n == 1 or pd.isna(in_lap['_s']) or pd.isna(out_lap['_s']):
                continue                             # lap 1 = standing start + damage stops
            statuses = in_lap['_status'] + out_lap['_status']
            if in_lap['_status'] == '1' and out_lap['_status'] == '1':
                condition = 'green'
            elif any(c in statuses for c in '467') and '5' not in statuses:
                condition = 'sc'
            else:
                continue
            if condition == 'green':
                ref = driver_clean[driver_clean['Stint'] == in_lap['Stint']]['_s']
                if len(ref) < MIN_STINT_GREEN_LAPS:  # stint too short/neutralised: use the whole race
                    ref = driver_clean['_s']
                if ref.empty:
                    continue
                ref_s = float(ref.median())
            else:
                # Under SC/VSC a green lap is the wrong yardstick: compare with the cars
                # that stayed out on the same two laps.
                pairs = stayed_out.get(n)
                if pairs is None or pairs.empty:
                    continue
                ref_s = float(pairs.median()) / 2
            stops.append({
                'driver':     driver,
                'lap':        n,
                'in_lap_s':   round(in_lap['_s'], 3),
                'out_lap_s':  round(out_lap['_s'], 3),
                'ref_lap_s':  round(ref_s, 3),
                'loss_s':     round(in_lap['_s'] + out_lap['_s'] - 2 * ref_s, 3),
                'condition':  condition,
            })

    stops.sort(key=lambda s: (s['lap'], s['driver']))
    green = [s['loss_s'] for s in stops if s['condition'] == 'green']
    sc = [s['loss_s'] for s in stops if s['condition'] == 'sc']
    return {
        'median_loss_s':    round(float(np.median(green)), 3) if green else None,
        'median_loss_sc_s': round(float(np.median(sc)), 3) if len(sc) >= 2 else None,
        'green_stops':      len(green),
        'sc_stops':         len(sc),
        'stops':            stops,
    }


# ── telemetry resampling (circuit.json, quali/fastest) ────────────────────────

def resample_by_distance(tel, step, linear=(), nearest=()):
    """
    Resample telemetry onto a fixed distance grid (0, step, 2*step, ... metres).
    `linear` columns are interpolated; `nearest` columns (gear, DRS, brake) take the
    value of the closest original sample. Returns {'distance': [...], col: [...]}.
    """
    tel = tel.dropna(subset=['Distance']).drop_duplicates(subset='Distance').sort_values('Distance')
    dist = tel['Distance'].to_numpy(dtype=float)
    if len(dist) < 2:
        return {'distance': [], **{c: [] for c in (*linear, *nearest)}}
    grid = np.arange(0, dist[-1], step)
    out = {'distance': grid}
    for col in linear:
        out[col] = np.interp(grid, dist, tel[col].to_numpy(dtype=float))
    if nearest:
        right = np.clip(np.searchsorted(dist, grid), 1, len(dist) - 1)
        idx = np.where(grid - dist[right - 1] <= dist[right] - grid, right - 1, right)
        for col in nearest:
            out[col] = tel[col].to_numpy()[idx]
    return out


def build_circuit(session):
    """Track outline from the fastest race lap (one point per ~10 m) plus corner markers."""
    lap = session.laps.pick_fastest()
    tel = lap.get_telemetry()
    tel = tel[tel['X'].notna() & tel['Y'].notna()]
    rs = resample_by_distance(tel, 10, linear=('X', 'Y', 'Speed'))
    points = [
        {'x': round(float(x), 1), 'y': round(float(y), 1), 'distance': int(d), 'speed': round(float(s), 1)}
        for d, x, y, s in zip(rs['distance'], rs['X'], rs['Y'], rs['Speed'])
    ]
    corners, rotation = [], None
    try:
        info = session.get_circuit_info()
        rotation = rnd(info.rotation, 1)
        corners = [{
            'number':   as_int(c['Number']),
            'letter':   as_str(c['Letter']) or '',
            'x':        rnd(c['X'], 1),
            'y':        rnd(c['Y'], 1),
            'distance': rnd(c['Distance'], 1),
            'angle':    rnd(c['Angle'], 1),
        } for c in info.corners.to_dict('records')]
    except Exception as e:
        log(f'    circuit_info unavailable ({e}); writing outline without corners')
    return {
        'name':           session.event['EventName'],
        'driver':         lap['Driver'],
        'lap_time_s':     secs(lap['LapTime']),
        'total_distance': points[-1]['distance'] if points else 0,
        'rotation':       rotation,
        'corners':        corners,
        'points':         points,
    }


def build_quali_fastest(session):
    """{driver: fastest-lap telemetry on a 5 m grid} for every driver with a timed lap."""
    laps = session.laps
    segment = {}
    for name, part in zip(('Q1', 'Q2', 'Q3'), laps.split_qualifying_sessions()):
        if part is not None:
            for d, n in zip(part['Driver'], part['LapNumber']):
                segment[(d, n)] = name

    out = {}
    for driver in laps['Driver'].unique():
        try:
            lap = laps.pick_drivers(driver).pick_fastest()
            if lap is None or pd.isna(lap['LapTime']):
                continue
            tel = lap.get_car_data().add_distance()
            tel = tel.assign(Brake=tel['Brake'].astype(int))
            rs = resample_by_distance(tel, 5, linear=('Speed', 'Throttle', 'RPM'),
                                      nearest=('Brake', 'nGear', 'DRS'))
        except Exception as e:
            log(f'    {driver}: no fastest-lap telemetry ({e})')
            continue
        if not len(rs['distance']):
            continue
        out[driver] = {
            'driver':     driver,
            'team':       lap['Team'],
            'lap_time_s': secs(lap['LapTime']),
            'segment':    segment.get((driver, lap['LapNumber'])),
            'compound':   as_str(lap.get('Compound')),
            'step_m':     5,
            'distance':   [int(v) for v in rs['distance']],
            'speed':      [round(float(v), 1) for v in rs['Speed']],
            'throttle':   [int(round(v)) for v in rs['Throttle']],
            'brake':      [int(v) for v in rs['Brake']],
            'n_gear':     [int(v) for v in rs['nGear']],
            'rpm':        [int(round(v)) for v in rs['RPM']],
            'drs':        [int(v) for v in rs['DRS']],
        }
    return out


# ── schedule / event ──────────────────────────────────────────────────────────

def event_sessions(event):
    """{code: start time (aware UTC)} for the sessions of this weekend we know how to build."""
    by_name = {name: code for code, (name, _) in SESSIONS.items()}
    found = {}
    for i in range(1, 6):
        name = event.get(f'Session{i}')
        start = event.get(f'Session{i}DateUtc')
        code = by_name.get(SESSION_ALIASES.get(name, name))
        if code and start is not None and pd.notna(start):
            ts = pd.Timestamp(start)
            found[code] = (ts.tz_localize('UTC') if ts.tzinfo is None else ts.tz_convert('UTC')).to_pydatetime()
    return found


def completed_sessions(event, now=None):
    """Session codes whose start + 3h is in the past, in build order (Q, SQ, S, R)."""
    now = now or datetime.now(timezone.utc)
    starts = event_sessions(event)
    return [c for c in SESSIONS if c in starts and starts[c] + COMPLETED_AFTER < now]


def built_sessions(event_dir):
    """Session codes already on disk. results.json is written last, so it marks a full build."""
    return [c for c, (_, folder) in SESSIONS.items() if (event_dir / folder / 'results.json').exists()]


def write_event(event_dir, year, event, total_laps=None, circuit=None):
    prev = read_json(event_dir / 'event.json') or {}
    write_json(event_dir / 'event.json', {
        'year':       year,
        'round':      int(event['RoundNumber']),
        'name':       event['EventName'],
        'country':    event['Country'],
        'location':   event['Location'],
        'circuit':    circuit or prev.get('circuit'),
        'date':       pd.Timestamp(event['EventDate']).strftime('%Y-%m-%d'),
        'format':     event['EventFormat'],
        'total_laps': total_laps or prev.get('total_laps'),
        'sessions':   {c: utc_iso(t) for c, t in event_sessions(event).items()},
        'built_at':   now_iso(),
    })


def rebuild_manifest(out_dir=OUT_DIR):
    """manifest.json from the event folders on disk, newest first."""
    events = []
    for path in out_dir.glob('*/*/event.json'):
        ev = read_json(path)
        sessions = built_sessions(path.parent)
        if not ev or not sessions:
            continue
        events.append({
            'year': ev['year'], 'round': ev['round'], 'name': ev['name'],
            'country': ev['country'], 'location': ev['location'], 'date': ev['date'],
            'format': ev['format'], 'sessions': sessions, 'built_at': ev['built_at'],
        })
    events.sort(key=lambda e: (e['year'], e['round']), reverse=True)
    prev = read_json(out_dir / 'manifest.json') or {}
    if prev.get('events') == events and prev.get('schema_version') == SCHEMA_VERSION:
        return prev                              # nothing changed: keep generated_at, no git diff
    manifest = {'generated_at': now_iso(), 'schema_version': SCHEMA_VERSION, 'events': events}
    write_json(out_dir / 'manifest.json', manifest)
    return manifest


# ── building one session ──────────────────────────────────────────────────────

def load_session(year, round_num, code):
    """Loaded FastF1 session, or None when F1 has not published the data yet."""
    import fastf1
    try:
        session = fastf1.get_session(year, round_num, code)
        session.load(laps=True, telemetry=True, weather=True, messages=True)
        laps = session.laps
    except Exception as e:
        log(f'  {year} R{round_num} {code}: data is not out yet ({type(e).__name__}: {e}) - skipped. '
            "F1's archive has needed a login since Oct 2026, so only sessions already in FASTF1_CACHE build.")
        return None
    if laps is None or laps.empty:
        log(f'  {year} R{round_num} {code}: session loaded but has no laps, data is not out yet - skipped')
        return None
    return session


def build_race_like(session, year, round_num, event_dir, folder, is_race):
    laps = session.laps
    total_laps = int(getattr(session, 'total_laps', 0) or 0) or int(laps['LapNumber'].max())
    lap_ends = leader_lap_ends(laps)
    out = event_dir / folder
    weather = session.weather_data

    write_json(out / 'replay.json', {
        'year':       year,
        'round':      round_num,
        'name':       session.event['EventName'],
        'circuit':    session.event['Location'],
        'date':       session.event['EventDate'].isoformat(),
        'total_laps': total_laps,
        'weather':    weather_summary(weather),
        'laps':       build_replay_laps(laps, total_laps),
    })
    write_json(out / 'laps.json', build_laps_table(laps))
    write_json(out / 'track_status.json', {
        'periods':    build_track_status(session.track_status, lap_ends),
        'sc_periods': build_sc_periods(session.race_control_messages, total_laps),
    })
    write_json(out / 'weather.json', build_weather(weather, lap_ends))
    write_json(out / 'pit_loss.json', build_pit_loss(laps))
    if is_race:
        try:
            write_json(event_dir / 'circuit.json', build_circuit(session))
        except Exception as e:
            log(f'    circuit.json skipped: {e}')
    write_json(out / 'results.json', build_results(session.results))      # last: marks the build complete
    return total_laps


def build_quali_like(session, event_dir, folder):
    out = event_dir / folder
    for driver, data in build_quali_fastest(session).items():
        path = out / 'fastest' / f'{driver}.json'
        write_json(path, data)
        if path.stat().st_size > 60_000:
            log(f'    WARNING {path.name} is {path.stat().st_size // 1024} KB (budget 60 KB)')
    write_json(out / 'results.json', build_results(session.results, quali=True))


def build_event(year, event, codes, force=False):
    """Build the given session codes for one event. Returns (built codes, failed codes)."""
    round_num = int(event['RoundNumber'])
    event_dir = OUT_DIR / str(year) / str(round_num)
    done = built_sessions(event_dir)
    built, failed = [], []
    for code in codes:
        if code in done and not force:
            continue
        log(f'  {year} R{round_num} {code}: loading...')
        session = load_session(year, round_num, code)
        if session is None:
            continue
        try:
            folder = SESSIONS[code][1]
            total_laps = None
            if code in ('R', 'S'):
                laps_run = build_race_like(session, year, round_num, event_dir, folder, is_race=code == 'R')
                total_laps = laps_run if code == 'R' else None
            else:
                build_quali_like(session, event_dir, folder)
            circuit = (session.session_info.get('Meeting', {}).get('Circuit', {}) or {}).get('ShortName')
            write_event(event_dir, year, event, total_laps=total_laps, circuit=circuit)
            built.append(code)
            log(f'  {year} R{round_num} {code}: built')
        except Exception:
            failed.append(code)
            log(f'  {year} R{round_num} {code}: FAILED\n{traceback.format_exc()}')
    return built, failed


# ── git change summary (used by the GitHub workflow) ──────────────────────────

def describe_changes(name_status_lines):
    """
    From `git diff --cached --name-status` lines, return (commit message, new races).
    New races are 'year/round' strings whose race/results.json was added.
    """
    folders = {folder: code for code, (_, folder) in SESSIONS.items()}
    events, new_races = {}, []
    for line in name_status_lines:
        parts = line.split()
        if len(parts) < 2:
            continue
        bits = parts[-1].replace('\\', '/').split('frontend/public/data/')[-1].split('/')
        if len(bits) < 3 or not (bits[0].isdigit() and bits[1].isdigit()):
            continue
        key = (int(bits[0]), int(bits[1]))
        events.setdefault(key, set())
        if bits[2] in folders:
            events[key].add(folders[bits[2]])
            if parts[0] == 'A' and bits[2:] == ['race', 'results.json']:
                new_races.append(f'{key[0]}/{key[1]}')
    labels = [
        f'{y} R{r} {",".join(c for c in SESSIONS if c in codes)}'.strip()
        for (y, r), codes in sorted(events.items())
    ]
    if not labels:
        message = 'data: refresh manifest'
    elif len(labels) <= 3:
        message = 'data: ' + '; '.join(labels)
    else:
        message = f'data: {len(labels)} events ({labels[0]} to {labels[-1]})'
    return message, new_races


# ── CLI ───────────────────────────────────────────────────────────────────────

def main(argv=None):
    p = argparse.ArgumentParser(description='Build static race data for Pitlane Live')
    p.add_argument('--year', type=int, action='append', dest='years',
                   help='Season to build (repeatable). Defaults to the current year.')
    p.add_argument('--round', type=int, dest='round_num', help='Only this round (needs one --year).')
    p.add_argument('--force', action='store_true', help='Rebuild sessions that already exist.')
    p.add_argument('--skip-existing', action='store_true',
                   help='Skip sessions already on disk. This is the default; the flag exists for backfill scripts.')
    p.add_argument('--sessions', help='Comma list of R,Q,S,SQ. Default: every session of the weekend.')
    p.add_argument('--manifest-only', action='store_true', help='Only rebuild manifest.json from disk.')
    p.add_argument('--describe-changes', action='store_true',
                   help='Read `git diff --cached --name-status` on stdin, print the commit message.')
    args = p.parse_args(argv)

    if args.describe_changes:
        message, new_races = describe_changes(sys.stdin.read().splitlines())
        print(message)
        if os.getenv('GITHUB_OUTPUT'):
            with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
                f.write(f'message={message}\nnew_races={" ".join(new_races)}\n')
        return 0

    if args.manifest_only:
        log(f'manifest: {len(rebuild_manifest()["events"])} events')
        return 0

    years = args.years or [datetime.now(timezone.utc).year]
    if args.round_num and len(years) != 1:
        p.error('--round needs exactly one --year')
    wanted = [s.strip().upper() for s in args.sessions.split(',')] if args.sessions else list(SESSIONS)
    unknown = [s for s in wanted if s not in SESSIONS]
    if unknown:
        p.error(f'unknown session(s): {",".join(unknown)}')

    import fastf1
    cache_dir = Path(os.getenv('FASTF1_CACHE') or ROOT / '.fastf1-cache')
    cache_dir.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(cache_dir))

    total_built, total_failed = 0, 0
    for year in years:
        log(f'== {year} ==')
        schedule = fastf1.get_event_schedule(year, include_testing=False)
        for _, event in schedule.iterrows():
            round_num = int(event['RoundNumber'])
            if args.round_num and round_num != args.round_num:
                continue
            codes = [c for c in completed_sessions(event) if c in wanted]
            if not codes:
                if args.round_num:
                    log(f'  {year} R{round_num}: no completed sessions yet')
                continue
            built, failed = build_event(year, event, codes, force=args.force)
            total_built += len(built)
            total_failed += len(failed)

    manifest = rebuild_manifest()
    log(f'done: {total_built} session(s) built, {total_failed} failed, manifest has {len(manifest["events"])} events')
    return 1 if total_failed else 0


if __name__ == '__main__':
    sys.exit(main())
