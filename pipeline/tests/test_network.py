"""
Tests against real sessions. Skipped by default; run with
    python -m pytest pipeline -m network
Point FASTF1_CACHE at a warm cache to avoid downloading.
"""
import json
import os
from pathlib import Path

import pytest

import build

pytestmark = pytest.mark.network


@pytest.fixture(scope='module')
def fastf1():
    import fastf1
    cache = Path(os.getenv('FASTF1_CACHE') or build.ROOT / '.fastf1-cache')
    cache.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(cache))
    return fastf1


@pytest.mark.parametrize('year,round_num', [(2025, 8), (2025, 9), (2024, 13)])
def test_pit_loss_is_plausible(fastf1, year, round_num):
    session = fastf1.get_session(year, round_num, 'R')
    session.load(laps=True, telemetry=False, weather=False, messages=False)
    loss = build.build_pit_loss(session.laps)
    assert loss['green_stops'] >= 5
    assert 15 <= loss['median_loss_s'] <= 35


def test_build_2025_r8_writes_every_file(fastf1, tmp_path, monkeypatch):
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
