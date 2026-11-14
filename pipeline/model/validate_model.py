"""
How good is the tyre model? Two checks per race, and the report for all of them.

- Leave one driver out: fit the model without a driver, take their base pace from their
  first stint only, and predict the clean laps of their later stints from the tyres they
  were really on. The error is what the model does not know about a car it has not seen.
- Whole race: rebuild every classified driver's green racing laps from the model, stint by
  stint (between pit stops), and compare with the time they really took.

tyre_model.py calls both and stores the numbers under `validation` in tyre_model.json.

    python pipeline/model/validate_model.py     # rewrite pipeline/model/VALIDATION.md from the files on disk
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # so `model` imports when run as a script

from model import tyre_model as tm  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'frontend' / 'public' / 'data'
REPORT = Path(__file__).resolve().parent / 'VALIDATION.md'


# ── leave one driver out ──────────────────────────────────────────────────────

def leave_one_driver_out(laps, quadratic=(), force_prior=False):
    """
    For every driver: fit without them, take their base pace from their first stint only,
    and predict the clean laps of their later stints from the tyres they were really on.
    Returns {'errors': {compound: [abs error per lap]}, 'stints': [abs error of a stint's
    total time], 'n_drivers': drivers that could be tested}.
    """
    by_driver = {}
    for l in laps:
        by_driver.setdefault(l['driver'], []).append(l)
    errors, stint_errors, tested = {}, [], 0
    for driver, own in by_driver.items():
        stints = sorted({l['stint'] for l in own})
        if len(stints) < 2:
            continue                                   # nothing to predict out of sample
        train = [l for l in laps if l['driver'] != driver]
        linked = tm.comparable_compounds(train)           # without this driver some compounds may not be comparable
        train = [l for l in train if l['compound'] in linked]
        if len({l['driver'] for l in train}) < 2:
            continue
        params, _ = tm.fit_with_fallback(train, quadratic, force_prior)
        known = set(params['compounds'])
        first = [l for l in own if l['stint'] == stints[0] and l['compound'] in known]
        if not first:
            continue
        base = float(np.mean([l['time'] - tm.predict(params, 0.0, l) for l in first]))
        any_tested = False
        for stint in stints[1:]:
            later = [l for l in own if l['stint'] == stint and l['compound'] in known]
            if not later:
                continue
            diffs = [tm.predict(params, base, l) - l['time'] for l in later]
            errors.setdefault(later[0]['compound'], []).extend(abs(d) for d in diffs)
            stint_errors.append(abs(sum(diffs)))
            any_tested = True
        tested += any_tested
    return {'errors': errors, 'stints': stint_errors, 'n_drivers': tested}



def race_time_check(params, racing, classified=None):
    """
    Whole-race check. For every (classified) driver, rebuild the time of their green racing
    laps from the model, stint by stint, and compare with what they really did. Everything
    else in a race time (in-laps, out-laps, Safety Car laps) is taken as it happened, so the
    difference in race time is the sum over these laps. The fit only sees clean laps; this
    includes the laps it drops (traffic, mistakes, restarts), so it shows how much quicker
    a model race is than a real one.
    """
    by_driver = {}
    for l in racing:
        if l['driver'] in params['base'] and (classified is None or l['driver'] in classified):
            by_driver.setdefault(l['driver'], {}).setdefault(l['stint'], []).append(l)
    race, stints = [], []
    for driver, own in by_driver.items():
        total = 0.0
        for laps in own.values():
            diff = sum(tm.predict(params, params['base'][driver], l) - l['time'] for l in laps)
            stints.append(diff)
            total += diff
        race.append(total)
    if not race:
        return None
    return {'race_time_mae_s': round(float(np.mean(np.abs(race))), 2),
            'race_time_bias_s': round(float(np.mean(race)), 2),
            'between_stops_mae_s': round(float(np.mean(np.abs(stints))), 2),
            'n_drivers': len(race)}


# ── VALIDATION.md ─────────────────────────────────────────────────────────────

# Why the races with the largest errors are hard, written after looking at each one.
# Shown in the "worst races" list; a race not listed here gets a reason from its numbers.
NOTES = {
    (2024, 8): 'Red flag on lap 1: everyone changed tyres during the stoppage and then ran to the end without '
               'stopping, so only 6 drivers have a second stint to test on, and at Monaco the pace is set by the '
               'car in front rather than by the tyres',
    (2024, 9): 'Wet start on a drying track: slicks only went on for the last third, and the track gained time '
               'every lap, which the model reads as tyres getting quicker with age (negative deg rates)',
    (2026, 16): 'A heavily interrupted race: about 320 driver laps under yellow, Safety Car or VSC and 73 pit '
                'stops, so the green runs are short, and one car ran intermediates in the opening laps',
}


def sessions():
    """Every race and sprint on disk that has a tyre_model.json, oldest first."""
    out = []
    for path in DATA.glob('*/*/*/tyre_model.json'):
        year, rnd, folder = path.relative_to(DATA).parts[:3]
        event = json.loads((path.parents[1] / 'event.json').read_text(encoding='utf-8'))
        out.append({'year': int(year), 'round': int(rnd), 'session': folder, 'name': event['name'],
                    'model': json.loads(path.read_text(encoding='utf-8'))})
    return sorted(out, key=lambda s: (s['year'], s['round'], s['session']))


def auto_reason(model):
    """A reason from the numbers alone, for races without a hand-written note."""
    excluded = model['laps_excluded']
    neutral = excluded.get('not_green', 0) + excluded.get('restart_lap', 0)
    if model['wet_running']:
        return 'mixed conditions: only the laps after the track dried are fitted'
    if neutral > 0.25 * (model['laps_used'] + neutral):
        return 'a large share of the race ran under yellow, Safety Car or VSC, leaving short green runs'
    if model['fuel_source'] == 'prior':
        return 'fuel and tyre wear could not be separated (the fuel slope is the prior)'
    return 'lap times scatter widely around the fit (traffic and tyre management)'


def fmt(value, digits=2, sign=False):
    if value is None:
        return '-'
    return f'{value:+.{digits}f}' if sign else f'{value:.{digits}f}'


def report(items):
    races = [s for s in items if s['session'] == 'race']
    modelled = [s for s in races if s['model']['modelled']]
    lodo = [s['model']['validation']['lodo_mae_s'] for s in modelled if s['model']['validation']['lodo_mae_s'] is not None]
    stint = [s['model']['validation']['stint_mae_s'] for s in modelled if s['model']['validation']['stint_mae_s'] is not None]
    bias = [s['model']['validation']['race_time_bias_s'] for s in modelled if s['model']['validation']['race_time_bias_s'] is not None]
    r2 = [s['model']['r2'] for s in modelled]
    rmse = [s['model']['rmse_s'] for s in modelled]
    prior = sum(s['model']['fuel_source'] == 'prior' for s in modelled)
    compounds = [(s, c, v) for s in modelled for c, v in s['model']['compounds'].items()]
    conf = {level: sum(v['confidence'] == level for _, _, v in compounds) for level in ('high', 'medium', 'low')}
    negative = sum(v['avg_deg_s_per_lap'] < 0 for _, _, v in compounds)
    worst = sorted((s for s in modelled if s['model']['validation']['lodo_mae_s'] is not None),
                   key=lambda s: -s['model']['validation']['lodo_mae_s'])[:3]
    sprints = [s for s in items if s['session'] != 'race']

    lines = [
        '# Tyre model validation',
        '',
        'Generated by `python pipeline/model/validate_model.py` from the `tyre_model.json` files on disk.',
        'Do not edit by hand. The method is in [MODEL.md](MODEL.md).',
        '',
        '## Headline numbers (races)',
        '',
        f'- Races: {len(races)}. Modelled: {len(modelled)}. Not modelled: {len(races) - len(modelled)}.',
        f'- Leave-one-driver-out error, per lap: median {np.median(lodo):.2f} s across races '
        f'(best {min(lodo):.2f} s, worst {max(lodo):.2f} s).',
        f'- Leave-one-driver-out error, per stint (total time over the stint\'s clean laps): median {np.median(stint):.1f} s.',
        f'- In-sample fit: median R² {np.median(r2):.2f}, median RMSE {np.median(rmse):.2f} s.',
        f'- Whole-race check: the model\'s race is a median {abs(np.median(bias)):.1f} s '
        f'{"quicker" if np.median(bias) < 0 else "slower"} than the real one over the green racing laps.',
        f'- Fuel slope taken from the prior ({tm.FUEL_PRIOR} s per lap) in {prior} of {len(modelled)} modelled races.',
        f'- Compound fits: {conf["high"]} high, {conf["medium"]} medium, {conf["low"]} low confidence; '
        f'{negative} have a negative deg rate (always low confidence).',
        '',
        '### The three worst races (leave-one-driver-out error per lap)',
        '',
    ]
    for s in worst:
        key = (s['year'], s['round'])
        lines.append(f'- {s["year"]} round {s["round"]}, {s["name"]}: {s["model"]["validation"]["lodo_mae_s"]:.2f} s. '
                     f'{NOTES.get(key) or auto_reason(s["model"]).capitalize()}.')
    lines += [
        '',
        '## What the model gets right',
        '',
        f'On a normal dry race the fit explains most of the lap-to-lap variation (median R² {np.median(r2):.2f}) and a '
        f'driver the model has never seen is predicted to a median {np.median(lodo):.2f} s per lap, using nothing but their '
        'first-stint pace and the tyres they were on. The ordering of the compounds, the size of the fuel effect and the '
        'difference between a low-wear and a high-wear track come out of the data without being told, and '
        f'{conf["high"]} of {len(compounds)} compound fits meet the high-confidence rule.',
        '',
        '## Where it fails',
        '',
        f'The error does not average out over a stint: the median stint is off by {np.median(stint):.1f} s in total, which is '
        'the same order as the gaps a strategy call is fought over. The model\'s race is also quicker than the real one '
        f'(median {abs(np.median(bias)):.1f} s over the green racing laps), because it is fitted on clean laps only. '
        f'{negative} compound fits have a negative deg rate, {prior} races needed the fuel prior, and '
        f'{len(races) - len(modelled)} races are not modelled at all.',
        '',
        '## Why',
        '',
        'Three things the lap times cannot tell apart. Traffic: a car stuck behind another laps slower on any tyre, and the '
        'model reads part of that as wear. Driver management: drivers lift to make a stint last, so the measured '
        'degradation is the degradation of a managed tyre, and a tyre pushed to the limit would wear faster than the fit '
        'says. Mixed conditions: a drying or rubbering-in track makes every lap faster regardless of tyre age, which the '
        'single fuel slope only partly absorbs (that is where the negative deg rates come from). Fuel burn and tyre age '
        'also rise together within a stint, so the two are only separated by stops at different times; when a race does '
        'not give enough of that, the fuel slope is fixed at the prior and the deg rates inherit its error.',
        '',
        '## Every race',
        '',
        '| Year | Rd | Race | Modelled | R² | RMSE s | LODO s/lap | LODO s/stint | Fuel s/lap | Deg rate s/lap (confidence) |',
        '|---|---|---|---|---|---|---|---|---|---|',
    ]

    def row(s):
        m = s['model']
        label = s['name'] + ('' if s['session'] == 'race' else ' (sprint)')
        if not m['modelled']:
            return f'| {s["year"]} | {s["round"]} | {label} | no: {m["reason"]} | - | - | - | - | - | - |'
        v = m['validation']
        deg = ', '.join(f'{c[0]} {x["avg_deg_s_per_lap"]:+.3f} ({x["confidence"]})' for c, x in m['compounds'].items())
        fuel = fmt(m['fuel_s_per_lap'], 3, True) + (' (prior)' if m['fuel_source'] == 'prior' else '')
        return (f'| {s["year"]} | {s["round"]} | {label} | yes | {m["r2"]:.2f} | {m["rmse_s"]:.2f} | '
                f'{fmt(v["lodo_mae_s"])} | {fmt(v["stint_mae_s"], 1)} | {fuel} | {deg} |')

    lines += [row(s) for s in races]
    if sprints:
        lines += ['', '## Sprints', '',
                  'Sprints are fitted too, but nobody changes tyres in one, so the fuel slope is almost always the prior, '
                  'compounds that no driver links are not comparable (only the biggest group is fitted) and there is '
                  'usually no second stint to test on.', '',
                  '| Year | Rd | Race | Modelled | R² | RMSE s | LODO s/lap | LODO s/stint | Fuel s/lap | Deg rate s/lap (confidence) |',
                  '|---|---|---|---|---|---|---|---|---|---|']
        lines += [row(s) for s in sprints]
    return '\n'.join(lines) + '\n'


def summary(items=None):
    """The headline numbers as a dict (the frontend's "How this works" page quotes them)."""
    items = items or sessions()
    races = [s for s in items if s['session'] == 'race']
    modelled = [s for s in races if s['model']['modelled']]
    def values(key):
        return [s['model']['validation'][key] for s in modelled if s['model']['validation'][key] is not None]
    return {
        'races': len(races), 'modelled': len(modelled),
        'median_lodo_mae_s': round(float(np.median(values('lodo_mae_s'))), 2),
        'median_stint_mae_s': round(float(np.median(values('stint_mae_s'))), 1),
        'median_race_time_bias_s': round(float(np.median(values('race_time_bias_s'))), 1),
        'median_r2': round(float(np.median([s['model']['r2'] for s in modelled])), 2),
        'median_rmse_s': round(float(np.median([s['model']['rmse_s'] for s in modelled])), 2),
        'fuel_prior_races': sum(s['model']['fuel_source'] == 'prior' for s in modelled),
    }


def main():
    items = sessions()
    REPORT.write_text(report(items), encoding='utf-8', newline='\n')
    print(f'{REPORT.relative_to(ROOT).as_posix()}: {len(items)} sessions')
    print(json.dumps(summary(items)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
