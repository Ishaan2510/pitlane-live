"""
Validation gate for built race and sprint folders.

    python pipeline/validate.py                       # every session under frontend/public/data
    python pipeline/validate.py path/to/2026/19/race  # these folders only

build.py runs validate_session() on every race or sprint before it is published; a session
with a problem is not moved into place. Exit code 1 when any session fails, one line each.

A session fails when:
- a track status period is missing a time, starts before lights out, or ends before it starts
- a compound is not one of SOFT, MEDIUM, HARD, INTERMEDIATE, WET, UNKNOWN
- the green pit loss median is outside 10 to 45 s, or a Safety Car / VSC median is not
  between 0 and the green one
- two drivers have the same position at the end of a lap, or a position is outside 1..cars
- the highest lap in laps.json is not the winner's lap count in results.json
"""
import json
import sys
from pathlib import Path

COMPOUNDS = {'SOFT', 'MEDIUM', 'HARD', 'INTERMEDIATE', 'WET', 'UNKNOWN'}
PIT_LOSS_RANGE_S = (10, 45)


def _read(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def validate_session(session_dir):
    """Problems found in one race or sprint folder, as short strings. [] = valid."""
    d = Path(session_dir)
    problems = []
    try:
        table = _read(d / 'laps.json')
        status = _read(d / 'track_status.json')
        pit_loss = _read(d / 'pit_loss.json')
        results = _read(d / 'results.json')
    except (OSError, ValueError) as e:
        return [f'unreadable file ({e})']
    col = {name: i for i, name in enumerate(table['columns'])}
    rows = table['rows']

    for i, p in enumerate(status['periods']):
        start, end = p.get('start_time_s'), p.get('end_time_s')
        if start is None or end is None or start < 0 or end < start:
            problems.append(f'track status period {i} runs {start} to {end}')
            break

    bad = sorted({str(r[col['compound']]) for r in rows} - COMPOUNDS)
    if bad:
        problems.append(f'compound outside the canonical set: {", ".join(bad)}')

    low, high = PIT_LOSS_RANGE_S
    green = pit_loss.get('median_loss_s')
    if green is not None and not low <= green <= high:
        problems.append(f'pit loss {green} s is outside {low} to {high} s')
    for key in ('median_loss_sc_s', 'median_loss_vsc_s'):
        value = pit_loss.get(key)
        if value is not None and (value <= 0 or (green is not None and value > green)):
            problems.append(f'{key} {value} s is not between 0 and the green loss')

    cars = max(len(results), len({r[col['driver']] for r in rows}))   # entries: a car that never started still has a place
    by_lap = {}
    for r in rows:
        if r[col['position']] is not None:
            by_lap.setdefault(r[col['lap']], []).append(r[col['position']])
    for lap, places in sorted(by_lap.items()):
        if len(set(places)) < len(places) or min(places) < 1 or max(places) > cars:
            problems.append(f'positions on lap {lap} are not a permutation')
            break

    laps_run = max((r[col['lap']] for r in rows), default=0)
    classified = max((r.get('laps') or 0 for r in results), default=0)
    if laps_run != classified:
        problems.append(f'laps.json has {laps_run} laps, results.json says {classified}')
    return problems


def main(argv=None):
    args = (argv if argv is not None else sys.argv[1:])
    root = Path(__file__).resolve().parent.parent / 'frontend' / 'public' / 'data'
    folders = [Path(a) for a in args] or sorted(p.parent for p in root.glob('*/*/*/laps.json'))
    failed = 0
    for folder in folders:
        problems = validate_session(folder)
        if problems:
            failed += 1
            print(f'INVALID {folder.as_posix()}: {"; ".join(problems)}')
    print(f'validate: {len(folders) - failed} of {len(folders)} session(s) valid')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
