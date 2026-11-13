"""FastF1 source. The F1 archive has needed a login since Oct 2026, so in practice this
only serves sessions that are already in the local FastF1 cache (see session_is_cached)."""
import os
from pathlib import Path

import pandas as pd

from .base import GRID_COLUMNS, PIT_COLUMNS, POSITION_COLUMNS


def cache_dir():
    return Path(os.getenv('FASTF1_CACHE') or Path(__file__).resolve().parents[2] / '.fastf1-cache')


def enable_cache():
    import fastf1
    cache_dir().mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(cache_dir()))


def session_is_cached(year, round_num, code):
    """True when FastF1 already has this session's parsed timing data on disk."""
    import fastf1
    try:
        api_path = fastf1.get_session(year, round_num, code).api_path   # /static/2025/<event>/<session>/
    except Exception:
        return False
    folder = cache_dir() / api_path.replace('/static/', '').strip('/')
    return (folder / '_extended_timing_data.ff1pkl').exists()


class FastF1Source:
    name = 'fastf1'

    def __init__(self, year, round_num, code, log=print, offline=False):
        self.year, self.round_num, self.code = year, round_num, code
        self.log = log
        self.offline = offline        # never touch the network for the session load
        self.session = None

    def load(self):
        import fastf1
        tag = f'{self.year} R{self.round_num} {self.code}'
        fastf1.Cache.offline_mode(self.offline)
        try:
            session = fastf1.get_session(self.year, self.round_num, self.code)
            session.load(laps=True, telemetry=True, weather=True, messages=True)
            laps = session.laps
        except Exception as e:
            self.log(f'  {tag}: FastF1 has no data ({type(e).__name__}: {e}) - skipped')
            return False
        finally:
            fastf1.Cache.offline_mode(False)
        if laps is None or laps.empty:
            self.log(f'  {tag}: session loaded but has no laps, data is not out yet - skipped')
            return False
        self.session = session
        return True

    # ── frames the builders use ───────────────────────────────────────────────
    def event(self):
        laps = self.session.laps
        total = int(getattr(self.session, 'total_laps', 0) or 0) or int(laps['LapNumber'].max())
        circuit = (self.session.session_info.get('Meeting', {}).get('Circuit', {}) or {}).get('ShortName')
        return pd.Series({'circuit': circuit, 'total_laps': total})

    def laps(self):
        return self.session.laps

    def results(self):
        return self.session.results

    def track_status(self):
        return self.session.track_status

    def race_control(self):
        return self.session.race_control_messages

    def weather(self):
        return self.session.weather_data

    def fastest_lap_telemetry(self, driver):
        laps = self.session.laps
        lap = laps.pick_drivers(driver).pick_fastest()
        if lap is None or pd.isna(lap['LapTime']):
            return None
        segment = None
        for name, part in zip(('Q1', 'Q2', 'Q3'), laps.split_qualifying_sessions()):
            if part is not None and ((part['Driver'] == driver) & (part['LapNumber'] == lap['LapNumber'])).any():
                segment = name
        tel = lap.get_car_data().add_distance()
        tel = tel.assign(Brake=tel['Brake'].astype(int))
        info = {'team': lap['Team'], 'lap_time': lap['LapTime'], 'segment': segment,
                'compound': lap.get('Compound')}
        return info, tel

    def circuit_outline(self):
        # Fastest lap first; some cars have no telemetry in the archive, so fall through to
        # the next fastest driver until one gives a usable outline.
        timed = self.session.laps.dropna(subset=['LapTime']).sort_values('LapTime')
        for _, lap in timed.drop_duplicates(subset='Driver').iterrows():
            try:
                tel = lap.get_telemetry()
                tel = tel[tel['X'].notna() & tel['Y'].notna()]
            except Exception:
                continue
            if len(tel) and tel['Distance'].max() >= 1000:
                tel.attrs = {'driver': lap['Driver'], 'lap_time': lap['LapTime']}
                return tel
        raise ValueError('no lap with position telemetry')

    def circuit_info(self):
        info = self.session.get_circuit_info()
        return info.corners, info.rotation

    # ── the rest of the interface, derived from the frames above ──────────────
    def drivers(self):
        r = self.session.results
        return pd.DataFrame({'Driver': r['Abbreviation'], 'DriverNumber': r['DriverNumber'],
                             'Team': r['TeamName'], 'TeamColor': r['TeamColor']}).reset_index(drop=True)

    def stints(self):
        g = self.session.laps.dropna(subset=['Stint']).groupby(['Driver', 'Stint'])
        out = g.agg(Compound=('Compound', 'first'), LapStart=('LapNumber', 'min'),
                    LapEnd=('LapNumber', 'max'), FirstLife=('TyreLife', 'first')).reset_index()
        out['TyreAgeAtStart'] = out.pop('FirstLife') - 1
        return out

    def pits(self):
        laps = self.session.laps
        return pd.DataFrame(laps[laps['PitInTime'].notna()][PIT_COLUMNS]).reset_index(drop=True)

    def grid(self):
        r = self.session.results
        return pd.DataFrame({'Driver': r['Abbreviation'], 'GridPosition': r['GridPosition']})[GRID_COLUMNS]

    def positions_at_lap_end(self):
        return pd.DataFrame(self.session.laps[POSITION_COLUMNS]).dropna().reset_index(drop=True)
