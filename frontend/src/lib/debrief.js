// The numbers behind the Debrief tab. Pure functions of the static race files:
// `laps` is parseLaps(laps.json), `results` is results.json (may be null),
// `clock` is buildRaceClock(), `bands` is statusBands(), `stops` is pitStops().

import { quantile } from 'd3-array'
import { TEAM_COLORS } from '@/data/drivers'
import { stints, leaders } from './raceEvents'

/**
 * Every driver with laps, in finishing order (classification when there are results,
 * else laps completed then last known position).
 *   { driver, team, color, grid, finish, status, laps, second }
 * `second` marks the lower-placed driver of a team: charts draw that line dashed.
 */
export function driverList(laps, results) {
  const res = Object.fromEntries((results || []).map(r => [r.driver, r]))
  const list = Object.values(laps.drivers).map(d => {
    const r = res[d.driver]
    return {
      driver: d.driver,
      team:   d.team,
      color:  r?.team_color || TEAM_COLORS[d.team] || '#888888',
      grid:   r?.grid_position > 0 ? r.grid_position : null,      // null: pit lane start or unknown
      finish: r?.position ?? null,
      status: r?.status ?? null,
      laps:   d.laps,
      _last:  d.position[d.laps] || 99,
    }
  })
  list.sort((a, b) => (a.finish ?? 99) - (b.finish ?? 99) || b.laps - a.laps || a._last - b._last)
  const seen = new Set()
  for (const d of list) {
    d.second = seen.has(d.team)
    seen.add(d.team)
    delete d._last
  }
  return list
}

// Stints per driver: { VER: [{ stint, compound, startLap, endLap, startAge }], ... }
export function strategy(laps) {
  return Object.fromEntries(Object.values(laps.drivers).map(d => [d.driver, stints(d)]))
}

// Position at the end of each lap; index 0 is the grid slot. null where unknown.
export function positionSeries(laps, drivers) {
  const out = {}
  for (const meta of drivers) {
    const d = laps.drivers[meta.driver]
    const series = [meta.grid]
    for (let n = 1; n <= d.laps; n++) series.push(d.position[n] || null)
    out[meta.driver] = series
  }
  return out
}

/**
 * Gap in seconds at the end of each lap to a reference: the leader (reference null)
 * or another driver. Index = lap, index 0 = 0. Negative = ahead of the reference.
 * Stops where either car stops.
 */
export function gapSeries(clock, reference = null) {
  const ref = reference ? clock.byCode[reference] : null
  const out = {}
  for (const d of clock.drivers) {
    const last = ref ? Math.min(d.done, ref.done) : d.done
    const series = [0]
    for (let n = 1; n <= last; n++) series.push(d.times[n] - (ref ? ref.times[n] : clock.spine[n]))
    out[d.driver] = series
  }
  return out
}

// A clean lap: green flag all lap, timed and accurate, not an in or out lap, not lap 1
export function isCleanLap(d, n) {
  return n > 1 && Number.isFinite(d.time[n]) && !!d.green[n] && !!d.accurate[n] && !d.pitIn[n] && !d.pitOut[n]
}

/**
 * Race pace per driver from clean laps, sorted by median (fastest first):
 *   { driver, n, median, q1, q3, low, high, delta }
 * low/high are the whiskers: the furthest laps within 1.5 x IQR of the box.
 * delta is the gap of the median to the fastest median. Drivers with no clean lap are left out.
 */
export function racePace(laps) {
  const rows = []
  for (const d of Object.values(laps.drivers)) {
    const times = []
    for (let n = 2; n <= d.laps; n++) if (isCleanLap(d, n)) times.push(d.time[n])
    if (!times.length) continue
    times.sort((a, b) => a - b)
    const q1 = quantile(times, 0.25), median = quantile(times, 0.5), q3 = quantile(times, 0.75)
    const reach = 1.5 * (q3 - q1)
    rows.push({
      driver: d.driver,
      n: times.length,
      median, q1, q3,
      low:  times.find(t => t >= q1 - reach),
      high: times.findLast(t => t <= q3 + reach),
    })
  }
  rows.sort((a, b) => a.median - b.median)
  for (const r of rows) r.delta = r.median - rows[0].median
  return rows
}

// True when anyone ran intermediates or wets: pace is then not comparable lap to lap
export function hadWetRunning(laps) {
  return Object.values(laps.drivers).some(d => d.compound.some(c => c === 'INTERMEDIATE' || c === 'WET'))
}

// Laps led per driver: { NOR: 44, VER: 27 }. The counts add up to the race distance.
export function lapsLed(laps, results) {
  const out = {}
  const lead = leaders(laps, results)
  for (let n = 1; n <= laps.totalLaps; n++) if (lead[n]) out[lead[n]] = (out[lead[n]] || 0) + 1
  return out
}

/**
 * Pit stop table rows: pitStops() plus the loss against the track's median.
 * A stop made under SC or VSC is compared with the Safety Car median instead.
 * Tyre changes during a red flag are not pit stops and are left out.
 */
export function pitTable(stops, pitLoss) {
  return stops.filter(s => s.status !== 'red').map(s => {
    const median = s.condition === 'sc' ? pitLoss?.median_loss_sc_s : pitLoss?.median_loss_s
    return {
      ...s,
      vsMedian: s.loss != null && median != null ? s.loss - median : null,
      gained: s.posBefore && s.posAfter ? s.posBefore - s.posAfter : null,
    }
  })
}

/**
 * The headline cards. Any field is null when the data cannot say.
 *   winner   { driver, team, margin, runnerUp }   margin in seconds to P2
 *   climber  { driver, grid, finish, gained }      most places gained, grid to flag
 *   mostLed  { driver, laps, total }
 *   fastest  { driver, lap, time }
 *   winnerStops, safetyCars, virtualSafetyCars, redFlags
 */
export function headlines({ laps, results, bands, stops }) {
  const res = results || []
  const first = res.find(r => r.position === 1) || null
  const second = res.find(r => r.position === 2) || null

  let climber = null
  for (const r of res) {
    if (!(r.grid_position > 0) || !/^\d+$/.test(String(r.classified_position))) continue
    const gained = r.grid_position - r.position
    if (!climber || gained > climber.gained) climber = { driver: r.driver, grid: r.grid_position, finish: r.position, gained }
  }
  if (climber && climber.gained <= 0) climber = null

  const led = Object.entries(lapsLed(laps, results)).sort((a, b) => b[1] - a[1])[0]

  let fastest = null
  for (const d of Object.values(laps.drivers)) {
    for (let n = 1; n <= d.laps; n++) {
      const t = d.time[n]
      if (Number.isFinite(t) && !d.deleted[n] && (!fastest || t < fastest.time)) fastest = { driver: d.driver, lap: n, time: t }
    }
  }

  const count = type => bands.filter(b => b.type === type).length
  return {
    winner: first && { driver: first.driver, team: first.team, margin: second?.time_s ?? null, runnerUp: second?.driver ?? null },
    climber,
    mostLed: led ? { driver: led[0], laps: led[1], total: laps.totalLaps } : null,
    fastest,
    winnerStops: first ? stops.filter(s => s.driver === first.driver && s.status !== 'red').length : null,
    safetyCars: count('sc'),
    virtualSafetyCars: count('vsc'),
    redFlags: count('red'),
  }
}
