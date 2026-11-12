from flask import Flask

from app.models import db, Prediction, RacePrediction, User
from app.services.user_totals import recompute_user_totals


def test_totals_combine_pit_calls_and_race_predictions():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
    db.init_app(app)
    with app.app_context():
        db.create_all()
        a = User(username='aaa', email='a@x', password_hash='x')
        b = User(username='bbb', email='b@x', password_hash='x')
        db.session.add_all([a, b])
        db.session.flush()

        def pit(status, pts):
            return Prediction(user_id=a.id, driver_name='VER', action='stay_out',
                              predicted_lap=0, confidence=50, status=status, points_earned=pts)

        db.session.add_all([pit('correct', 75), pit('wrong', 0), pit('wrong', 0), pit('pending', 0)])
        db.session.add_all([
            RacePrediction(user_id=a.id, year=2025, round_num=1, predicted_order=['VER'],
                           status='scored', total_points=30),
            RacePrediction(user_id=a.id, year=2025, round_num=2, predicted_order=['VER'],
                           status='pending', total_points=99),
        ])
        db.session.commit()

        assert recompute_user_totals() == 2
        assert (a.total_score, a.accuracy_rate) == (105, 33.3)
        assert (b.total_score, b.accuracy_rate) == (0, 0.0)
