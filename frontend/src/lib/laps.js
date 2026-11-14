// race/laps.json is columnar (pipeline/SCHEMA.md): one row per driver per lap.
// parseLaps turns it, once, into typed arrays per driver, indexed by lap number
// (index 0 is unused), so the replay clock and the debrief can read a lap in O(1).

const UNKNOWN_COMPOUNDS = new Set(['', 'NAN', 'NONE', 'UNKNOWN'])

// 'SOFT' ... 'WET', or null when the data does not know ('nan', 'None', 'UNKNOWN', null)
export function cleanCompound(value) {
  const c = String(value ?? '').toUpperCase()
  return UNKNOWN_COMPOUNDS.has(c) ? null : c
}

export function parseLaps(json) {
  const col = Object.fromEntries(json.columns.map((name, i) => [name, i]))
  const rows = json.rows

  const lastLap = {}
  let totalLaps = 0
  for (const r of rows) {
    const d = r[col.driver], lap = r[col.lap]
    if (!(lastLap[d] >= lap)) lastLap[d] = lap
    if (lap > totalLaps) totalLaps = lap
  }

  const drivers = {}
  for (const code in lastLap) {
    const n = lastLap[code] + 1
    drivers[code] = {
      driver:   code,
      team:     null,
      laps:     lastLap[code],                    // highest lap number with a row
      has:      new Uint8Array(n),                // 1 where a row exists
      time:     new Float64Array(n).fill(NaN),    // lap_time_s, NaN when missing
      sectors:  new Uint8Array(n),                // how many of the three sector times exist
      position: new Uint8Array(n),                // 0 when missing
      compound: new Array(n).fill(null),
      tyreLife: new Uint16Array(n),
      stint:    new Uint8Array(n),
      pitIn:    new Uint8Array(n),
      pitOut:   new Uint8Array(n),
      green:    new Uint8Array(n),                // track_status is exactly "1"
      accurate: new Uint8Array(n),
      deleted:  new Uint8Array(n),
      status:   new Array(n).fill(''),            // raw track_status string
    }
  }

  for (const r of rows) {
    const d = drivers[r[col.driver]], i = r[col.lap]
    d.team        = r[col.team]
    d.has[i]      = 1
    d.time[i]     = r[col.lap_time_s] ?? NaN
    d.sectors[i]  = (r[col.sector1_s] != null) + (r[col.sector2_s] != null) + (r[col.sector3_s] != null)
    d.position[i] = r[col.position] ?? 0
    d.compound[i] = cleanCompound(r[col.compound])
    d.tyreLife[i] = r[col.tyre_life] ?? 0
    d.stint[i]    = r[col.stint] ?? 0
    d.pitIn[i]    = r[col.pit_in] ? 1 : 0
    d.pitOut[i]   = r[col.pit_out] ? 1 : 0
    d.status[i]   = String(r[col.track_status] ?? '')
    d.green[i]    = d.status[i] === '1' ? 1 : 0
    d.accurate[i] = r[col.is_accurate] ? 1 : 0
    d.deleted[i]  = r[col.deleted] ? 1 : 0
  }

  return { totalLaps, drivers }
}
