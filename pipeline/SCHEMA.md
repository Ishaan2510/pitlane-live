# Static race data schema (schema_version 1)

Written by `pipeline/build.py` into `frontend/public/data/`, served at `/data/...`.
All files are compact JSON. Times are seconds (3 decimals), speeds km/h (1 decimal),
coordinates FastF1 track units of 1/10 m (1 decimal). Missing values are `null`.

```
manifest.json
{year}/{round}/event.json
{year}/{round}/circuit.json                 from the Race session
{year}/{round}/race/replay.json
{year}/{round}/race/laps.json
{year}/{round}/race/results.json            written last: its presence marks a complete build
{year}/{round}/race/track_status.json
{year}/{round}/race/weather.json
{year}/{round}/race/pit_loss.json
{year}/{round}/quali/results.json           written last
{year}/{round}/quali/fastest/{DRIVER}.json
{year}/{round}/sprint/...                   same files as race/ (no circuit.json)
{year}/{round}/sprint_quali/...             same files as quali/
```

Session codes: `R` Race, `Q` Qualifying, `S` Sprint, `SQ` Sprint Qualifying.

## Sources

Every session is built from one of two sources and both write the same files:

- `fastf1`: sessions that are already in a local FastF1 cache (F1's timing archive has
  needed a login since October 2026, so nothing new comes from it).
- `openf1`: everything else, from the free OpenF1 REST API, with Jolpica as the fallback
  for a missing race classification.

`event.json` and each `manifest.json` entry record it per session in `source`.
Differences you can see in the data:

| | fastf1 | openf1 |
|---|---|---|
| Session time zero (`*_time_s` in `track_status.json`) | start of the timing feed, about an hour before lights out | the scheduled session start, so earlier messages are negative |
| Track status | F1's own status stream | rebuilt from race control messages (sector yellows, SC, VSC, red, "TRACK CLEAR") |
| Lap 1 | usually no lap or sector times | lap and sector times present |
| `time_s` of lapped cars in `results.json` | gap at the flag | `null` (OpenF1 only says "+1 LAP") |
| In-lap of a car that retires in the pits | `pit_in` is true | `pit_in` is false (no pit record) |
| `position` in `laps.json` | computed by FastF1 | F1's position feed at the end of the lap; differs on about 1% of laps, mostly lapped cars |
| `is_accurate` | FastF1's definition | timed lap with all sectors, not an in/out lap, no SC/VSC/red, not lap 1 |
| Telemetry (`circuit.json`, `quali/fastest`) | about 4 Hz car data merged with position data | about 3.7 Hz car data; distance is speed integrated over time, so it can drift a few metres per lap |
| Circuit corners | FastF1 `circuit_info` | same corner list (MultiViewer), `distance` taken from the nearest outline point |

## manifest.json

Rebuilt from the folders on disk after every run. Events are sorted newest first.
`sessions` lists what is actually built, in the order Q, SQ, S, R.

```json
{
  "generated_at": "2026-11-13T10:50:11Z",
  "schema_version": 1,
  "events": [
    { "year": 2025, "round": 8, "name": "Monaco Grand Prix", "country": "Monaco",
      "location": "Monaco", "date": "2025-05-25", "format": "conventional",
      "sessions": ["Q", "R"], "source": { "Q": "openf1", "R": "fastf1" },
      "built_at": "2026-11-13T10:50:11Z" }
  ]
}
```

## event.json

`total_laps` is the race distance actually run (`null` until the race is built).
`sessions` holds the start time of every session of the weekend the pipeline can build.
`source` says where each built session came from (`fastf1` or `openf1`).

```json
{ "year": 2025, "round": 8, "name": "Monaco Grand Prix", "country": "Monaco",
  "location": "Monaco", "circuit": "Monte Carlo", "date": "2025-05-25",
  "format": "conventional", "total_laps": 78,
  "sessions": { "Q": "2025-05-24T14:00:00Z", "R": "2025-05-25T13:00:00Z" },
  "source": { "Q": "openf1", "R": "fastf1" },
  "built_at": "2026-11-13T10:50:11Z" }
```

## race/replay.json

Lap-by-lap leaderboard for the replay and the pit-call simulation. Same shape the old
`{year}_R{round}_processed.json` had, except `lap_time` is **seconds as a number**
(was a pandas timedelta string) and the unused `distance` and `results` fields are gone.
Drivers are sorted by position. `gap` is the time behind the leader at the end of the
lap (`"LEADER"` for P1 or when unknown). `pit_in` = pitted at the end of this lap,
`pit_out` = left the pits at the start of this lap.

```json
{
  "year": 2025, "round": 8, "name": "Monaco Grand Prix", "circuit": "Monaco",
  "date": "2025-05-25T00:00:00", "total_laps": 78,
  "weather": { "track_temp": 41.6, "air_temp": 22.5, "humidity": 50.0,
               "wind_speed": 0.8, "wind_direction": 159, "rainfall": false },
  "laps": [
    { "lap_number": 2, "drivers": [
      { "driver": "NOR", "team": "McLaren", "position": 1, "lap_time": 104.634,
        "compound": "MEDIUM", "tire_life": 2, "pit_out": false, "pit_in": false,
        "avg_speed": 157.2, "max_speed": 252.0, "gap": "LEADER" },
      { "driver": "LEC", "team": "Ferrari", "position": 2, "lap_time": 104.769,
        "compound": "MEDIUM", "tire_life": 2, "pit_out": false, "pit_in": false,
        "avg_speed": 169.5, "max_speed": 236.0, "gap": "+1.276s" }
    ] }
  ]
}
```

## race/laps.json

Input for the strategy simulator and the degradation model. Columnar: one row per driver
per lap, sorted by lap then position. `track_status` is FastF1's string of every status
code seen during the lap (`"1"` = green all lap, `"124"` = green, yellow and SC).

```json
{
  "columns": ["driver", "team", "lap", "lap_time_s", "sector1_s", "sector2_s", "sector3_s",
              "compound", "tyre_life", "stint", "fresh_tyre", "pit_in", "pit_out",
              "position", "track_status", "is_accurate", "deleted"],
  "rows": [
    ["SAI", "Williams", 2, 111.609, 38.745, 46.984, 25.88, "HARD", 2, 1, true,
     false, false, 11, "16", false, false]
  ]
}
```

## race/results.json

From `session.results`, in classification order. `time_s` is the race time for the
winner and the gap to the winner for other cars on the lead lap (`null` otherwise).
`quali/results.json` has the same fields plus `q1_s`, `q2_s`, `q3_s`.

```json
[
  { "driver": "NOR", "number": "4", "team": "McLaren", "team_color": "#F47600",
    "position": 1, "classified_position": "1", "grid_position": 1, "status": "Finished",
    "points": 25.0, "laps": 78, "time_s": 6033.843 },
  { "driver": "GAS", "number": "10", "team": "Alpine", "team_color": "#00A1E8",
    "position": 20, "classified_position": "R", "grid_position": 17, "status": "Retired",
    "points": 0.0, "laps": 7, "time_s": null }
]
```

## race/track_status.json

`periods` come from `session.track_status`; each runs until the next status change.
`status` is one of `green`, `yellow`, `sc`, `vsc`, `vsc_ending`, `red` (`unknown` for a
code FastF1 does not document). Laps are the lap the leader was on; times are session
time, which starts well before lights out. `sc_periods` come from the race control
messages (`type` is `sc` or `vsc`); a Safety Car still out at the flag ends on the last lap.

```json
{
  "periods": [
    { "status": "green", "message": "AllClear", "start_lap": 1, "end_lap": 2,
      "start_time_s": 3438.05, "end_time_s": 3462.459 }
  ],
  "sc_periods": [ { "type": "vsc", "start_lap": 2, "end_lap": 4 } ]
}
```

## race/weather.json

`summary` is the block the old processed JSON carried (conditions at the end of the
session). `laps` is columnar: the weather sample nearest to the moment the leader
finished each lap.

```json
{
  "summary": { "track_temp": 41.6, "air_temp": 22.5, "humidity": 50.0,
               "wind_speed": 0.8, "wind_direction": 159, "rainfall": false },
  "laps": { "columns": ["lap", "track_temp", "air_temp", "humidity", "rainfall"],
            "rows": [[1, 43.9, 22.0, 51.0, false], [2, 42.7, 21.7, 53.0, false]] }
}
```

## race/pit_loss.json

Measured cost of a pit stop at this track.

- **Green stops** (`track_status` is exactly `"1"` on both the in-lap and the out-lap):
  `loss_s = in_lap + out_lap - 2 * ref_lap`, where `ref_lap` is the driver's median green,
  non-pit lap of the stint that ended with the stop (whole race if that stint has fewer
  than 3 such laps). `median_loss_s` is the median over these stops.
- **SC stops** (either lap saw SC, VSC or VSC ending, and no red flag): a green lap is the
  wrong yardstick, so `ref_lap` is half the median `(lap N + lap N+1)` of the cars that
  stayed out on those two laps. `median_loss_sc_s` is `null` with fewer than 2 such stops.
- Left out: lap 1 stops, stops under yellow only or red flag, stops with a missing lap time.

```json
{
  "median_loss_s": 18.968, "median_loss_sc_s": null, "green_stops": 36, "sc_stops": 0,
  "stops": [
    { "driver": "HUL", "lap": 12, "in_lap_s": 96.743, "out_lap_s": 78.279,
      "ref_lap_s": 80.974, "loss_s": 13.074, "condition": "green" }
  ]
}
```

## circuit.json

Track outline from the fastest race lap, one point every 10 m (`distance` in metres from
the start line). `corners` and `rotation` come from FastF1's `circuit_info`; rotate the
outline by `rotation` degrees to match the official track map. Replaces the old
`{year}_R{round}_circuit.json` (`coordinates` is now `points`, which also carry `speed`).

```json
{
  "name": "Monaco Grand Prix", "driver": "NOR", "lap_time_s": 73.221,
  "total_distance": 3280, "rotation": 315.0,
  "corners": [ { "number": 1, "letter": "", "x": -7381.1, "y": -4719.9,
                 "distance": 186.5, "angle": 140.4 } ],
  "points": [ { "x": -7669.0, "y": -6498.0, "distance": 0, "speed": 268.9 },
              { "x": -7673.6, "y": -6431.5, "distance": 10, "speed": 270.3 } ]
}
```

## quali/fastest/{DRIVER}.json

The driver's fastest qualifying lap from `get_car_data().add_distance()`, resampled to a
5 m grid. Arrays are parallel, one value per grid point. `speed`, `throttle` and `rpm`
are interpolated; `brake` (0/1), `n_gear` and `drs` take the nearest original sample.
`segment` is `Q1`, `Q2` or `Q3`. About 5 KB per km of track; budget 60 KB per file.

```json
{
  "driver": "VER", "team": "Red Bull Racing", "lap_time_s": 77.019, "segment": "Q3",
  "compound": "SOFT", "step_m": 5,
  "distance": [500, 505, 510, 515],
  "speed":    [312.0, 312.0, 312.0, 312.0],
  "throttle": [100, 100, 100, 100],
  "brake":    [0, 0, 0, 0],
  "n_gear":   [8, 8, 8, 8],
  "rpm":      [11081, 11078, 11073, 11068],
  "drs":      [0, 0, 0, 0]
}
```
