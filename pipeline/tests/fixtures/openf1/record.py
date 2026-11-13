"""
Re-record the trimmed OpenF1 fixtures in this folder (2025 Monaco GP race, session 9979).

    python pipeline/tests/fixtures/openf1/record.py

Keeps three drivers that cover the awkward cases:
  NOR (4)   normal stop: in-lap 19, out-lap 20
  TSU (22)  pits at the end of lap 1, has a deleted lap (lap 8)
  GAS (10)  starts on used tyres, pits on lap 1, retires on lap 8
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from sources.openf1_source import OpenF1Client   # noqa: E402

SESSION = 9979
DRIVERS = {4: 21, 22: 10, 10: 10}        # driver_number -> last lap kept
UNTIL = '2025-05-25T13:32:00'            # just after NOR's lap 21


def main():
    client = OpenF1Client()
    get = lambda name: client.get(name, session_key=SESSION)   # noqa: E731
    mine = lambda rows: [r for r in rows if r.get('driver_number') in DRIVERS]   # noqa: E731

    laps = [{k: v for k, v in lap.items() if not k.startswith('segments_')}
            for lap in mine(get('laps')) if lap['lap_number'] <= DRIVERS[lap['driver_number']]]
    race_control = [m for m in get('race_control')
                    if m['flag'] != 'BLUE' and m['date'][:19] < UNTIL
                    and (m['driver_number'] is None or m['driver_number'] in DRIVERS)
                    and (m['category'] != 'Other' or 'DELETED' in m['message'])
                    and (' (' not in m['message'] or any(f'CAR {d} ' in m['message'] for d in DRIVERS))]
    out = {
        'drivers': mine(get('drivers')),
        'laps': laps,
        'stints': mine(get('stints')),
        'pit': mine(get('pit')),
        'position': [p for p in mine(get('position')) if p['date'][:19] < UNTIL],
        'race_control': race_control,
        'session_result': mine(get('session_result')),
        'weather': get('weather')[:3],
    }
    for name, rows in out.items():
        for row in rows:
            row.pop('meeting_key', None)
            row.pop('headshot_url', None)
        (HERE / f'{name}.json').write_text(json.dumps(rows, indent=1) + '\n', encoding='utf-8')
        print(f'{name}: {len(rows)} rows')


if __name__ == '__main__':
    main()
