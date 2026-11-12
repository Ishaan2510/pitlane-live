from flask import Blueprint, jsonify
from app.models import db, User, Prediction
from sqlalchemy import func

bp = Blueprint('leaderboard', __name__, url_prefix='/api')

@bp.route('/leaderboard', methods=['GET'])
def get_leaderboard():
    """Get top users by total score"""
    users = User.query.order_by(User.total_score.desc()).limit(100).all()

    # Only count real race predictions, not simulation ones
    counts = dict(
        db.session.query(Prediction.user_id, func.count(Prediction.id))
        .filter(Prediction.mode == 'live')
        .group_by(Prediction.user_id)
    )

    leaderboard = []
    for rank, user in enumerate(users, start=1):
        leaderboard.append({
            'rank':             rank,
            'username':         user.username,
            'totalPoints':      user.total_score,
            'accuracy':         round(user.accuracy_rate, 1),
            'predictionsCount': counts.get(user.id, 0)
        })

    return jsonify(leaderboard)