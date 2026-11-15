// The invariants that must hold for every race in the library, not just the three in
// raceClock.test.js: the order at every lap end is exactly the order in laps.json (no
// exceptions: the pipeline's validation gate refuses a race that repeats a position),
// and race time only moves forward for every driver.
import { describe, expect, it } from 'vitest'
import { buildRaceClock } from '../raceClock'
import { loadRace, manifest } from './helpers'

const RACES = manifest().events.filter(e => e.sessions.includes('R')).map(e => [e.year, e.round, e.name])

describe.each(RACES)('raceClock %i/%i (%s)', (year, round) => {
  const race = loadRace(year, round)
  const clock = buildRaceClock(race)
  const col = Object.fromEntries(race.rawLaps.columns.map((c, i) => [c, i]))

  // lap -> [{ driver, position }] for rows the clock counts as completed laps
  const byLap = new Map()
  for (const r of race.rawLaps.rows) {
    const d = clock.byCode[r[col.driver]], lap = r[col.lap], position = r[col.position]
    if (position == null || lap > d.done) continue      // no position, or the lap a retired car never finished
    if (!byLap.has(lap)) byLap.set(lap, [])
    byLap.get(lap).push({ d, position })
  }

  it('laps.json never gives two drivers the same position on a lap', () => {
    for (const [lap, rows] of byLap) {
      expect(new Set(rows.map(r => r.position)).size, `lap ${lap}`).toBe(rows.length)
    }
  })

  it('positions at every lap end equal the positions in laps.json', () => {
    const wrong = []
    let checked = 0
    for (const [lap, rows] of byLap) {
      for (const { d, position } of rows) {
        const got = clock.stateAt(d.times[lap]).find(c => c.driver === d.driver).position
        if (got !== position) wrong.push(`${d.driver} lap ${lap}: laps.json P${position}, clock P${got}`)
        checked++
      }
    }
    expect(wrong).toEqual([])
    expect(checked).toBeGreaterThan(race.rawLaps.rows.length * 0.9)
  })

  it('cumulative time is strictly increasing for every driver', () => {
    for (const d of clock.drivers) {
      for (let n = 1; n <= d.done; n++) expect(d.times[n], `${d.driver} lap ${n}`).toBeGreaterThan(d.times[n - 1])
    }
  })
})
