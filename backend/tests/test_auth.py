from app.config import Config


def _client():
    Config.SQLALCHEMY_DATABASE_URI = 'sqlite://'
    from app import create_app
    from app.models import db
    app = create_app()
    with app.app_context():
        db.create_all()
    return app.test_client()


def test_register_login_and_rate_limit():
    c = _client()
    r = c.post('/api/auth/register', json={'username': 'abc', 'email': 'a@b.co', 'password': ' secret '})
    assert r.status_code == 201 and r.json['user']['email'] == 'a@b.co'

    # Password is no longer stripped
    assert c.post('/api/auth/login', json={'identifier': 'abc', 'password': 'secret'}).status_code == 401
    ok = c.post('/api/auth/login', json={'identifier': 'abc', 'password': ' secret '})
    assert ok.status_code == 200 and 'email' in ok.json['user']

    # 10/min per IP across login; the 3rd login above was the 2nd hit, so 8 more pass, then 429
    codes = [c.post('/api/auth/login', json={'identifier': 'abc', 'password': 'x'},
                    headers={'X-Forwarded-For': '1.2.3.4, 10.0.0.1'}).status_code for _ in range(11)]
    assert codes[:10] == [401] * 10 and codes[10] == 429
    assert c.get('/api/users/1').status_code == 404
