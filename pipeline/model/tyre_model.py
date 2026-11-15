"""
Tyre degradation model: one linear least-squares fit per race or sprint, across the field.

    lap_time = driver_base[d] + fuel * lap_number + compound_offset[c] + deg[c] * tyre_life (+ quad[c] * tyre_life^2)

The maths, the clean-lap rules and the confidence rule are written up in MODEL.md.
build.py calls build_tyre_model() for every race and sprint and writes tyre_model.json.

    python pipeline/model/tyre_model.py                 # (re)write tyre_model.json for every session on disk
    python pipeline/model/tyre_model.py path/to/race    # these folders only
"""
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # so `model` imports when run as a script

DRY = ('SOFT', 'MEDIUM', 'HARD')
WET = ('INTERMEDIATE', 'WET')

FUEL_RANGE = (-0.09, -0.01)        # s per lap: a fitted slope outside this is not believable
FUEL_PRIOR = -0.035                # s per lap, used when the fit cannot separate fuel from tyres
RACING_LAP = 1.30                  # the whole-race check ignores laps beyond 130%: the car was not racing
SLOW_LAP = 1.07                    # a lap above 107% of the driver's median clean lap is not a racing lap
WET_RACE_SHARE = 0.05              # this share of laps on intermediates or wets makes it a wet race
MAX_UNKNOWN_SHARE = 0.05           # more laps than this on an unknown compound: no model
MIN_COMPOUND_LAPS = 15             # a compound needs this many clean laps ...
MIN_COMPOUND_DRIVERS = 2           # ... from this many drivers to be fitted
MIN_LAPS = 60                      # clean laps needed for a model at all
MIN_DRIVERS = 5
MIN_TWO_STINT_DRIVERS = 3          # fewer drivers with two fitted stints: fuel cannot be told from tyres
QUAD_GAIN = 0.05                   # the quadratic term must lower the leave-one-driver-out error by this share

# Confidence per compound: (clean laps, drivers, standard error of the deg rate in s/lap)
HIGH = (150, 8, 0.010)
MEDIUM = (60, 4, 0.025)
ORDER_TOLERANCE_S = 0.1            # a softer tyre may look this much slower than a harder one when new: fit noise
DEG_SANE = (0.0, 0.4)              # s per lap; a dry tyre outside this is a sign the fit is confounded


# ── clean laps ────────────────────────────────────────────────────────────────

def read_laps(table):
    """laps.json -> {driver: [row dict, ...] in lap order}."""
    by_driver = {}
    for row in table['rows']:
        r = dict(zip(table['columns'], row))
        by_driver.setdefault(r['driver'], []).append(r)
    for rows in by_driver.values():
        rows.sort(key=lambda r: r['lap'])
    return by_driver


def comparable_compounds(laps):
    """
    Compound offsets are only comparable through drivers who ran both compounds. If the
    compounds fall into groups no driver links (a sprint where nobody changes tyres), the
    offset between the groups cannot be told from the drivers' pace. Returns the biggest
    linked group (by laps).
    """
    group = {l['compound']: l['compound'] for l in laps}

    def root(c):
        while group[c] != c:
            c = group[c]
        return c

    ran = {}
    for lap in laps:
        ran.setdefault(lap['driver'], set()).add(lap['compound'])
    for compounds in ran.values():
        first, *rest = sorted(compounds)
        for c in rest:
            group[root(c)] = root(first)
    size = Counter(root(l['compound']) for l in laps)
    if not size:
        return set()
    biggest = max(size, key=lambda c: (size[c], c))
    return {c for c in group if root(c) == biggest}


def clean_laps(table):
    """
    The laps the model is fitted on, and why the others were left out.
    Returns (laps, racing, excluded, info):
      laps      [{driver, lap, time, compound, life, stint}] clean laps
      racing    the same plus the green racing laps the fit drops as untypical (slow,
                inaccurate, deleted, first lap after a restart): used to check race times
      excluded  Counter of reasons
      info      {wet_running, wet_share, dry_from_lap, unknown_share, total_laps}
    """
    by_driver = read_laps(table)
    rows = [r for d in by_driver.values() for r in d]
    wet_laps = [r['lap'] for r in rows if r['compound'] in WET]
    dry_from = max(wet_laps) + 1 if wet_laps else 1          # the lap after anyone last ran a wet tyre
    wet_share = len(wet_laps) / len(rows) if rows else 0.0
    info = {
        'wet_running': wet_share >= WET_RACE_SHARE,              # a couple of cars gambling on inters is not a wet race
        'wet_share': round(wet_share, 3),
        'dry_from_lap': dry_from,
        'unknown_share': sum(r['compound'] == 'UNKNOWN' for r in rows) / len(rows) if rows else 0.0,
        'total_laps': max((r['lap'] for r in rows), default=0),
    }

    excluded, candidates, racing = Counter(), [], []
    for driver, laps in by_driver.items():
        previous = None
        for r in laps:
            status = str(r['track_status'] or '')
            after_neutral = previous is not None and previous['lap'] == r['lap'] - 1 \
                and any(c in str(previous['track_status'] or '') for c in '4567')
            previous = r
            lap = {'driver': driver, 'lap': r['lap'], 'time': r['lap_time_s'], 'compound': r['compound'],
                   'life': r['tyre_life'], 'stint': r['stint']}
            if r['lap_time_s'] is None:
                reason = 'no_lap_time'
            elif r['lap'] == 1:
                reason = 'lap_1'
            elif r['pit_in'] or r['pit_out'] or r.get('pit_stop'):
                reason = 'in_or_out_lap'
            elif status != '1':
                reason = 'not_green'
            elif r['compound'] == 'UNKNOWN' or r['tyre_life'] is None or r['stint'] is None:
                reason = 'unknown_compound'
            elif r['compound'] in WET:
                reason = 'wet_tyre'
            elif r['lap'] < dry_from:
                reason = 'before_track_dry'
            else:
                racing.append(lap)
                if after_neutral:
                    reason = 'restart_lap'
                elif r['deleted']:
                    reason = 'deleted'
                elif not r['is_accurate']:
                    reason = 'not_accurate'
                else:
                    candidates.append(lap)
                    continue
            excluded[reason] += 1

    # laps spent letting cars by, nursing damage, ...: above 107% of the driver's own median
    median = {}
    for lap in candidates:
        median.setdefault(lap['driver'], []).append(lap['time'])
    median = {d: float(np.median(t)) for d, t in median.items()}
    kept = []
    for lap in candidates:
        if lap['time'] > SLOW_LAP * median[lap['driver']]:
            excluded['slower_than_107pct'] += 1
        else:
            kept.append(lap)

    # a compound hardly anyone ran cannot be fitted
    laps_of, drivers_of = Counter(l['compound'] for l in kept), {}
    for lap in kept:
        drivers_of.setdefault(lap['compound'], set()).add(lap['driver'])
    usable = {c for c in laps_of if laps_of[c] >= MIN_COMPOUND_LAPS and len(drivers_of[c]) >= MIN_COMPOUND_DRIVERS}
    excluded['compound_too_few_laps'] += sum(1 for l in kept if l['compound'] not in usable)
    kept = [l for l in kept if l['compound'] in usable]

    comparable = comparable_compounds(kept)
    excluded['compound_not_comparable'] += sum(1 for l in kept if l['compound'] not in comparable)
    usable &= comparable
    kept = [l for l in kept if l['compound'] in usable]

    # "racing" drops laps far off the pace (a car limping back, a lap that includes a stop
    # on track): they are not something any strategy model is meant to rebuild
    racing = [l for l in racing if l['compound'] in usable
              and l['time'] <= RACING_LAP * median.get(l['driver'], float('inf'))]
    return kept, racing, +excluded, info


# ── the fit ───────────────────────────────────────────────────────────────────

def fit(laps, quadratic=(), fuel=None):
    """
    Ordinary least squares on the clean laps. `quadratic` lists the compounds that get a
    tyre_life^2 term; `fuel` fixes the fuel slope instead of fitting it.
    Returns a dict of parameters, standard errors and residuals.
    """
    drivers = sorted({l['driver'] for l in laps})
    used = Counter(l['compound'] for l in laps)
    compounds = sorted(used, key=lambda c: (-used[c], c))          # reference = the most-used compound
    quadratic = [c for c in compounds if c in quadratic]

    names = [('base', d) for d in drivers]
    if fuel is None:
        names.append(('fuel', None))
    names += [('offset', c) for c in compounds[1:]] + [('deg', c) for c in compounds] + [('quad', c) for c in quadratic]
    col = {name: i for i, name in enumerate(names)}

    X = np.zeros((len(laps), len(names)))
    y = np.empty(len(laps))
    for i, l in enumerate(laps):
        X[i, col[('base', l['driver'])]] = 1
        if fuel is None:
            X[i, col[('fuel', None)]] = l['lap']
        if ('offset', l['compound']) in col:
            X[i, col[('offset', l['compound'])]] = 1
        X[i, col[('deg', l['compound'])]] = l['life']
        if ('quad', l['compound']) in col:
            X[i, col[('quad', l['compound'])]] = l['life'] ** 2
        y[i] = l['time'] - (fuel or 0.0) * l['lap']

    beta, _, rank, _ = np.linalg.lstsq(X, y, rcond=None)
    residuals = y - X @ beta
    dof = max(len(laps) - rank, 1)
    cov = float(residuals @ residuals) / dof * np.linalg.pinv(X.T @ X)

    def value(kind, key):
        return float(beta[col[(kind, key)]]) if (kind, key) in col else 0.0

    def variance(weights):                       # variance of a weighted sum of coefficients
        w = np.zeros(len(names))
        for name, weight in weights.items():
            if name in col:
                w[col[name]] = weight
        return max(float(w @ cov @ w), 0.0)

    lives = {c: [l['life'] for l in laps if l['compound'] == c] for c in compounds}
    out = {
        'drivers': drivers, 'compounds': compounds, 'quadratic': quadratic, 'rank_deficient': rank < len(names),
        'base': {d: value('base', d) for d in drivers},
        'fuel': value('fuel', None) if fuel is None else fuel,
        'fuel_se': variance({('fuel', None): 1}) ** 0.5 if fuel is None else None,
        'offset': {c: value('offset', c) for c in compounds},
        'offset_se': {c: variance({('offset', c): 1}) ** 0.5 for c in compounds},
        'deg': {c: value('deg', c) for c in compounds},
        'quad': {c: value('quad', c) for c in compounds},
        'max_life': {c: int(max(lives[c])) for c in compounds},
        'residuals': residuals,
    }
    # The deg rate people read: the average slope over the tyre ages actually seen.
    # For a linear compound that is the coefficient itself.
    out['avg_deg'], out['deg_se'] = {}, {}
    for c in compounds:
        span = min(lives[c]) + max(lives[c])                 # d/dx of a + b x + q x^2, averaged = b + q (x0 + x1)
        out['avg_deg'][c] = out['deg'][c] + out['quad'][c] * span
        out['deg_se'][c] = variance({('deg', c): 1, ('quad', c): span}) ** 0.5
    return out


def predict(params, base, lap):
    """Model lap time for a lap dict, given the driver's base pace."""
    c, life = lap['compound'], lap['life']
    return (base + params['fuel'] * lap['lap'] + params['offset'][c]
            + params['deg'][c] * life + params['quad'][c] * life * life)


def two_stint_drivers(laps):
    stints = {}
    for l in laps:
        stints.setdefault(l['driver'], set()).add(l['stint'])
    return sum(1 for s in stints.values() if len(s) >= 2)


def fit_with_fallback(laps, quadratic=(), force_prior=False):
    """
    Fit with a free fuel slope; if that slope is not believable (fuel and tyre age are
    partly collinear, fully so when nobody ran two stints) refit with it fixed at the prior.
    Returns (params, 'fit' | 'prior').
    """
    if not force_prior and two_stint_drivers(laps) >= MIN_TWO_STINT_DRIVERS:
        params = fit(laps, quadratic)
        if FUEL_RANGE[0] <= params['fuel'] <= FUEL_RANGE[1] and not params['rank_deficient']:
            return params, 'fit'
    return fit(laps, quadratic, fuel=FUEL_PRIOR), 'prior'


# ── model form ────────────────────────────────────────────────────────────────

def choose_quadratic(laps, force_prior):
    """Compounds that get a tyre_life^2 term. Each compound is tried on its own: the term is
    kept when it lowers that compound's leave-one-driver-out error by more than QUAD_GAIN
    and the curve bends upwards (the tyre falling away, not a fluke of the noise)."""
    from model.validate_model import leave_one_driver_out
    linear = leave_one_driver_out(laps, (), force_prior)
    chosen = []
    for c in sorted({l['compound'] for l in laps}):
        before = linear['errors'].get(c)
        after = leave_one_driver_out(laps, (c,), force_prior)['errors'].get(c)
        if before and after and np.mean(after) < (1 - QUAD_GAIN) * np.mean(before)                 and fit_with_fallback(laps, (c,), force_prior)[0]['quad'][c] > 0:
            chosen.append(c)
    return chosen, linear


# ── confidence ────────────────────────────────────────────────────────────────

def confidence(n_laps, n_drivers, deg, deg_se):
    """('high' | 'medium' | 'low', the reason in a few words). The rule is in MODEL.md."""
    if not DEG_SANE[0] <= deg <= DEG_SANE[1]:
        return 'low', f'a deg rate of {deg:+.3f} s per lap is not physical: fuel, track evolution or traffic is mixed in'
    for level, (laps, drivers, se) in (('high', HIGH), ('medium', MEDIUM)):
        if n_laps >= laps and n_drivers >= drivers and deg_se <= se:
            return level, f'{n_laps} clean laps from {n_drivers} drivers, deg rate known to ±{deg_se:.3f} s per lap'
    if n_laps < MEDIUM[0]:
        return 'low', f'only {n_laps} clean laps'
    if n_drivers < MEDIUM[1]:
        return 'low', f'only {n_drivers} drivers ran it'
    return 'low', f'the deg rate is only known to ±{deg_se:.3f} s per lap'


# ── the whole thing ───────────────────────────────────────────────────────────

def not_modelled(reason, info, excluded):
    return {'modelled': False, 'reason': reason, 'wet_running': info['wet_running'], 'wet_share': info['wet_share'],
            'dry_from_lap': info['dry_from_lap'], 'laps_used': 0, 'laps_excluded': dict(excluded),
            'compounds': {}, 'drivers': {}, 'validation': None}


def build_tyre_model(table, results=None):
    """laps.json (and results.json, for the whole-race check) -> the tyre_model.json dict."""
    from model.validate_model import leave_one_driver_out, race_time_check
    laps, racing, excluded, info = clean_laps(table)
    if info['unknown_share'] > MAX_UNKNOWN_SHARE:
        return not_modelled(f'the compound is unknown on {info["unknown_share"]:.0%} of laps', info, excluded)
    n_drivers = len({l['driver'] for l in laps})
    if len(laps) < MIN_LAPS or n_drivers < MIN_DRIVERS:
        if info['wet_running']:
            why = 'wet race: too few laps on dry tyres after the track dried' if info['dry_from_lap'] <= info['total_laps'] \
                else 'wet race: intermediate or wet tyres were in use to the end'
        else:
            why = f'only {len(laps)} clean laps from {n_drivers} drivers'
        return not_modelled(why, info, excluded)

    force_prior = fit_with_fallback(laps)[1] == 'prior'
    quadratic, _ = choose_quadratic(laps, force_prior)
    params, fuel_source = fit_with_fallback(laps, quadratic, force_prior)
    lodo = leave_one_driver_out(laps, quadratic, force_prior)

    times = np.array([l['time'] for l in laps])
    res = params['residuals']
    compounds = {}
    for c in params['compounds']:
        mask = np.array([l['compound'] == c for l in laps])
        n, drivers = int(mask.sum()), len({l['driver'] for l in laps if l['compound'] == c})
        level, why = confidence(n, drivers, params['avg_deg'][c], params['deg_se'][c])
        compounds[c] = {
            'offset_s':         round(params['offset'][c], 4),
            'offset_se':        round(params['offset_se'][c], 4),
            'form':             'quadratic' if c in quadratic else 'linear',
            'deg_s_per_lap':    round(params['deg'][c], 5),        # coefficient of tyre_life
            'quad_s_per_lap2':  round(params['quad'][c], 6),       # coefficient of tyre_life^2 (0 when linear)
            'avg_deg_s_per_lap': round(params['avg_deg'][c], 4),   # average slope over the ages seen
            'deg_se':           round(params['deg_se'][c], 4),
            'laps':             n,
            'drivers':          drivers,
            'max_life_seen':    params['max_life'][c],
            'residual_sd_s':    round(float(np.sqrt(np.mean(res[mask] ** 2))), 3),
            'confidence':       level,
            'confidence_reason': why,
            'lodo_mae_s':       round(float(np.mean(lodo['errors'][c])), 3) if lodo['errors'].get(c) else None,
            # [tyre_life, lap time with fuel and driver pace taken out], for the degradation chart
            'points':           [[l['life'], round(l['time'] - params['base'][l['driver']] - params['fuel'] * l['lap'], 2)]
                                 for l in laps if l['compound'] == c],
        }

    # A softer tyre is quicker than a harder one when both are new. Where the fit says
    # otherwise by more than ORDER_TOLERANCE_S (and both have enough laps to mean it), the offset is confounded with
    # something else, and the compound with fewer laps behind it is marked low.
    def new_tyre(c):
        return compounds[c]['offset_s'] + compounds[c]['deg_s_per_lap'] + compounds[c]['quad_s_per_lap2']

    fitted = [c for c in DRY if c in compounds and compounds[c]['laps'] >= MEDIUM[0]]
    for i, softer in enumerate(fitted):
        for harder in fitted[i + 1:]:
            if new_tyre(softer) > new_tyre(harder) + ORDER_TOLERANCE_S:
                weak = min((softer, harder), key=lambda c: compounds[c]['laps'])
                compounds[weak]['confidence'] = 'low'
                compounds[weak]['confidence_reason'] = (
                    f'the fit has new {softer.lower()}s slower than new {harder.lower()}s, which is not physical: '
                    'the cars on each compound were not comparable')

    all_errors = [e for errs in lodo['errors'].values() for e in errs]
    classified = None
    if results:
        classified = {r['driver'] for r in results if str(r.get('classified_position', '')).isdigit()}
    check = race_time_check(params, racing, classified) or {}
    return {
        'modelled':           True,
        'reason':             None,
        'wet_running':        info['wet_running'],
        'wet_share':          info['wet_share'],
        'dry_from_lap':       info['dry_from_lap'],
        'reference_compound': params['compounds'][0],
        'fuel_s_per_lap':     round(params['fuel'], 5),
        'fuel_se':            round(params['fuel_se'], 5) if params['fuel_se'] is not None else None,
        'fuel_source':        fuel_source,
        'r2':                 round(1 - float(res @ res) / float(((times - times.mean()) ** 2).sum()), 4),
        'rmse_s':             round(float(np.sqrt(np.mean(res ** 2))), 3),
        'laps_used':          len(laps),
        'laps_excluded':      dict(excluded),
        'compounds':          compounds,
        'drivers':            {d: round(b, 3) for d, b in params['base'].items()},
        'validation': {
            'lodo_mae_s':  round(float(np.mean(all_errors)), 3) if all_errors else None,
            'stint_mae_s': round(float(np.mean(lodo['stints'])), 2) if lodo['stints'] else None,
            'n_drivers':   lodo['n_drivers'],
            'race_time_mae_s':     check.get('race_time_mae_s'),
            'race_time_bias_s':    check.get('race_time_bias_s'),
            'between_stops_mae_s': check.get('between_stops_mae_s'),
        },
    }


def model_for_folder(session_dir):
    d = Path(session_dir)
    table = json.loads((d / 'laps.json').read_text(encoding='utf-8'))
    results = d / 'results.json'
    return build_tyre_model(table, json.loads(results.read_text(encoding='utf-8')) if results.exists() else None)


def main(argv=None):
    args = argv if argv is not None else sys.argv[1:]
    root = Path(__file__).resolve().parents[2] / 'frontend' / 'public' / 'data'
    folders = [Path(a) for a in args] or sorted(p.parent for p in root.glob('*/*/*/laps.json'))
    for folder in folders:
        model = model_for_folder(folder)
        tmp = folder / 'tyre_model.json.tmp'
        tmp.write_text(json.dumps(model, separators=(',', ':'), allow_nan=False), encoding='utf-8')
        tmp.replace(folder / 'tyre_model.json')
        print(folder.as_posix(), 'modelled' if model['modelled'] else f'NOT modelled: {model["reason"]}', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
