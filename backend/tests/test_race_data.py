"""RaceDataSource: static pipeline files first, legacy processed JSON as fallback."""
import json
from pathlib import Path

import pytest

from app.services import race_data
from app.services.fastf1_service import fastf1_service
from app.services.race_prediction_scoring import extract_finishing_order, extract_stint_sequences
from app.services.scoring_service import build_pit_registry

REPO = Path(__file__).resolve().parents[2]
STATIC = REPO / 'frontend' / 'public' / 'data'
BASE = 'https://example.test/data'


@pytest.fixture
def source(monkeypatch):
    """A RaceDataSource whose HTTP fetch reads frontend/public/data instead of the network."""
    src = race_data.RaceDataSource()
    calls = []

    def fetch(url):
        calls.append(url)
        path = STATIC / url.removeprefix(BASE + '/')
        if not path.exists():
            raise FileNotFoundError(url)
        return json.loads(path.read_text(encoding='utf-8'))

    monkeypatch.setattr(src, '_fetch', fetch)
    monkeypatch.setenv('PUBLIC_DATA_BASE_URL', BASE + '/')
    src.calls = calls
    return src


def test_static_race_matches_legacy_file_for_scoring(source):
    """2025 R8 from results.json + laps.json scores exactly like the legacy processed file."""
    static = source.get_race(2025, 8)
    legacy = fastf1_service.load_processed(2025, 8)

    assert static is not legacy and static['name'] == legacy['name'] == 'Monaco Grand Prix'
    assert static['total_laps'] == legacy['total_laps'] == 78
    assert extract_finishing_order(static) == extract_finishing_order(legacy)
    assert extract_finishing_order(static)[0] == 'NOR'
    assert build_pit_registry(static) == build_pit_registry(legacy)
    assert extract_stint_sequences(static) == extract_stint_sequences(legacy)


def test_fetched_race_is_cached_in_memory(source):
    first = source.get_race(2025, 8)
    assert len(source.calls) == 3            # event.json, results.json, laps.json
    assert source.get_race(2025, 8) is first
    assert len(source.calls) == 3


def test_falls_back_to_legacy_when_static_file_is_missing(source):
    assert not (STATIC / '2024' / '1').exists()      # not built by the pipeline yet
    race = source.get_race(2024, 1)
    assert race is fastf1_service.load_processed(2024, 1)
    assert (2024, 1) not in source._cache            # misses are not cached


def test_falls_back_to_legacy_when_base_url_is_unset(source, monkeypatch):
    monkeypatch.delenv('PUBLIC_DATA_BASE_URL')
    assert source.get_race(2025, 8) is fastf1_service.load_processed(2025, 8)
    assert source.calls == []


def test_unknown_race_is_none(source):
    assert source.get_race(1999, 1) is None
