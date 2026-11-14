# The tyre model

`pipeline/model/tyre_model.py` fits one model per race and per sprint and writes
`{session}/tyre_model.json`. The Strategy tab and the degradation chart on the Debrief tab
read that file. How well it works, race by race, is in [VALIDATION.md](VALIDATION.md).

## What it says

A lap time is the sum of four things and whatever is left over:

```
lap_time = driver_base[d] + fuel * lap_number + compound_offset[c] + deg[c] * tyre_life + noise
```

- `driver_base[d]`: one number per driver. How quick that car and driver are in this
  race, on a new set of the reference compound, with the fuel load of "lap 0".
- `fuel`: one number per race, in seconds per lap. Cars get lighter as they burn fuel and
  the track usually gets quicker as rubber goes down, so this is expected to be negative.
  It is shared by the whole field.
- `compound_offset[c]`: how much slower (or quicker) compound `c` is than the reference
  compound when both are new. The reference is the compound with the most clean laps; its
  offset is 0.
- `deg[c]`: seconds lost per lap of tyre age on compound `c`. This is the degradation rate.
- `tyre_life` is the age of the set at the end of the lap (a new set shows 1 on its first
  lap; a used set starts higher).

The fit is ordinary least squares over every clean lap of the race at once (numpy
`lstsq`): one column per driver, one for the lap number, one per non-reference compound,
one per compound multiplied by tyre life. Nothing is tuned per track.

## Which laps count

Only clean laps are fitted. A lap is left out, with the reason counted in
`laps_excluded`, when:

| Reason | Rule |
|---|---|
| `no_lap_time` | the lap has no time |
| `lap_1` | the first lap (standing start) |
| `in_or_out_lap` | the lap ends or starts in the pit lane |
| `not_green` | the track status was anything but green at any point in the lap |
| `unknown_compound` | the compound, tyre age or stint is unknown |
| `wet_tyre` | intermediate or wet tyres |
| `before_track_dry` | a dry-tyre lap from before the last lap anyone ran a wet-weather tyre |
| `restart_lap` | the first lap after a Safety Car, VSC or red flag |
| `deleted` | the stewards deleted it |
| `not_accurate` | the source marks the lap as not accurate |
| `slower_than_107pct` | more than 107% of that driver's median clean lap (letting cars by, damage) |
| `compound_too_few_laps` | the compound has fewer than 15 clean laps or fewer than 2 drivers |
| `compound_not_comparable` | no driver ran both this compound and the others (see below) |

A compound offset is only known through drivers who ran both compounds: if half the field
runs mediums and half softs and nobody changes (a sprint), the gap between the two cannot
be told from the gap between the drivers. Compounds are grouped by the drivers that link
them and only the biggest group is fitted.

## Fuel and tyres rise together

Within a stint the lap number and the tyre age go up together, so "the car got lighter"
and "the tyre got older" look the same. They are only separated by stops made at
different times. When that is not enough the fitted fuel slope goes somewhere silly, and
the degradation rates go wrong with it. So:

- if the fitted `fuel` is outside -0.09 to -0.01 s per lap, or
- fewer than 3 drivers have two fitted stints, or the fit is rank deficient,

the model is refitted with the fuel slope fixed at **-0.035 s per lap** and the file says
`fuel_source: "prior"`. Otherwise `fuel_source` is `"fit"`. With the prior, any error in
it goes straight into every degradation rate (too much fuel effect means too much
degradation, and the other way round).

## Straight line or curve

A second form adds a term in tyre age squared for a compound:

```
... + deg[c] * tyre_life + quad[c] * tyre_life^2
```

Each compound is tried on its own. The curve is kept only when it lowers that compound's
leave-one-driver-out error (below) by more than 5% and bends upwards (`quad > 0`: the
tyre falling away faster as it ages). Otherwise the compound stays a straight line and
`quad_s_per_lap2` is 0. For a curved compound `deg_s_per_lap` is the linear coefficient
and `avg_deg_s_per_lap` is the average slope over the tyre ages actually seen, which is
the number to quote; for a straight line the two are the same.

## Wet races and unknown tyres

- A race with any intermediate or wet running is fitted on dry-tyre laps only, and only
  from the lap after anyone last ran a wet-weather tyre (`dry_from_lap`). If that leaves
  fewer than 60 clean laps or fewer than 5 drivers, the race is `modelled: false` with the
  reason.
- `wet_share` is the share of all laps run on intermediates or wets, and `wet_running` is
  true when it is 5% or more (a couple of cars gambling on intermediates for a few laps
  does not make a wet race). The Strategy tab does not simulate a race with
  `wet_running: true` even when the dry part could be fitted, because the moment to switch
  to slicks decides those races and the model knows nothing about it.
- A race with an `UNKNOWN` compound on more than 5% of its laps is `modelled: false`.
- Any race with fewer than 60 clean laps or fewer than 5 drivers is `modelled: false`.

## Confidence

Each compound gets `high`, `medium` or `low`, with the reason in `confidence_reason`:

| Level | Clean laps | Drivers | Standard error of the deg rate |
|---|---|---|---|
| high | at least 150 | at least 8 | at most 0.010 s per lap |
| medium | at least 60 | at least 4 | at most 0.025 s per lap |
| low | anything else | | |

Two things force `low` whatever the counts:

- a deg rate below 0 or above 0.4 s per lap. Tyres do not get quicker with age; a negative
  rate means track evolution or traffic has leaked into it.
- the fit has a softer compound more than 0.1 s slower than a harder one when both are new
  (and both have at least 60 laps). This is common: the softer tyre is usually the one on
  the car in the opening stint, with the field bunched up and everyone saving tyres. The cars on each compound were not comparable; the compound with
  fewer laps is marked.

In the simulator a stint longer than `max_life_seen` (the oldest tyre of that compound in
the race) is an extrapolation and is treated as low confidence as well.

## What is in the file

```json
{
  "modelled": true, "reason": null, "wet_running": false, "wet_share": 0.0, "dry_from_lap": 1,
  "reference_compound": "HARD",
  "fuel_s_per_lap": -0.0562, "fuel_se": 0.0031, "fuel_source": "fit",
  "r2": 0.87, "rmse_s": 0.61, "laps_used": 617,
  "laps_excluded": { "lap_1": 22, "in_or_out_lap": 56, "not_green": 190 },
  "compounds": {
    "HARD": { "offset_s": 0.0, "offset_se": 0.0, "form": "linear",
              "deg_s_per_lap": 0.0412, "quad_s_per_lap2": 0.0, "avg_deg_s_per_lap": 0.0412,
              "deg_se": 0.0061, "laps": 456, "drivers": 20, "max_life_seen": 31,
              "residual_sd_s": 0.59, "confidence": "high",
              "confidence_reason": "456 clean laps from 20 drivers, deg rate known to ±0.006 s per lap",
              "lodo_mae_s": 0.52,
              "points": [[3, 0.21], [4, 0.05]] }
  },
  "drivers": { "VER": 96.412 },
  "validation": { "lodo_mae_s": 0.54, "stint_mae_s": 7.4, "n_drivers": 19,
                  "race_time_mae_s": 1.3, "race_time_bias_s": -0.86, "between_stops_mae_s": 1.1 }
}
```

- `offset_se` and `deg_se` are the standard errors from the fit. `residual_sd_s` is the
  spread of that compound's laps around the fit. The simulator draws from all three.
- `points` are the clean laps as `[tyre_life, lap time minus driver base minus fuel * lap]`:
  what is left is the compound offset plus degradation plus noise. The degradation chart
  plots them with the fitted line.
- `drivers` is `driver_base`. The model's lap time for a driver is
  `drivers[d] + fuel_s_per_lap * lap + offset_s + deg_s_per_lap * life + quad_s_per_lap2 * life^2`.

## How it is checked

`pipeline/model/validate_model.py`:

- **Leave one driver out.** Fit without a driver. Take that driver's base pace from their
  first stint only. Predict the clean laps of their later stints from the tyres they were
  really on. `lodo_mae_s` is the mean absolute error per lap and `stint_mae_s` the mean
  absolute error of a stint's total time over its clean laps. `n_drivers` is how many
  drivers could be tested (they need two fitted stints).
- **Whole race.** For every classified driver, rebuild the time of their green racing laps
  from the model, stint by stint, and compare with what they did; everything else in their
  race (in-laps, out-laps, Safety Car laps) is taken as it happened. This includes the laps
  the fit drops as untypical, up to 130% of the driver's median. `race_time_bias_s` is
  negative when the model's race is quicker than the real one, which it normally is: the
  model is fitted on clean laps and a real race has traffic and mistakes in it.

## What it does not know

- Traffic. A car held up runs slower on any tyre; some of that is read as wear.
- Tyre management. The rates are those of tyres driven the way the drivers chose to drive
  them. A tyre pushed harder to make a different strategy work would wear faster.
- Track evolution beyond a straight line, temperature changes, wind, damage.
- The warm-up of a new tyre and the cliff at the end of its life, unless the curve is kept.
- Anything about a tyre older than the oldest one seen in that race.
