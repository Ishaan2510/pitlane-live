from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    total_score = db.Column(db.Integer, default=0)
    accuracy_rate = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    predictions = db.relationship('Prediction', back_populates='user', lazy=True)
    scores = db.relationship('UserScore', back_populates='user', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'total_score': self.total_score,
            'accuracy_rate': round(self.accuracy_rate, 1)
        }


class Race(db.Model):
    __tablename__ = 'races'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    circuit = db.Column(db.String(100), nullable=False)
    country = db.Column(db.String(10), nullable=False)
    date = db.Column(db.Date, nullable=False)
    total_laps = db.Column(db.Integer, nullable=False)
    current_lap = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='upcoming')  # upcoming, live, completed
    
    drivers = db.relationship('Driver', back_populates='race', lazy=True, cascade='all, delete-orphan')
    predictions = db.relationship('Prediction', back_populates='race', lazy=True)
    
    def to_dict(self, include_drivers=False):
        data = {
            'id': self.id,
            'name': self.name,
            'circuit': self.circuit,
            'country': self.country,
            'date': self.date.isoformat(),
            'laps': self.total_laps,
            'currentLap': self.current_lap,
            'status': self.status
        }
        if include_drivers:
            data['leaders'] = [d.to_dict() for d in self.drivers]
        return data


class Driver(db.Model):
    __tablename__ = 'drivers'
    
    id = db.Column(db.Integer, primary_key=True)
    race_id = db.Column(db.Integer, db.ForeignKey('races.id'), nullable=False)
    driver_name = db.Column(db.String(100), nullable=False)
    team = db.Column(db.String(100), nullable=False)
    position = db.Column(db.Integer, nullable=False)
    gap = db.Column(db.String(20), default='LEADER')
    tire_compound = db.Column(db.String(20), nullable=False)
    tire_age = db.Column(db.Integer, default=0)
    last_pit_lap = db.Column(db.Integer, default=0)
    
    race = db.relationship('Race', back_populates='drivers')
    
    def to_dict(self):
        return {
            'position': self.position,
            'driver': self.driver_name,
            'team': self.team,
            'gap': self.gap,
            'tireCompound': self.tire_compound,
            'tireAge': self.tire_age,
            'lastPitLap': self.last_pit_lap
        }


class Prediction(db.Model):
    __tablename__ = 'predictions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    race_id = db.Column(db.Integer, db.ForeignKey('races.id'), nullable=False)
    driver_name = db.Column(db.String(100), nullable=False)
    action = db.Column(db.String(50), nullable=False)  # pit_soft, pit_medium, pit_hard, stay_out
    predicted_lap = db.Column(db.Integer, nullable=False)
    confidence = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, correct, incorrect, close
    points_earned = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', back_populates='predictions')
    race = db.relationship('Race', back_populates='predictions')
    
    def to_dict(self):
        return {
            'id': self.id,
            'driver': self.driver_name,
            'action': self.action,
            'lap': self.predicted_lap,
            'confidence': self.confidence,
            'status': self.status,
            'points': self.points_earned,
            'timestamp': self.created_at.isoformat()
        }


class UserScore(db.Model):
    __tablename__ = 'user_scores'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    race_id = db.Column(db.Integer, db.ForeignKey('races.id'), nullable=False)
    points_earned = db.Column(db.Integer, default=0)
    accuracy = db.Column(db.Float, default=0.0)
    rank = db.Column(db.Integer, nullable=True)
    
    user = db.relationship('User', back_populates='scores')
    
    def to_dict(self):
        return {
            'race_id': self.race_id,
            'points': self.points_earned,
            'accuracy': round(self.accuracy, 1),
            'rank': self.rank
        }
