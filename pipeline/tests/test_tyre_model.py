"""Tyre model: synthetic races with known answers, the refusals, and three real races."""
import json
from pathlib import Path

import numpy as np
import pytest

import build
from model import tyre_model as tm
from model import validate_model as vm

COLS = build.LAPS_COLUMNS
DATA = Path(__file__).resolve().parents[2] / 'frontend' / 'public' / 'data'

FUEL = -0.04
OFFSET = {'SOFT': -0.8, 'MEDIUM': 0.0, 'HARD': 0.5}
DEG = {'SOFT': 0.12, 'MEDIUM': 0.07, 'HARD': 0.03}


def race(plans, total=60, fuel=FUEL, deg=DEG, offset=OFFSET, noise=0.25, seed=1, status=None, quad=None):
    """
    A synthetic laps.json. plans: [[(compound, last lap of the stint), ...] per driver].
    Lap time = base + fuel * lap + offset + deg * life (+ quad * life^2) + noise.
    """
    rng = np.random.default_rng(seed)
    rows = []
    for i, plan in enumerate(plans):
        base, lap, driver = 90 + 0.15 * i, 1, f'D{i:02d}'
        for stint, (compound, last) in enumerate(plan, start=1):
            for life, n in enumerate(range(lap, last + 1), start=1):
                time = (base + fuel * n + offset[compound] + deg[compound] * life
                        + (quad or {}).get(compound, 0) * life * life + rng.normal(0, noise))
                r = dict.fromkeys(COLS)
                r.update(driver=driver, team='T', lap=n, lap_time_s=round(time, 3), compound=compound,
                         tyre_life=life, stint=stint, pit_in=n == last and last != total,
                         pit_out=life == 1 and n > 1, pit_stop=n == last and last != total,
                         position=i + 1, track_status=(status or {}).get(n, '1'), is_accurate=True, deleted=False)
                rows.append([r[c] for c in COLS])
            lap = last + 1
    return {'columns': COLS, 'rows': rows}


def varied_plans(n=12, total=60):
    """One- and two-stop races on different compounds with the stops spread out."""
    plans = []
    for i in range(n):
        first = 14 + 2 * i
        if i % 3 == 0:
            plans.append([('SOFT', first), ('HARD', total)])
        elif i % 3 == 1:
            plans.append([('MEDIUM', first), ('HARD', 38 + i), ('SOFT', total)])
        else:
            plans.append([('MEDIUM', first + 6), ('HARD', total)])
    return plans


# ── recovery ──────────────────────────────────────────────────────────────────

def test_known_deg_rates_are_recovered():
    model = tm.build_tyre_model(race(varied_plans()))
    assert model['modelled'] and model['fuel_source'] == 'fit'
    assert model['reference_compound'] == 'HARD'                       # the most-used compound
    assert abs(model['fuel_s_per_lap'] - FUEL) < 0.01
    for c in ('SOFT', 'MEDIUM', 'HARD'):
        got = model['compounds'][c]
        assert got['form'] == 'linear'
        assert abs(got['deg_s_per_lap'] - DEG[c]) < 0.015, c
        assert abs(got['offset_s'] - (OFFSET[c] - OFFSET['HARD'])) < 0.3, c
        assert abs(got['deg_s_per_lap'] - DEG[c]) < 4 * got['deg_se'], c      # the standard error is honest
        assert abs(got['residual_sd_s'] - 0.25) < 0.05
        assert got['laps'] == len(got['points']) and got['max_life_seen'] >= 20
    assert model['r2'] > 0.8 and abs(model['rmse_s'] - 0.25) < 0.03
    v = model['validation']
    assert v['n_drivers'] == 12 and v['lodo_mae_s'] < 0.35           # about the noise: 0.25 * sqrt(2/pi) = 0.20
    assert abs(v['race_time_bias_s']) < 1.0


def test_exclusions_are_counted_by_reason():
    status = {**{n: '4' for n in (30, 31)}, 32: '41'}                 # Safety Car on laps 30-32
    table = race(varied_plans(), status=status)
    col = {c: i for i, c in enumerate(COLS)}
    slow = next(r for r in table['rows'] if r[col['driver']] == 'D00' and r[col['lap']] == 10)
    slow[col['lap_time_s']] += 9.0                                    # let the leaders by: above 107%
    deleted = next(r for r in table['rows'] if r[col['driver']] == 'D01' and r[col['lap']] == 10)
    deleted[col['deleted']] = True
    laps, racing, excluded, info = tm.clean_laps(table)
    assert excluded['lap_1'] == 12
    # 12 cars x 3 Safety Car laps and 12 restart laps, less the ones that were in or out laps
    assert 30 <= excluded['not_green'] <= 36 and 10 <= excluded['restart_lap'] <= 12
    assert excluded['slower_than_107pct'] == 1 and excluded['deleted'] == 1
    assert excluded['in_or_out_lap'] > 12
    assert not any(l['lap'] in (1, 30, 31, 32, 33) for l in laps)
    assert len(racing) == len(laps) + excluded['restart_lap'] + 2     # plus the slow lap and the deleted lap
    assert info == {'wet_running': False, 'wet_share': 0.0, 'dry_from_lap': 1, 'unknown_share': 0.0, 'total_laps': 60}


def test_quadratic_term_is_kept_only_where_it_helps():
    # softs fall off a cliff, the others wear in a straight line
    plans = [[('SOFT', 18 + i), ('HARD', 60)] if i % 2 else [('HARD', 30 + i), ('SOFT', 60)] for i in range(12)]
    model = tm.build_tyre_model(race(plans, deg={**DEG, 'SOFT': 0.02}, quad={'SOFT': 0.008}, noise=0.15))
    assert model['compounds']['SOFT']['form'] == 'quadratic'
    assert abs(model['compounds']['SOFT']['quad_s_per_lap2'] - 0.008) < 0.003
    assert model['compounds']['HARD']['form'] == 'linear' and model['compounds']['HARD']['quad_s_per_lap2'] == 0
    assert model['compounds']['SOFT']['avg_deg_s_per_lap'] > 0.15     # the average slope, not the linear term
    # and a plain linear race stays linear
    assert all(c['form'] == 'linear' for c in tm.build_tyre_model(race(varied_plans()))['compounds'].values())


# ── fuel / tyre collinearity ──────────────────────────────────────────────────

def test_fuel_prior_when_nobody_stops():
    # one stint each: tyre life is the lap number, so fuel and wear cannot be told apart
    plans = [[('MEDIUM', 24)] for _ in range(12)]
    model = tm.build_tyre_model(race(plans, total=24))
    assert model['fuel_source'] == 'prior' and model['fuel_s_per_lap'] == tm.FUEL_PRIOR
    assert model['fuel_se'] is None
    # the deg rate takes up whatever the prior got wrong: true 0.07, fuel -0.04 vs prior -0.035
    assert abs(model['compounds']['MEDIUM']['deg_s_per_lap'] - (0.07 - 0.04 + 0.035)) < 0.01
    assert model['validation']['n_drivers'] == 0 and model['validation']['lodo_mae_s'] is None


def test_fuel_prior_when_the_fitted_slope_is_not_believable():
    # a track that gets slower all race (rain coming): the free fit gives a positive "fuel" slope
    table = race(varied_plans(), fuel=+0.03)
    free = tm.fit(tm.clean_laps(table)[0])
    assert free['fuel'] > tm.FUEL_RANGE[1]
    model = tm.build_tyre_model(table)
    assert model['fuel_source'] == 'prior' and model['fuel_s_per_lap'] == tm.FUEL_PRIOR


# ── refusals ──────────────────────────────────────────────────────────────────

def test_wet_race_is_refused():
    wet = race([[('INTERMEDIATE', 30), ('WET', 60)] for _ in range(10)], deg={'INTERMEDIATE': 0.1, 'WET': 0.1},
               offset={'INTERMEDIATE': 0, 'WET': 2})
    model = tm.build_tyre_model(wet)
    assert not model['modelled'] and 'wet' in model['reason'] and model['wet_running']
    assert model['compounds'] == {} and model['validation'] is None
    assert model['laps_excluded']['wet_tyre'] > 500


def test_drying_race_is_fitted_on_the_dry_laps_only_or_refused():
    drying = [[('INTERMEDIATE', 12 + i % 3), ('MEDIUM', 34 + i), ('SOFT', 60)] for i in range(12)]
    model = tm.build_tyre_model(race(drying, deg={**DEG, 'INTERMEDIATE': 0.1}, offset={**OFFSET, 'INTERMEDIATE': 8}))
    assert model['modelled'] and model['wet_running'] and model['dry_from_lap'] == 15
    assert set(model['compounds']) == {'MEDIUM', 'SOFT'}
    assert model['laps_excluded']['before_track_dry'] > 0
    # one car gambling on intermediates for three laps does not make it a wet race
    gamble = varied_plans()
    gamble[0] = [('INTERMEDIATE', 3), ('MEDIUM', 30), ('HARD', 60)]
    model = tm.build_tyre_model(race(gamble, deg={**DEG, 'INTERMEDIATE': 0.1}, offset={**OFFSET, 'INTERMEDIATE': 8}))
    assert model['modelled'] and not model['wet_running'] and 0 < model['wet_share'] < 0.05
    assert model['dry_from_lap'] == 4 and 'INTERMEDIATE' not in model['compounds']
    # slicks only for the last few laps: not enough to fit
    late = [[('INTERMEDIATE', 55), ('SOFT', 60)] for _ in range(12)]
    model = tm.build_tyre_model(race(late, deg={**DEG, 'INTERMEDIATE': 0.1}, offset={**OFFSET, 'INTERMEDIATE': 8}))
    assert not model['modelled'] and 'wet race' in model['reason']


def test_unknown_compounds_are_refused_above_five_percent():
    table = race(varied_plans())
    col = COLS.index('compound')
    for r in table['rows'][::12]:                                     # 8% of laps
        r[col] = 'UNKNOWN'
    model = tm.build_tyre_model(table)
    assert not model['modelled'] and 'unknown' in model['reason']
    table = race(varied_plans())
    for r in table['rows'][::40]:                                     # 2.5%: fitted without them
        r[col] = 'UNKNOWN'
    assert tm.build_tyre_model(table)['modelled']


def test_compounds_no_driver_links_are_not_compared():
    # a sprint: half the field on mediums, half on softs, nobody stops
    plans = [[('MEDIUM' if i < 7 else 'SOFT', 24)] for i in range(12)]
    model = tm.build_tyre_model(race(plans, total=24))
    assert list(model['compounds']) == ['MEDIUM']
    assert model['laps_excluded']['compound_not_comparable'] == 5 * 23


# ── confidence ────────────────────────────────────────────────────────────────

def test_confidence_rule():
    assert tm.confidence(400, 12, 0.05, 0.004)[0] == 'high'
    assert tm.confidence(100, 6, 0.05, 0.02)[0] == 'medium'
    assert tm.confidence(400, 12, 0.05, 0.02)[0] == 'medium'          # plenty of laps, loose deg rate
    assert tm.confidence(40, 3, 0.05, 0.004)[0] == 'low'
    assert tm.confidence(400, 12, -0.01, 0.004)[0] == 'low'           # tyres do not get faster with age
    assert tm.confidence(400, 12, 0.45, 0.004)[0] == 'low'
    assert all(isinstance(tm.confidence(*args)[1], str) for args in [(400, 12, 0.05, 0.004), (40, 3, 0.05, 0.1)])


def test_soft_slower_than_hard_when_new_is_marked_low():
    # the softs here are 1 s SLOWER than the hards when new
    model = tm.build_tyre_model(race(varied_plans(), offset={'SOFT': 1.5, 'MEDIUM': 0.0, 'HARD': 0.5}))
    assert model['compounds']['SOFT']['confidence'] == 'low'
    assert 'not physical' in model['compounds']['SOFT']['confidence_reason']
    assert model['compounds']['HARD']['confidence'] != 'low'


# ── real races ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize('year, rnd', [(2024, 1), (2025, 14), (2026, 3)])
def test_real_race_gives_physically_sensible_values(year, rnd):
    folder = DATA / str(year) / str(rnd) / 'race'
    model = tm.model_for_folder(folder)
    assert model['modelled'] and model['r2'] > 0.5 and model['rmse_s'] < 1.5
    assert tm.FUEL_RANGE[0] <= model['fuel_s_per_lap'] <= tm.FUEL_RANGE[1]
    compounds = model['compounds']
    for name, c in compounds.items():
        assert 0 <= c['avg_deg_s_per_lap'] <= 0.4 or c['confidence'] == 'low', name
        assert c['deg_se'] > 0 and c['laps'] >= tm.MIN_COMPOUND_LAPS
    def new(c):
        return compounds[c]['offset_s'] + compounds[c]['deg_s_per_lap'] + compounds[c]['quad_s_per_lap2']
    if all(c in compounds and compounds[c]['laps'] >= tm.MEDIUM[0] for c in ('SOFT', 'HARD')):
        assert new('SOFT') < new('HARD') + tm.ORDER_TOLERANCE_S or 'low' in (compounds['SOFT']['confidence'], compounds['HARD']['confidence'])
    v = model['validation']
    assert v['n_drivers'] >= 10 and 0.1 < v['lodo_mae_s'] < 2.0
    # the file on disk is this model (build.py wrote it from the same laps.json)
    on_disk = folder / 'tyre_model.json'
    if on_disk.exists():
        assert json.loads(on_disk.read_text(encoding='utf-8')) == json.loads(json.dumps(model))


def test_validation_report_lists_every_session():
    items = vm.sessions()
    if not items:
        pytest.skip('no tyre_model.json on disk')
    text = vm.report(items)
    assert text.count('\n| 20') == len(items)
    assert 'What the model gets right' in text and 'Where it fails' in text and '## Why' in text
    head = vm.summary(items)
    assert head['modelled'] <= head['races'] and 0.1 < head['median_lodo_mae_s'] < 2.0
