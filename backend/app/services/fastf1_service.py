import fastf1
import pandas as pd
from pathlib import Path
import json
from datetime import datetime
import numpy as np

# Setup FastF1 cache
CACHE_DIR = Path(__file__).parent.parent.parent / 'fastf1_cache'
CACHE_DIR.mkdir(exist_ok=True)
fastf1.Cache.enable_cache(str(CACHE_DIR))

class FastF1Service:
    """Service to fetch and process F1 race data from FastF1"""
    
    def __init__(self):
        self.processed_cache_dir = CACHE_DIR / 'processed'
        self.processed_cache_dir.mkdir(exist_ok=True)
    
    def get_available_races(self, year=2024):
        """Get list of available races for a year"""
        try:
            schedule = fastf1.get_event_schedule(year)
            races = []
            
            for idx, event in schedule.iterrows():
                if event['EventFormat'] != 'testing':
                    races.append({
                        'round': event['RoundNumber'],
                        'name': event['EventName'],
                        'location': event['Location'],
                        'country': event['Country'],
                        'date': event['EventDate'].isoformat() if pd.notna(event['EventDate']) else None,
                        'circuit': event['EventName'],
                        'year': year
                    })
            
            return races
        except Exception as e:
            print(f"Error fetching schedule: {e}")
            return []
    
    def load_race_session(self, year, race_round, session_type='Race'):
        """Load a race session from FastF1"""
        try:
            print(f"Loading {year} Round {race_round} {session_type}...")
            session = fastf1.get_session(year, race_round, session_type)
            session.load()
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
        
        session = self.load_race_session(year, race_round)
        if not session:
            return None
        
        # Get circuit coordinates from any driver's lap
        try:
            laps = session.laps
            first_valid_lap = laps[laps['LapNumber'] == 1].iloc[0]
            telemetry = first_valid_lap.get_telemetry()
            
            # Extract track coordinates
            coords = []
            for _, point in telemetry.iterrows():
                if pd.notna(point['X']) and pd.notna(point['Y']):
                    coords.append({
                        'x': float(point['X']),
                        'y': float(point['Y']),
                        'distance': float(point['Distance']) if pd.notna(point['Distance']) else 0
                    })
            
            circuit_data = {
                'coordinates': coords,
                'total_distance': max(c['distance'] for c in coords) if coords else 0,
                'name': session.event['EventName']
            }
            
            # Save to cache
            with open(cache_file, 'w') as f:
                json.dump(circuit_data, f)
            
            return circuit_data
        except Exception as e:
            print(f"Error getting circuit data: {e}")
            return None
    
    def get_weather_data(self, year, race_round):
        """Get weather information for the race"""
        session = self.load_race_session(year, race_round)
        if not session:
            return None
        
        try:
            weather = session.weather_data
            if weather.empty:
                return None
            
            # Get average weather conditions
            latest = weather.iloc[-1]
            return {
                'track_temp': float(latest['TrackTemp']) if pd.notna(latest['TrackTemp']) else None,
                'air_temp': float(latest['AirTemp']) if pd.notna(latest['AirTemp']) else None,
                'humidity': float(latest['Humidity']) if pd.notna(latest['Humidity']) else None,
                'wind_speed': float(latest['WindSpeed']) if pd.notna(latest['WindSpeed']) else None,
                'wind_direction': int(latest['WindDirection']) if pd.notna(latest['WindDirection']) else None,
                'rainfall': bool(latest['Rainfall']) if pd.notna(latest['Rainfall']) else False
            }
        except Exception as e:
            print(f"Error getting weather: {e}")
            return None
    
    def process_race_telemetry(self, year, race_round):
        """Process full race telemetry into lap-by-lap data"""
        cache_file = self.processed_cache_dir / f"{year}_R{race_round}_processed.json"
        
        if cache_file.exists():
            print(f"Loading from cache: {cache_file}")
            with open(cache_file, 'r') as f:
                return json.load(f)
        
        session = self.load_race_session(year, race_round)
        if not session:
            return None
        
        print("Processing telemetry...")
        
        race_data = {
            'year': year,
            'round': race_round,
            'name': session.event['EventName'],
            'circuit': session.event['Location'],
            'date': session.event['EventDate'].isoformat(),
            'total_laps': int(session.total_laps) if hasattr(session, 'total_laps') else 0,
            'laps': []
        }
        
        laps = session.laps
        
        for lap_number in range(1, race_data['total_laps'] + 1):
            lap_data = self._process_lap(laps, lap_number)
            race_data['laps'].append(lap_data)
        
        with open(cache_file, 'w') as f:
            json.dump(race_data, f, indent=2)
        
        print(f"✅ Processed {len(race_data['laps'])} laps")
        return race_data
    
    def _process_lap(self, laps, lap_number):
        """Process a single lap with telemetry data"""
        lap_laps = laps[laps['LapNumber'] == lap_number]
        
        drivers = []
        for idx, lap in lap_laps.iterrows():
            if pd.isna(lap['LapTime']):
                continue
            
            # Get telemetry for this lap
            try:
                telemetry = lap.get_telemetry()
                
                # Get average telemetry values
                avg_speed = telemetry['Speed'].mean() if 'Speed' in telemetry else None
                max_speed = telemetry['Speed'].max() if 'Speed' in telemetry else None
                
                # Get position at end of lap (distance)
                lap_distance = telemetry['Distance'].iloc[-1] if 'Distance' in telemetry and len(telemetry) > 0 else 0
            except:
                avg_speed = None
                max_speed = None
                lap_distance = 0
            
            driver_data = {
                'driver': lap['Driver'],
                'team': lap['Team'],
                'position': int(lap['Position']) if pd.notna(lap['Position']) else None,
                'lap_time': str(lap['LapTime']) if pd.notna(lap['LapTime']) else None,
                'compound': lap['Compound'] if pd.notna(lap['Compound']) else 'UNKNOWN',
                'tire_life': int(lap['TyreLife']) if pd.notna(lap['TyreLife']) else 0,
                'pit_out': bool(lap['PitOutTime']) if 'PitOutTime' in lap and pd.notna(lap['PitOutTime']) else False,
                'pit_in': bool(lap['PitInTime']) if 'PitInTime' in lap and pd.notna(lap['PitInTime']) else False,
                'distance': float(lap_distance) if lap_distance else 0,
                'avg_speed': float(avg_speed) if pd.notna(avg_speed) else None,
                'max_speed': float(max_speed) if pd.notna(max_speed) else None
            }
            drivers.append(driver_data)
        
        # Sort by position
        drivers.sort(key=lambda x: x['position'] if x['position'] else 999)
        
        # Calculate gaps
        if drivers and drivers[0]['position'] == 1:
            for i, driver in enumerate(drivers):
                if i == 0:
                    driver['gap'] = 'LEADER'
                else:
                    driver['gap'] = f"+{i * 0.5:.1f}s"
        
        return {
            'lap_number': lap_number,
            'drivers': drivers
        }
    
    def get_race_summary(self, year, race_round):
        """Get quick race summary"""
        try:
            session = self.load_race_session(year, race_round)
            if not session:
                return None
            
            results = session.results
            
            return {
                'name': session.event['EventName'],
                'date': session.event['EventDate'].isoformat(),
                'winner': results.iloc[0]['Abbreviation'] if len(results) > 0 else None,
                'podium': [
                    results.iloc[i]['Abbreviation'] 
                    for i in range(min(3, len(results)))
                ]
            }
        except Exception as e:
            print(f"Error getting summary: {e}")
            return None

fastf1_service = FastF1Service()
