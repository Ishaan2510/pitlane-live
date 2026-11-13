"""
race_data.py — where scoring and the summary endpoint get a finished race from.

Primary source: the static files the data pipeline publishes on the CDN
(PUBLIC_DATA_BASE_URL, e.g. https://pitlane-live-f1.vercel.app/data):
    {year}/{round}/event.json          name, date, race distance
    {year}/{round}/race/results.json   official classification -> finishing order
    {year}/{round}/race/laps.json      per-lap rows -> stints and pit laps

Fallback: the legacy backend/fastf1_cache/processed/{year}_R{round}_processed.json,
used when PUBLIC_DATA_BASE_URL is unset or the static files are missing.

Both come back in the legacy "race_data" shape, so build_pit_registry,
extract_finishing_order and extract_stint_sequences work on either.
"""

import os
import time

import requests

from app.services.fastf1_service import fastf1_service

CACHE_TTL  = 600   # seconds a fetched race stays in memory
CACHE_SIZE = 4     # races kept (the Render box has 512 MB)
TIMEOUT    = 10


def race_from_static(event: dict, results: list, laps: dict) -> dict:
    """Assemble event.json + race/results.json + race/laps.json into the legacy race_data shape."""
    columns = laps['columns']
    by_lap = {}
    for row in laps['rows']:
        lap = dict(zip(columns, row))
        by_lap.setdefault(lap['lap'], []).append({
            'driver':    lap['driver'],
            'team':      lap['team'],
            'position':  lap['position'],
            'compound':  lap['compound'] or 'UNKNOWN',
            'tire_life': lap['tyre_life'] or 0,
            'stint':     lap['stint'],
            'pit_in':    bool(lap['pit_in']),
            'pit_out':   bool(lap['pit_out']),
        })

    total_laps = event.get('total_laps') or max(by_lap, default=0)
    return {
        'year':       event['year'],
        'round':      event['round'],
        'name':       event['name'],
        'circuit':    event.get('location'),
        'date':       event.get('date'),
        'total_laps': total_laps,
        'results':    results,
        'laps': [
            {'lap_number': n,
             'drivers': sorted(by_lap.get(n, []), key=lambda d: d['position'] or 999)}
            for n in range(1, total_laps + 1)
        ],
    }


class RaceDataSource:
    def __init__(self):
        self._cache = {}   # (year, round) -> (fetched_at, race_data)

    def _fetch(self, url: str):
        res = requests.get(url, timeout=TIMEOUT)
        res.raise_for_status()
        return res.json()

    def _from_static(self, year: int, round_num: int):
        base = (os.getenv('PUBLIC_DATA_BASE_URL') or '').rstrip('/')
        if not base:
            return None
        prefix = f'{base}/{year}/{round_num}'
        try:
            return race_from_static(
                self._fetch(f'{prefix}/event.json'),
                self._fetch(f'{prefix}/race/results.json'),
                self._fetch(f'{prefix}/race/laps.json'),
            )
        except Exception as e:   # 404, network error, HTML instead of JSON, unexpected shape
            print(f'[race_data] no static data for {year} R{round_num} ({e}); trying legacy file')
            return None

    def get_race(self, year: int, round_num: int):
        """
        Race in the legacy race_data shape, or None if neither source has it.
        Shared between requests: read it, never mutate it. Misses are not cached,
        so a race that has just been published is picked up on the next call.
        """
        key = (year, round_num)
        hit = self._cache.get(key)
        if hit and time.time() - hit[0] < CACHE_TTL:
            return hit[1]

        data = self._from_static(year, round_num)
        if data is None:
            return fastf1_service.load_processed(year, round_num)   # has its own LRU cache

        self._cache.pop(key, None)
        self._cache[key] = (time.time(), data)
        while len(self._cache) > CACHE_SIZE:
            self._cache.pop(next(iter(self._cache)))                # oldest first
        return data


race_data_source = RaceDataSource()
