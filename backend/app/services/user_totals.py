"""
The single place User.total_score and User.accuracy_rate are computed.

total_score   = pit-call points + scored race-prediction points
accuracy_rate = % correct among scored pit-call predictions (race predictions use
                partial credit, so they have no correct/wrong to count)
"""
from sqlalchemy import case, func

from app.models import db, Prediction, RacePrediction, User


def recompute_user_totals() -> int:
    pit_points = dict(
        db.session.query(Prediction.user_id, func.sum(Prediction.points_earned))
        .group_by(Prediction.user_id)
    )
    race_points = dict(
        db.session.query(RacePrediction.user_id, func.sum(RacePrediction.total_points))
        .filter(RacePrediction.status == 'scored')
        .group_by(RacePrediction.user_id)
    )
    accuracy = {
        user_id: round(correct / scored * 100, 1)
        for user_id, scored, correct in (
            db.session.query(
                Prediction.user_id,
                func.count(Prediction.id),
                func.sum(case((Prediction.status == 'correct', 1), else_=0)),
            )
            .filter(Prediction.status.in_(('correct', 'wrong')))
            .group_by(Prediction.user_id)
        )
    }

    rows = [
        {
            'id':            user_id,
            'total_score':   int(pit_points.get(user_id) or 0) + int(race_points.get(user_id) or 0),
            'accuracy_rate': accuracy.get(user_id, 0.0),
        }
        for (user_id,) in db.session.query(User.id)
    ]
    db.session.bulk_update_mappings(User, rows)
    db.session.commit()
    return len(rows)
