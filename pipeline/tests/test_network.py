"""
Tests against real sessions. Skipped by default; run with
    python -m pytest pipeline -m network
FASTF1_CACHE must point at a FastF1 cache that holds the 2025 R8, 2025 R9 and 2024 R13
races (F1's archive needs a login, so they cannot be downloaded). OpenF1 is fetched live.
"""
import json

import pytest

import build
from parity import compare, table
from sources.fastf1_source import enable_cache

pytestmark = pytest.mark.network


@pytest.fixture(scope='module')
def fastf1():
    import fastf1
    enable_cache()
    return fastf1


@pytest.mark.parametrize('year,round_num', [(2025, 8), (2025, 9), (2024, 13)])
def test_pit_loss_is_plausible(fastf1, year, round_num):
    session = fastf1.get_session(year, round_num, 'R')
    session.load(laps=True, telemetry=False, weather=False, messages=False)
    loss = build.build_pit_loss(session.laps)
    assert loss['green_stops'] >= 5
    assert 15 <= loss['median_loss_s'] <= 35


def test_fastf1_and_openf1_build_the_same_race(fastf1, tmp_path, monkeypatch):
    """2025 R8 race from both sources: lap times within 0.05 s on 95% of laps, identical
    compounds, stint boundaries, pit-in laps and classified order, pit loss within 1.5 s."""
    event = fastf1.get_event(2025, 8)
    for source in ('fastf1', 'openf1'):
        monkeypatch.setattr(build, 'OUT_DIR', tmp_path / source)
        built, failed = build.build_event(2025, event, ['R'], source=source)
        assert built == ['R'] and failed == [], f'{source} did not build'
    rows, ok = compare(tmp_path / 'fastf1' / '2025' / '8', tmp_path / 'openf1' / '2025' / '8')
    print('\n' + table(rows, 'fastf1', 'openf1'))
    assert ok, '\n' + table(rows, 'fastf1', 'openf1')


def test_build_2025_r8_writes_every_file(fastf1, tmp_path, monkeypatch):
    """Auto source: the race comes from the FastF1 cache, qualifying from OpenF1."""
    monkeypatch.setattr(build, 'OUT_DIR', tmp_path)
    event = fastf1.get_event(2025, 8)
    built, failed = build.build_event(2025, event, ['Q', 'R'])
    assert built == ['Q', 'R'] and failed == []
    manifest = build.rebuild_manifest(tmp_path)

    ev = tmp_path / '2025' / '8'
    expected = [tmp_path / 'manifest.json', ev / 'event.json', ev / 'circuit.json',
                ev / 'quali' / 'results.json']
    expected += [ev / 'race' / f'{n}.json'
                 for n in ('replay', 'laps', 'results', 'track_status', 'weather', 'pit_loss')]
    for path in expected:
        assert path.exists(), path
    fastest = list((ev / 'quali' / 'fastest').glob('*.json'))
    assert len(fastest) >= 18
    for path in expected + fastest:
        json.loads(path.read_text(encoding='utf-8'))
    assert all(p.stat().st_size < 60_000 for p in fastest)
    assert sum(p.stat().st_size for p in ev.rglob('*.json')) < 1_500_000
    assert manifest['events'][0]['sessions'] == ['Q', 'R']
    assert manifest['events'][0]['source'] == {'Q': 'openf1', 'R': 'fastf1'}
