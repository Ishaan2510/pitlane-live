"""init_db.py must seed a fresh sqlite database, and refuse anything that is not sqlite."""
import sqlite3

import pytest

from app.config import Config


def test_fresh_sqlite_database_seeds(tmp_path, monkeypatch):
    path = tmp_path / 'seed.db'
    monkeypatch.setattr(Config, 'SQLALCHEMY_DATABASE_URI', f'sqlite:///{path.as_posix()}')
    import init_db
    init_db.init_database()

    con = sqlite3.connect(path)
    try:
        users = con.execute('select username, password_hash from users').fetchall()
        assert len(users) == 5 and all(h for _, h in users)        # password_hash is NOT NULL
        assert con.execute('select count(*) from races').fetchone()[0] == 3
    finally:
        con.close()


def test_refuses_a_database_that_is_not_sqlite(monkeypatch):
    monkeypatch.setattr(Config, 'SQLALCHEMY_DATABASE_URI', 'postgresql://user:pw@localhost:1/prod')
    import init_db
    with pytest.raises(SystemExit, match='only runs on sqlite'):
        init_db.init_database()
