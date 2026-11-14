import { describe, expect, it } from 'vitest'
import { buildRaceClock } from '../raceClock'
import { statusBands, pitStops, lapStatus } from '../raceEvents'
import { driverList, strategy, positionSeries, gapSeries, racePace, lapsLed, pitTable, headlines, hadWetRunning } from '../debrief'
import { loadRace } from './helpers'

const RACES = [
  [2025, 3,  'Japan 2025: green all the way'],
  [2026, 19, 'Mexico City 2026: SC, VSC, red flag, retirements'],
]

describe.each(RACES)('debrief %i/%i (%s)', (year, round) => {
  const race = loadRace(year, round)
  const { laps, results, rawLaps } = race
  const col = Object.fromEntries(rawLaps.columns.map((c, i) => [c, i]))
  const rowsOf = code => rawLaps.rows.filter(r => r[col.driver] === code)
  const bands = statusBands(race.trackStatus, laps.totalLaps)
  const stops = pitStops(laps, race.pitLoss, bands)
  const drivers = driverList(laps, results)

  it('lists every driver with laps, classified cars in classification order', () => {
    expect(drivers.length).toBe(Object.keys(laps.drivers).length)
    const withLaps = results.filter(r => laps.drivers[r.driver]).map(r => r.driver)
    expect(drivers.map(d => d.driver)).toEqual(withLaps)
  })

  it('stint counts and lengths match laps.json', () => {
    const plan = strategy(laps)
    for (const d of drivers) {
      const rows = rowsOf(d.driver)
      expect(plan[d.driver].length, d.driver).toBe(new Set(rows.map(r => r[col.stint])).size)
      const lapsInStints = plan[d.driver].reduce((sum, s) => sum + s.endLap - s.startLap + 1, 0)
      expect(lapsInStints, d.driver).toBe(rows.length)
    }
  })

  it('laps led add up to the race distance', () => {
    const led = lapsLed(laps, results)
    expect(Object.values(led).reduce((a, b) => a + b, 0)).toBe(race.replay.total_laps)
    // and agree with P1 in the raw rows
    const p1 = {}
    for (const r of rawLaps.rows) if (r[col.position] === 1) p1[r[col.driver]] = (p1[r[col.driver]] || 0) + 1
    expect(led).toEqual(p1)
  })

  it('biggest climber matches grid and finish in results.json', () => {
    const h = headlines({ laps, results, bands, stops })
    const best = Math.max(...results.filter(r => r.grid_position > 0 && /^\d+$/.test(r.classified_position)).map(r => r.grid_position - r.position))
    const r = results.find(x => x.driver === h.climber.driver)
    expect(h.climber.gained).toBe(best)
    expect(h.climber.grid).toBe(r.grid_position)
    expect(h.climber.finish).toBe(r.position)
    expect(r.grid_position - r.position).toBe(best)
  })

  it('headline numbers come from the files', () => {
    const h = headlines({ laps, results, bands, stops })
    expect(h.winner.driver).toBe(results[0].driver)
    expect(h.winner.margin).toBe(results[1].time_s)
    expect(h.mostLed.total).toBe(race.replay.total_laps)
    const best = Math.min(...rawLaps.rows.filter(r => r[col.lap_time_s] != null && !r[col.deleted]).map(r => r[col.lap_time_s]))
    expect(h.fastest.time).toBe(best)
    expect(h.safetyCars).toBe(race.trackStatus.sc_periods.filter(p => p.type === 'sc').length)
    expect(h.virtualSafetyCars).toBe(race.trackStatus.sc_periods.filter(p => p.type === 'vsc').length)
    const winnerRows = rowsOf(results[0].driver)
    const redStops = stops.filter(s => s.driver === results[0].driver && s.status === 'red').length
    expect(h.winnerStops + redStops).toBe(new Set(winnerRows.map(r => r[col.stint])).size - 1)
  })

  it('position series starts on the grid and follows laps.json', () => {
    const series = positionSeries(laps, drivers)
    for (const d of drivers) {
      expect(series[d.driver][0]).toBe(d.grid)
      expect(series[d.driver].length).toBe(laps.drivers[d.driver].laps + 1)
    }
    const r = rawLaps.rows[Math.floor(rawLaps.rows.length / 2)]
    expect(series[r[col.driver]][r[col.lap]]).toBe(r[col.position])
  })

  it('gap series matches replay.json and flips sign with the reference', () => {
    const clock = buildRaceClock(race)
    const toLeader = gapSeries(clock)
    const lap = race.replay.laps[9]
    const row = lap.drivers[4]
    expect(toLeader[row.driver][lap.lap_number]).toBeCloseTo(parseFloat(row.gap.replace('+', '')), 2)
    const a = drivers[0].driver, b = drivers[1].driver
    expect(gapSeries(clock, a)[b][10]).toBeCloseTo(-gapSeries(clock, b)[a][10], 6)
  })

  it('race pace is ordered and uses only clean laps', () => {
    const pace = racePace(laps)
    expect(pace[0].delta).toBe(0)
    for (let i = 0; i < pace.length; i++) {
      const p = pace[i]
      if (i) expect(p.median).toBeGreaterThanOrEqual(pace[i - 1].median)
      expect(p.low).toBeLessThanOrEqual(p.q1)
      expect(p.q1).toBeLessThanOrEqual(p.median)
      expect(p.median).toBeLessThanOrEqual(p.q3)
      expect(p.q3).toBeLessThanOrEqual(p.high)
      const clean = rowsOf(p.driver).filter(r => r[col.lap] > 1 && r[col.lap_time_s] != null && r[col.track_status] === '1' && r[col.is_accurate] && !r[col.pit_in] && !r[col.pit_out])
      expect(p.n, p.driver).toBe(clean.length)
    }
  })

  it('pit table has one row per stop outside red flags, with the loss from pit_loss.json', () => {
    const table = pitTable(stops, race.pitLoss)
    // every stop is a lap flagged pit_in or followed by a pit_out lap, never invented
    for (const st of stops) {
      const rows = rowsOf(st.driver)
      const inLap = rows.find(r => r[col.lap] === st.lap), outLap = rows.find(r => r[col.lap] === st.lap + 1)
      expect(inLap[col.pit_in] || outLap[col.pit_out], `${st.driver} lap ${st.lap}`).toBe(true)
    }
    expect(stops.length).toBeGreaterThan(0)
    for (const s of race.pitLoss.stops) {
      const row = table.find(t => t.driver === s.driver && t.lap === s.lap)
      if (!row) { expect(lapStatus(bands, s.lap) === 'red' || lapStatus(bands, s.lap + 1) === 'red').toBe(true); continue }
      expect(row.loss).toBe(s.loss_s)
    }
  })
})

describe('debrief edge cases', () => {
  it('knows a wet race from a dry one', () => {
    expect(hadWetRunning(loadRace(2026, 20).laps)).toBe(true)
    expect(hadWetRunning(loadRace(2025, 3).laps)).toBe(false)
  })

  it('copes with a race that has no clean pit stop and no results', () => {
    const race = loadRace(2024, 21)   // median_loss_s is null
    const bands = statusBands(race.trackStatus, race.laps.totalLaps)
    const stops = pitStops(race.laps, race.pitLoss, bands)
    expect(race.pitLoss.median_loss_s).toBeNull()
    expect(pitTable(stops, race.pitLoss).every(r => r.condition !== 'green' || r.vsMedian === null)).toBe(true)
    const h = headlines({ laps: race.laps, results: null, bands, stops })
    expect(h.winner).toBeNull()
    expect(h.climber).toBeNull()
    expect(h.redFlags).toBe(1)
    expect(driverList(race.laps, null).length).toBe(Object.keys(race.laps.drivers).length)
  })
})
