"""
The contract between data sources and the builders in build.py.

A source is created for ONE session (year, round, session code) and hands back plain
pandas objects with the fixed column names below. build.py never touches FastF1 or
OpenF1 directly, so both sources produce the same output files.

Times: every `Time` column is a Timedelta from the start of the session's timing feed
(any fixed zero is fine, as long as laps, track status and weather share it).
"""
from typing import Protocol

import pandas as pd

# laps(): one row per driver per lap. This is the frame the builders work on.
LAP_COLUMNS = [
    'Driver', 'Team', 'LapNumber',
    'LapTime', 'Sector1Time', 'Sector2Time', 'Sector3Time',   # Timedelta
    'Time',                                # Timedelta: session time at the END of the lap
    'Compound', 'TyreLife', 'Stint', 'FreshTyre',
    'PitInTime', 'PitOutTime',             # not-null = pitted at the end of / left the pits on this lap
    'Position',                            # position at the end of the lap
    'TrackStatus',                         # every status code seen during the lap, e.g. '1', '124'
    'IsAccurate', 'Deleted',
    'SpeedI1', 'SpeedI2', 'SpeedFL', 'SpeedST',
]
DRIVER_COLUMNS = ['Driver', 'DriverNumber', 'Team', 'TeamColor']
STINT_COLUMNS = ['Driver', 'Stint', 'Compound', 'LapStart', 'LapEnd', 'TyreAgeAtStart']
PIT_COLUMNS = ['Driver', 'LapNumber']                      # LapNumber = the in-lap
RESULT_COLUMNS = ['Abbreviation', 'DriverNumber', 'TeamName', 'TeamColor', 'Position',
                  'ClassifiedPosition', 'GridPosition', 'Status', 'Points', 'Laps',
                  'Time', 'Q1', 'Q2', 'Q3']
GRID_COLUMNS = ['Driver', 'GridPosition']
TRACK_STATUS_COLUMNS = ['Time', 'Status', 'Message']       # Status = F1 code: 1 2 4 5 6 7
RACE_CONTROL_COLUMNS = ['Time', 'Message', 'Lap']
WEATHER_COLUMNS = ['Time', 'TrackTemp', 'AirTemp', 'Humidity', 'WindSpeed', 'WindDirection', 'Rainfall']
POSITION_COLUMNS = ['Driver', 'LapNumber', 'Position']
TELEMETRY_COLUMNS = ['Distance', 'Speed', 'Throttle', 'Brake', 'nGear', 'DRS']   # Distance in metres
OUTLINE_COLUMNS = ['Distance', 'X', 'Y', 'Speed']


class Source(Protocol):
    name: str            # 'fastf1' or 'openf1', recorded in event.json and manifest.json

    def load(self) -> bool:
        """Fetch the session. False (with a log line) when the data is not complete yet."""

    def event(self) -> pd.Series:
        """Index: circuit (short name), total_laps (laps actually run; race and sprint only)."""

    def drivers(self) -> pd.DataFrame: ...
    def laps(self) -> pd.DataFrame: ...
    def stints(self) -> pd.DataFrame: ...
    def pits(self) -> pd.DataFrame: ...
    def results(self) -> pd.DataFrame: ...
    def grid(self) -> pd.DataFrame: ...
    def track_status(self) -> pd.DataFrame: ...
    def race_control(self) -> pd.DataFrame: ...
    def weather(self) -> pd.DataFrame: ...
    def positions_at_lap_end(self) -> pd.DataFrame: ...

    def fastest_lap_telemetry(self, driver: str):
        """(info, telemetry) for the driver's fastest lap of this session, or None.
        info: team, lap_time (Timedelta), segment ('Q1'/'Q2'/'Q3'/None), compound.
        telemetry: TELEMETRY_COLUMNS."""

    def circuit_outline(self) -> pd.DataFrame:
        """OUTLINE_COLUMNS for the fastest lap that has position data.
        .attrs carries 'driver' and 'lap_time'. Raises if no lap has position data."""

    def circuit_info(self):
        """(corners DataFrame [Number, Letter, X, Y, Distance, Angle], rotation in degrees)."""
