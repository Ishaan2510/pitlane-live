import fastf1
import pandas as pd
from pathlib import Path
import json
from datetime import datetime
import numpy as np
import threading
import requests


# Setup FastF1 cache
CACHE_DIR = Path(__file__).parent.parent.parent / 'fastf1_cache'
CACHE_DIR.mkdir(exist_ok=True)
fastf1.Cache.enable_cache(str(CACHE_DIR))

OPENF1_BASE = 'https://api.openf1.org/v1'

class FastF1Service:
    """Service to fetch and process F1 race data from FastF1"""
    
    def __init__(self):
        self.processed_cache_dir = CACHE_DIR / 'processed'
        self.processed_cache_dir.mkdir(exist_ok=True)
        self._session_cache = {}
        self._global_lock = threading.Lock()
        self._race_locks = {}        # per-race locks

    def _get_race_lock(self, key):
        """Get or create a lock for a specific race"""
        with self._global_lock:
            if key not in self._race_locks:
                self._race_locks[key] = threading.Lock()
            return self._race_locks[key]

    def _get_cached_rounds(self, year):
        """Scan fastf1_cache folder to find which rounds are actually downloaded"""
        available_rounds = set()
        year_dir = CACHE_DIR / str(year)
        
        if not year_dir.exists():
            return available_rounds
        
        for race_dir in year_dir.iterdir():
            if not race_dir.is_dir():
                continue
            race_session_dirs = list(race_dir.glob('*_Race'))
            for session_dir in race_session_dirs:
                files = list(session_dir.glob('*.ff1pkl'))
                if len(files) >= 3:
                    available_rounds.add(race_dir.name)
        
        return available_rounds

    def get_available_races(self, year=2024):
        """Get list of races that are ACTUALLY cached and ready to replay"""
        try:
            schedule = fastf1.get_event_schedule(year)
            cached_rounds = self._get_cached_rounds(year)
            
            races = []
            for idx, event in schedule.iterrows():
                if event['EventFormat'] == 'testing':
                    continue

                round_num  = int(event['RoundNumber'])
                event_date = event['EventDate']
                
                is_cached = any(
                    f"{event_date.strftime('%Y-%m-%d')}" in folder_name
                    for folder_name in cached_rounds
                ) if pd.notna(event_date) else False

                is_processed = (
                    self.processed_cache_dir / f"{year}_R{round_num}_processed.json"
                ).exists()

                if is_cached or is_processed:
                    races.append({
                        'round':    round_num,
                        'name':     event['EventName'],
                        'location': event['Location'],
                        'country':  event['Country'],
                        'date':     event_date.isoformat() if pd.notna(event_date) else None,
                        'year':     year,
                        'cached':   True,
                    })

            print(f"Found {len(races)} cached races for {year}")
            return races

        except Exception as e:
            print(f"Error fetching schedule: {e}")
            return []

    def load_race_session(self, year, race_round, session_type='Race'):
        """Load a race session — uses in-memory cache to avoid reloading"""
        key = f"{year}_R{race_round}_{session_type}"
        
        if key in self._session_cache:
            return self._session_cache[key]
        
        lock = self._get_race_lock(f"session_{key}")
        with lock:
            if key in self._session_cache:
                return self._session_cache[key]
            
            try:
                print(f"Loading {year} Round {race_round} {session_type}...")
                session = fastf1.get_session(year, race_round, session_type)
                session.load(telemetry=False)
                self._session_cache[key] = session
                return session
            except Exception as e:
                print(f"Error loading session: {e}")
                return None

    def get_circuit_data(self, year, race_round):
        """Get circuit coordinates and track info"""
        cache_file = self.processed_cache_dir / f"{year}_R{race_round}_circuit.json"
        
        if cache_file.exists():
            with open(cache_file, 'r') as f:
                return json.load(f)
        
        lock = self._get_race_lock(f"circuit_{year}_R{race_round}")
        with lock:
            # Double check after lock
            if cache_file.exists():
                with open(cache_file, 'r') as f:
                    return json.load(f)

            session = self.load_race_session(year, race_round)
            if not session:
                return None
            
            try:
                laps = session.laps
                first_valid_lap = laps[laps['LapNumber'] == 1].iloc[0]
                telemetry = first_valid_lap.get_telemetry()
                
                coords = []
                for _, point in telemetry.iterrows():
                    if pd.notna(point['X']) and pd.notna(point['Y']):
                        coords.append({
                            'x':        float(point['X']),
                            'y':        float(point['Y']),
                            'distance': float(point['Distance']) if pd.notna(point['Distance']) else 0
                        })
                
                circuit_data = {
                    'coordinates':    coords,
                    'total_distance': max(c['distance'] for c in coords) if coords else 0,
                    'name':           session.event['EventName']
                }
                
                with open(cache_file, 'w') as f:
                    json.dump(circuit_data, f)
                
                return circuit_data
            except Exception as e:
                print(f"Error getting circuit data: {e}")
                return None

    def get_weather_data(self, year, race_round):
        """Get weather information — reuses already-loaded session"""
        session = self.load_race_session(year, race_round)
        if not session:
            return None
        
        try:
            weather = session.weather_data
            if weather.empty:
                return None
            
            latest = weather.iloc[-1]
            return {
                'track_temp':     float(latest['TrackTemp'])    if pd.notna(latest['TrackTemp'])     else None,
                'air_temp':       float(latest['AirTemp'])      if pd.notna(latest['AirTemp'])       else None,
                'humidity':       float(latest['Humidity'])     if pd.notna(latest['Humidity'])      else None,
                'wind_speed':     float(latest['WindSpeed'])    if pd.notna(latest['WindSpeed'])     else None,
                'wind_direction': int(latest['WindDirection'])  if pd.notna(latest['WindDirection']) else None,
                'rainfall':       bool(latest['Rainfall'])      if pd.notna(latest['Rainfall'])      else False
            }
        except Exception as e:
            print(f"Error getting weather: {e}")
            return None

    def process_race_telemetry(self, year, race_round):
        """Process full race telemetry into lap-by-lap data"""
        cache_file = self.processed_cache_dir / f"{year}_R{race_round}_processed.json"
        
        # Return immediately if already processed
        if cache_file.exists():
            print(f"Loading from cache: {cache_file}")
            with open(cache_file, 'r') as f:
                return json.load(f)
        
        # Lock per race so only ONE thread processes it
        lock = self._get_race_lock(f"telemetry_{year}_R{race_round}")
        with lock:
            # Double-check after acquiring lock
            if cache_file.exists():
                print(f"Loading from cache: {cache_file}")
                with open(cache_file, 'r') as f:
                    return json.load(f)

            session = self.load_race_session(year, race_round)
            if not session:
                return None
            
            print(f"Processing telemetry for {year} R{race_round}...")
            
            race_data = {
                'year':       year,
                'round':      race_round,
                'name':       session.event['EventName'],
                'circuit':    session.event['Location'],
                'date':       session.event['EventDate'].isoformat(),
                'total_laps': int(session.total_laps) if hasattr(session, 'total_laps') else 0,
                'laps':       []
            }
            
            laps = session.laps.copy()
            for lap_number in range(1, race_data['total_laps'] + 1):
                lap_data = self._build_lap(laps, lap_number)
                race_data['laps'].append(lap_data)
            
            # Write to a temp file first, then rename — prevents corrupt reads
            tmp_file = cache_file.with_suffix('.tmp')
            with open(tmp_file, 'w') as f:
                json.dump(race_data, f, indent=2)
            tmp_file.rename(cache_file)
            
            print(f"✅ Processed {len(race_data['laps'])} laps → {cache_file.name}")
            return race_data

    def _build_lap(self, laps, lap_number):
        """Build a single lap with telemetry data"""
        lap_laps = laps[laps['LapNumber'] == lap_number]
        
        drivers = []
        for idx, lap in lap_laps.iterrows():
            if pd.isna(lap['LapTime']):
                continue
            
            try:
                telemetry    = lap.get_telemetry()
                avg_speed    = telemetry['Speed'].mean() if 'Speed' in telemetry else None
                max_speed    = telemetry['Speed'].max()  if 'Speed' in telemetry else None
                lap_distance = telemetry['Distance'].iloc[-1] if 'Distance' in telemetry and len(telemetry) > 0 else 0
            except:
                avg_speed    = None
                max_speed    = None
                lap_distance = 0
            
            driver_data = {
                'driver':    lap['Driver'],
                'team':      lap['Team'],
                'position':  int(lap['Position'])    if pd.notna(lap['Position'])  else None,
                'lap_time':  str(lap['LapTime'])     if pd.notna(lap['LapTime'])   else None,
                'compound':  lap['Compound']         if pd.notna(lap['Compound'])  else 'UNKNOWN',
                'tire_life': int(lap['TyreLife'])    if pd.notna(lap['TyreLife'])  else 0,
                'pit_out':   bool(lap['PitOutTime']) if 'PitOutTime' in lap and pd.notna(lap['PitOutTime']) else False,
                'pit_in':    bool(lap['PitInTime'])  if 'PitInTime'  in lap and pd.notna(lap['PitInTime'])  else False,
                'distance':  float(lap_distance)     if lap_distance else 0,
                'avg_speed': float(avg_speed)        if avg_speed is not None and pd.notna(avg_speed) else None,
                'max_speed': float(max_speed)        if max_speed is not None and pd.notna(max_speed) else None
            }
            drivers.append(driver_data)
        
        drivers.sort(key=lambda x: x['position'] if x['position'] else 999)
        
        if drivers and drivers[0]['position'] == 1:
            for i, driver in enumerate(drivers):
                driver['gap'] = 'LEADER' if i == 0 else f"+{i * 0.5:.1f}s"
        
        return {
            'lap_number': lap_number,
            'drivers':    drivers
        }

    def get_race_summary(self, year, race_round):
        """Get quick race summary"""
        try:
            session = self.load_race_session(year, race_round)
            if not session:
                return None
            
            results = session.results
            return {
                'name':   session.event['EventName'],
                'date':   session.event['EventDate'].isoformat(),
                'winner': results.iloc[0]['Abbreviation'] if len(results) > 0 else None,
                'podium': [results.iloc[i]['Abbreviation'] for i in range(min(3, len(results)))]
            }
        except Exception as e:
            print(f"Error getting summary: {e}")
            return None

    def get_driver_lap_telemetry(self, year, race_round, driver_code, lap_number):
        """
        Fetch speed telemetry for ONE driver on ONE lap, on demand.
        Called by /api/replay/telemetry when user selects a driver in the UI.
        """
        cache_key = self.processed_cache_dir / f"{year}_R{race_round}_tel_{driver_code}_L{lap_number}.json"

        if cache_key.exists():
            with open(cache_key) as f:
                return json.load(f)

        try:
            session = fastf1.get_session(year, race_round, 'Race')
            session.load(telemetry=False)

            laps = session.laps
            lap = laps[
                (laps['Driver'] == driver_code) &
                (laps['LapNumber'] == lap_number)
            ]
            if lap.empty:
                return None

            tel = lap.iloc[0].get_telemetry()
            result = {
                'driver':    driver_code,
                'lap':       lap_number,
                'avg_speed': round(float(tel['Speed'].mean()), 1) if 'Speed' in tel else None,
                'max_speed': round(float(tel['Speed'].max()),  1) if 'Speed' in tel else None,
            }

            with open(cache_key, 'w') as f:
                json.dump(result, f)

            return result

        except Exception as e:
            print(f"[get_driver_lap_telemetry] {e}")
            return None

    def get_live_session_key(self):
        """Get the session_key for the current or most recent live session."""
        try:
            r = requests.get(f'{OPENF1_BASE}/sessions?session_type=Race', timeout=5)
            sessions = r.json()
            if not sessions:
                return None
            return sessions[-1]['session_key']
        except Exception as e:
            print(f"[get_live_session_key] {e}")
            return None

    def get_live_positions(self, session_key=None):
        """
        Current driver positions from OpenF1.
        Returns a list ordered by position.
        """
        if not session_key:
            session_key = self.get_live_session_key()
        if not session_key:
            return []

        try:
            r = requests.get(
                f'{OPENF1_BASE}/position?session_key={session_key}',
                timeout=5
            )
            raw = r.json()

            # Keep only the latest entry per driver
            latest = {}
            for entry in raw:
                drv = entry['driver_number']
                if drv not in latest or entry['date'] > latest[drv]['date']:
                    latest[drv] = entry

            return sorted(latest.values(), key=lambda x: x.get('position', 99))

        except Exception as e:
            print(f"[get_live_positions] {e}")
            return []

    def get_live_car_data(self, session_key=None, driver_number=None):
        """
        Latest telemetry for a specific driver: speed, gear, throttle, brake, DRS.
        """
        if not session_key:
            session_key = self.get_live_session_key()
        if not session_key:
            return None

        try:
            url = f'{OPENF1_BASE}/car_data?session_key={session_key}'
            if driver_number:
                url += f'&driver_number={driver_number}'

            r = requests.get(url, timeout=5)
            data = r.json()
            if not data:
                return None

            latest = data[-1]
            return {
                'speed':    latest.get('speed'),
                'gear':     latest.get('n_gear'),
                'throttle': latest.get('throttle'),
                'brake':    latest.get('brake'),
                'drs':      latest.get('drs'),
            }
        except Exception as e:
            print(f"[get_live_car_data] {e}")
            return None

    def get_live_intervals(self, session_key=None):
        """
        Real time gaps between drivers (the +3.2s you see on TV).
        OpenF1 /intervals endpoint, updated every few seconds.
        """
        if not session_key:
            session_key = self.get_live_session_key()
        if not session_key:
            return {}

        try:
            r = requests.get(
                f'{OPENF1_BASE}/intervals?session_key={session_key}',
                timeout=5
            )
            raw = r.json()

            latest = {}
            for entry in raw:
                drv = entry['driver_number']
                if drv not in latest or entry['date'] > latest[drv]['date']:
                    latest[drv] = entry

            return {
                drv: {
                    'gap_to_leader': entry.get('gap_to_leader'),
                    'interval':      entry.get('interval'),
                }
                for drv, entry in latest.items()
            }
        except Exception as e:
            print(f"[get_live_intervals] {e}")
            return {}

    def get_live_pit_stops(self, session_key=None):
        """All pit stops so far in the current session."""
        if not session_key:
            session_key = self.get_live_session_key()
        if not session_key:
            return []

        try:
            r = requests.get(
                f'{OPENF1_BASE}/pit?session_key={session_key}',
                timeout=5
            )
            return r.json()
        except Exception as e:
            print(f"[get_live_pit_stops] {e}")
            return []

    def get_live_race_control(self, session_key=None):
        """Race control messages: safety car, red flag, VSC, track limits, etc."""
        if not session_key:
            session_key = self.get_live_session_key()
        if not session_key:
            return []

        try:
            r = requests.get(
                f'{OPENF1_BASE}/race_control?session_key={session_key}',
                timeout=5
            )
            return r.json()
        except Exception as e:
            print(f"[get_live_race_control] {e}")
            return []

    def get_live_stints(self, session_key=None):
        """Current tyre stints (compound, age) per driver."""
        if not session_key:
            session_key = self.get_live_session_key()
        if not session_key:
            return {}

        try:
            r = requests.get(
                f'{OPENF1_BASE}/stints?session_key={session_key}',
                timeout=5
            )
            raw = r.json()

            # Latest stint per driver
            stints = {}
            for entry in raw:
                drv = entry['driver_number']
                if drv not in stints or entry.get('stint_number', 0) > stints[drv].get('stint_number', 0):
                    stints[drv] = entry

            return {
                drv: {
                    'compound': s.get('compound'),
                    'tyre_age': s.get('tyre_age_at_start', 0),
                    'stint_no': s.get('stint_number'),
                }
                for drv, s in stints.items()
            }
        except Exception as e:
            print(f"[get_live_stints] {e}")
            return {}

    def get_live_full_state(self):
        """
        One call that assembles everything the frontend needs for live mode:
        positions + intervals + stints + latest race control message.
        The frontend polls this every 3 seconds via SSE or short polling.
        """
        session_key = self.get_live_session_key()
        if not session_key:
            return {'error': 'No live session', 'session_key': None}

        positions = self.get_live_positions(session_key)
        intervals = self.get_live_intervals(session_key)
        stints    = self.get_live_stints(session_key)
        rc_msgs   = self.get_live_race_control(session_key)
        latest_rc = rc_msgs[-1] if rc_msgs else None

        # Driver number → abbreviation/team mapping from OpenF1
        try:
            drv_r = requests.get(
                f'{OPENF1_BASE}/drivers?session_key={session_key}',
                timeout=5
            )
            drivers_meta = {
                str(d['driver_number']): {
                    'code': d.get('name_acronym', '???'),
                    'team': d.get('team_name', 'Unknown'),
                }
                for d in drv_r.json()
            }
        except:
            drivers_meta = {}

        # Merge everything into one list
        merged = []
        for pos in positions:
            drv_num  = str(pos['driver_number'])
            meta     = drivers_meta.get(drv_num, {})
            gap_info = intervals.get(pos['driver_number'], {})
            stint    = stints.get(pos['driver_number'], {})

            merged.append({
                'driver_number': pos['driver_number'],
                'driver':        meta.get('code', drv_num),
                'team':          meta.get('team', 'Unknown'),
                'position':      pos.get('position'),
                'gap':           gap_info.get('gap_to_leader') or 'LEADER',
                'interval':      gap_info.get('interval'),
                'compound':      stint.get('compound', 'UNKNOWN'),
                'tire_age':      stint.get('tyre_age', 0),
            })

        return {
            'session_key':  session_key,
            'drivers':      merged,
            'race_control': latest_rc,
            'timestamp':    datetime.utcnow().isoformat(),
        }

fastf1_service = FastF1Service()
