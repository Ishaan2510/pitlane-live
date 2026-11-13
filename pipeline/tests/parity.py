"""
Compare the race files two sources built for the same event.

    python pipeline/tests/parity.py <event dir A> <event dir B>

compare() returns (rows, ok): one row per check with both values, and whether all passed.
Used by the network parity test and handy on its own.
"""
import json
import sys
from pathlib import Path

LAP_TOLERANCE_S = 0.05
LAP_MATCH_SHARE = 0.95
PIT_LOSS_TOLERANCE_S = 1.5


def _load(event_dir, name):
    return json.loads((Path(event_dir) / 'race' / name).read_text(encoding='utf-8'))


def _laps(event_dir):
    table = _load(event_dir, 'laps.json')
    return {(r['driver'], r['lap']): r for r in (dict(zip(table['columns'], row)) for row in table['rows'])}


def _stint_starts(laps):
    """{driver: [(first lap of the stint, compound), ...]}"""
    out = {}
    for (driver, lap), row in sorted(laps.items()):
        stints = out.setdefault(driver, [])
        if row['stint'] is not None and (not stints or stints[-1][2] != row['stint']):
            stints.append((lap, row['compound'], row['stint']))
    return {d: [(lap, compound) for lap, compound, _ in s] for d, s in out.items()}


def compare(dir_a, dir_b):
    a, b = _laps(dir_a), _laps(dir_b)
    rows = []

    def check(name, value_a, value_b, ok, detail=''):
        rows.append((name, str(value_a), str(value_b), 'ok' if ok else 'FAIL', detail))

    both = [k for k in a if k in b and a[k]['lap_time_s'] is not None and b[k]['lap_time_s'] is not None]
    close = [k for k in both if abs(a[k]['lap_time_s'] - b[k]['lap_time_s']) <= LAP_TOLERANCE_S]
    share = len(close) / len(both) if both else 0
    worst = max(both, key=lambda k: abs(a[k]['lap_time_s'] - b[k]['lap_time_s']), default=None)
    check('lap rows', len(a), len(b), True, f'{len(both)} timed in both')
    check(f'lap times within {LAP_TOLERANCE_S}s', f'{share:.1%}', f'need {LAP_MATCH_SHARE:.0%}',
          share >= LAP_MATCH_SHARE,
          f'worst {worst}: {a[worst]["lap_time_s"]} vs {b[worst]["lap_time_s"]}' if worst else '')

    compound_diff = [k for k in a if k in b and a[k]['compound'] != b[k]['compound']]
    check('compound per lap', 'same' if not compound_diff else f'{len(compound_diff)} differ', '',
          not compound_diff, str(compound_diff[:4]) if compound_diff else '')

    stints_a, stints_b = _stint_starts(a), _stint_starts(b)
    stint_diff = [d for d in stints_a if stints_a[d] != stints_b.get(d)]
    check('stint boundaries', sum(map(len, stints_a.values())), sum(map(len, stints_b.values())),
          not stint_diff, '; '.join(f'{d}: {stints_a[d]} vs {stints_b.get(d)}' for d in stint_diff[:2]))

    # A pit stop = an in-lap followed by another lap. A car that retires in the pit lane has
    # an in-lap in FastF1 only (OpenF1 has no pit record for it), so that is reported, not failed.
    def stops(laps):
        return {k for k, r in laps.items() if r['pit_in'] and (k[0], k[1] + 1) in laps}

    def retired_in_pits(laps):
        return sorted(k for k, r in laps.items() if r['pit_in'] and (k[0], k[1] + 1) not in laps)

    pits_a, pits_b = stops(a), stops(b)
    check('pit-in laps', len(pits_a), len(pits_b), pits_a == pits_b,
          f'only A {sorted(pits_a - pits_b)[:4]} only B {sorted(pits_b - pits_a)[:4]}' if pits_a != pits_b else '')
    check('retired in the pits (info)', retired_in_pits(a), retired_in_pits(b), True)

    def order(event_dir):
        return [r['driver'] for r in sorted(_load(event_dir, 'results.json'), key=lambda r: r['position'])]

    order_a, order_b = order(dir_a), order(dir_b)
    check('classified order', ' '.join(order_a[:5]) + ' ...', ' '.join(order_b[:5]) + ' ...', order_a == order_b)

    loss_a, loss_b = _load(dir_a, 'pit_loss.json'), _load(dir_b, 'pit_loss.json')
    ma, mb = loss_a['median_loss_s'], loss_b['median_loss_s']
    check('pit loss median (s)', ma, mb,
          (ma is None and mb is None) or (None not in (ma, mb) and abs(ma - mb) <= PIT_LOSS_TOLERANCE_S),
          f'green stops {loss_a["green_stops"]} vs {loss_b["green_stops"]}')
    return rows, all(r[3] == 'ok' for r in rows)


def table(rows, label_a='A', label_b='B'):
    head = ('check', label_a, label_b, '', 'detail')
    widths = [max(len(str(r[i])) for r in [head, *rows]) for i in range(4)]
    return '\n'.join('  '.join(str(c).ljust(w) for c, w in zip(r, widths)) + '  ' + r[4]
                     for r in [head, *rows])


if __name__ == '__main__':
    result, passed = compare(sys.argv[1], sys.argv[2])
    print(table(result))
    sys.exit(0 if passed else 1)
