from app import create_app
from app.models import db, User, Race, Driver
from datetime import date, timedelta

def init_database():
    app = create_app()
    
    with app.app_context():
        # Drop all tables and recreate
        print("Dropping all tables...")
        db.drop_all()
        
        print("Creating tables...")
        db.create_all()
        
        print("Seeding data...")
        
        # Create sample users
        users = [
            User(username='StrategyKing', email='king@example.com', total_score=4520, accuracy_rate=87.3),
            User(username='F1Prophet', email='prophet@example.com', total_score=4385, accuracy_rate=84.1),
            User(username='PitStopMaster', email='master@example.com', total_score=4210, accuracy_rate=82.5),
            User(username='TireWhisperer', email='whisper@example.com', total_score=3995, accuracy_rate=79.8),
            User(username='RaceStrategist', email='strategist@example.com', total_score=3870, accuracy_rate=78.2),
        ]
        db.session.add_all(users)
        
        # Create sample races
        today = date.today()
        races = [
            Race(
                name='Bahrain Grand Prix',
                circuit='Bahrain International Circuit',
                country='🇧🇭',
                date=today + timedelta(days=30),
                total_laps=57,
                status='upcoming'
            ),
            Race(
                name='Saudi Arabian Grand Prix',
                circuit='Jeddah Corniche Circuit',
                country='🇸🇦',
                date=today + timedelta(days=37),
                total_laps=50,
                status='upcoming'
            ),
            Race(
                name='Australian Grand Prix',
                circuit='Albert Park Circuit',
                country='🇦🇺',
                date=today + timedelta(days=50),
                total_laps=58,
                current_lap=23,
                status='live'
            ),
        ]
        db.session.add_all(races)
        db.session.commit()
        
        # Create drivers for Australian GP (race_id=3)
        drivers = [
            Driver(race_id=3, driver_name='Max Verstappen', team='Red Bull Racing', 
                   position=1, gap='LEADER', tire_compound='MEDIUM', tire_age=12, last_pit_lap=11),
            Driver(race_id=3, driver_name='Charles Leclerc', team='Ferrari',
                   position=2, gap='+3.2s', tire_compound='HARD', tire_age=15, last_pit_lap=8),
            Driver(race_id=3, driver_name='Lewis Hamilton', team='Mercedes',
                   position=3, gap='+5.8s', tire_compound='MEDIUM', tire_age=10, last_pit_lap=13),
        ]
        db.session.add_all(drivers)
        db.session.commit()
        
        print("✅ Database initialized successfully!")
        print(f"   - {len(users)} users created")
        print(f"   - {len(races)} races created")
        print(f"   - {len(drivers)} drivers created")

if __name__ == '__main__':
    init_database()
