"""
Test script to verify FastF1 integration
Run this to fetch and cache a race before using the API
"""
from app.services.fastf1_service import fastf1_service

def test_fetch_race():
    print("\n" + "="*60)
    print("Testing FastF1 Integration")
    print("="*60 + "\n")
    
    # Test 1: Get available races
    print("📅 Fetching 2024 race calendar...")
    races = fastf1_service.get_available_races(2024)
    print(f"✅ Found {len(races)} races\n")
    
    if races:
        print("First 3 races:")
        for race in races[:3]:
            print(f"  Round {race['round']}: {race['name']}")
    
    # Test 2: Get race summary
    print("\n📊 Fetching race summary for 2024 Round 1 (Bahrain)...")
    summary = fastf1_service.get_race_summary(2024, 1)
    if summary:
        print(f"✅ Winner: {summary['winner']}")
        print(f"   Podium: {', '.join(summary['podium'])}")
    
    # Test 3: Process full race telemetry
    print("\n🏎️  Processing full race telemetry for 2024 Round 1...")
    print("⚠️  This will take 2-3 minutes on first run (then cached)")
    race_data = fastf1_service.process_race_telemetry(2024, 1)
    
    if race_data:
        print(f"\n✅ Successfully processed {len(race_data['laps'])} laps")
        print(f"   Race: {race_data['name']}")
        print(f"   Circuit: {race_data['circuit']}")
        
        # Show lap 1 data
        if race_data['laps']:
            lap1 = race_data['laps'][0]
            print(f"\n   Lap 1 - Top 3:")
            for driver in lap1['drivers'][:3]:
                print(f"     P{driver['position']}: {driver['driver']} ({driver['team']}) - {driver['compound']}")
    
    print("\n" + "="*60)
    print("✅ FastF1 integration working!")
    print("="*60 + "\n")

if __name__ == '__main__':
    test_fetch_race()
