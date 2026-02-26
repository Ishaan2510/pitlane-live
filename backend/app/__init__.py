from flask import Flask
from flask_cors import CORS
from app.config import Config
from app.models import db

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Enable CORS for frontend
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # Initialize database
    db.init_app(app)
    
    # Register blueprints
    from app.routes import races, predictions, leaderboard, users, replay, schedule
    app.register_blueprint(races.bp)
    app.register_blueprint(predictions.bp)
    app.register_blueprint(leaderboard.bp)
    app.register_blueprint(users.bp)
    app.register_blueprint(replay.bp)
    app.register_blueprint(schedule.bp)
    
    return app
