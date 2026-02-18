from flask import Blueprint, jsonify
from app.models import db, User, Prediction
from sqlalchemy import func

bp = Blueprint('leaderboard', __name__, url_prefix='/api')

@bp.route('/leaderboard', methods=['GET'])
def get_leaderboard():
    """Get top users by total score"""
    users = User.query.order_by(User.total_score.desc()).limit(50).all()
    
    leaderboard = []
    for rank, user in enumerate(users, start=1):
        predictions_count = Prediction.query.filter_by(user_id=user.id).count()
        leaderboard.append({
            'rank': rank,
            'username': user.username,
            'totalPoints': user.total_score,
            'accuracy': round(user.accuracy_rate, 1),
            'predictionsCount': predictions_count
        })
    
    return jsonify(leaderboard)
