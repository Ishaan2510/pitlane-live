"""
Adds predictions.year, predictions.round_num and predictions.mode.
db.create_all() never alters existing tables, so run this once per database. Safe to re-run.

From Git Bash:
    cd backend
    DATABASE_URL='postgresql://...' python migrations/001_prediction_year_round.py
(or put DATABASE_URL in backend/.env and just run python migrations/001_prediction_year_round.py)
"""
import os
import sys

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text

COLUMNS = [
    ('year',      'INTEGER'),
    ('round_num', 'INTEGER'),
    ('mode',      "VARCHAR(10) DEFAULT 'sim'"),
]


def main():
    load_dotenv()
    url = os.getenv('DATABASE_URL')
    if not url:
        sys.exit('DATABASE_URL is not set')

    engine = create_engine(url)
    existing = {c['name'] for c in inspect(engine).get_columns('predictions')}
    with engine.begin() as conn:
        for name, ddl in COLUMNS:
            if engine.dialect.name == 'postgresql':
                conn.execute(text(f'ALTER TABLE predictions ADD COLUMN IF NOT EXISTS {name} {ddl}'))
            elif name not in existing:   # SQLite has no ADD COLUMN IF NOT EXISTS
                conn.execute(text(f'ALTER TABLE predictions ADD COLUMN {name} {ddl}'))
            print(f'predictions.{name}: ' + ('already present' if name in existing else 'added'))


if __name__ == '__main__':
    main()
