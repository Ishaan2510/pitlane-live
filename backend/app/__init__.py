from flask import Flask
from flask_cors import CORS
from app.config import Config
from app.models import db

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Enable CORS for frontend (allowlist via CORS_ORIGINS)
    cors_origins = app.config.get('CORS_ORIGINS') or []
    CORS(
        app,
        resources={r"/api/*": {
            "origins": cors_origins or [],
            "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-Admin-Key"],
        }},
        supports_credentials=False
    )
    
    # Initialize database
    db.init_app(app)
    
    # Register blueprints
    from app.routes import races, predictions, leaderboard, users, replay, schedule, scoring, news, drivers, race_predictions
    app.register_blueprint(races.bp)
    app.register_blueprint(predictions.bp)
    app.register_blueprint(leaderboard.bp)
    app.register_blueprint(users.bp)
    app.register_blueprint(replay.bp)
    app.register_blueprint(schedule.bp)
    app.register_blueprint(scoring.bp)
    app.register_blueprint(news.bp)
    app.register_blueprint(drivers.bp)
    app.register_blueprint(race_predictions.bp)
    
    # Health check for uptime monitoring
    @app.route('/health')
    def health():
        from flask import jsonify
        response = jsonify({'status': 'ok'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    
    @app.route('/api/health')
    def api_health():
        return {'status': 'ok'}
    
    return app
