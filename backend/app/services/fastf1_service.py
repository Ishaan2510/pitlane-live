import fastf1
import pandas as pd
from pathlib import Path
import json
from datetime import datetime

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
                # Only include race events (not testing)
                if event['EventFormat'] != 'testing':
                    races.append({
                        'round': event['RoundNumber'],
                        'name': event['EventName'],
                        'location': event['Location'],
                        'country': event['Country'],
                        'date': event['EventDate'].isoformat() if pd.notna(event['EventDate']) else None,
                        'circuit': event['EventName']
                    })
            
            return races
        except Exception as e:
            print(f"Error fetching schedule: {e}")
            return []
    
    def load_race_session(self, year, race_round, session_type='Race'):
        """
        Load a race session from FastF1
        session_type: 'Race', 'Sprint', 'Qualifying'
        """
        try:
            print(f"Loading {year} Round {race_round} {session_type}...")
            session = fastf1.get_session(year, race_round, session_type)
            session.load()
            return session
        except Exception as e:
            print(f"Error loading session: {e}")
            return None
    
    def process_race_telemetry(self, year, race_round):
        """
        Process full race telemetry into lap-by-lap data
        Returns structured data for replay
        """
        cache_file = self.processed_cache_dir / f"{year}_R{race_round}_processed.json"
        
        # Check if already processed
        if cache_file.exists():
            print(f"Loading from cache: {cache_file}")
            with open(cache_file, 'r') as f:
                return json.load(f)
        
        # Load session
        session = self.load_race_session(year, race_round)
        if not session:
            return None
        
        print("Processing telemetry...")
        
        # Get race info
        race_data = {
            'year': year,
            'round': race_round,
            'name': session.event['EventName'],
            'circuit': session.event['Location'],
            'date': session.event['EventDate'].isoformat(),
            'total_laps': int(session.total_laps) if hasattr(session, 'total_laps') else 0,
            'laps': []
        }
        
        # Process each lap
        laps = session.laps
        
        for lap_number in range(1, race_data['total_laps'] + 1):
            lap_data = self._process_lap(laps, lap_number)
            race_data['laps'].append(lap_data)
        
        # Save to cache
        with open(cache_file, 'w') as f:
            json.dump(race_data, f, indent=2)
        
        print(f"✅ Processed {len(race_data['laps'])} laps")
        return race_data
    
    def _process_lap(self, laps, lap_number):
        """Process a single lap and return driver positions/data"""
        lap_laps = laps[laps['LapNumber'] == lap_number]
        
        drivers = []
        for idx, lap in lap_laps.iterrows():
            # Skip if driver didn't complete the lap
            if pd.isna(lap['LapTime']):
                continue
            
            driver_data = {
                'driver': lap['Driver'],
                'team': lap['Team'],
                'position': int(lap['Position']) if pd.notna(lap['Position']) else None,
                'lap_time': str(lap['LapTime']) if pd.notna(lap['LapTime']) else None,
                'compound': lap['Compound'] if pd.notna(lap['Compound']) else 'UNKNOWN',
                'tire_life': int(lap['TyreLife']) if pd.notna(lap['TyreLife']) else 0,
                'pit_out': bool(lap['PitOutTime']) if 'PitOutTime' in lap and pd.notna(lap['PitOutTime']) else False,
                'pit_in': bool(lap['PitInTime']) if 'PitInTime' in lap and pd.notna(lap['PitInTime']) else False
            }
            drivers.append(driver_data)
        
        # Sort by position
        drivers.sort(key=lambda x: x['position'] if x['position'] else 999)
        
        # Calculate gaps to leader
        if drivers and drivers[0]['position'] == 1:
            leader_time = drivers[0]['lap_time']
            for i, driver in enumerate(drivers):
                if i == 0:
                    driver['gap'] = 'LEADER'
                else:
                    # In real implementation, calculate cumulative gaps
                    # For now, just show position-based gap
                    driver['gap'] = f"+{i * 0.5:.1f}s"
        
        return {
            'lap_number': lap_number,
            'drivers': drivers
        }
    
    def get_race_summary(self, year, race_round):
        """Get quick race summary without full telemetry"""
        try:
            session = self.load_race_session(year, race_round)
            if not session:
                return None
            
            results = session.results
            
            summary = {
                'name': session.event['EventName'],
                'date': session.event['EventDate'].isoformat(),
                'winner': results.iloc[0]['Abbreviation'] if len(results) > 0 else None,
                'podium': [
                    results.iloc[i]['Abbreviation'] 
                    for i in range(min(3, len(results)))
                ]
            }
            
            return summary
        except Exception as e:
            print(f"Error getting summary: {e}")
            return None

# Singleton instance
fastf1_service = FastF1Service()
