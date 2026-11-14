import { describe, expect, it } from 'vitest'
import { buildRaceClock } from '../raceClock'
import { loadRace } from './helpers'

// A normal race (no Safety Car, nobody retired), a race with a VSC, two Safety Cars,
// a red flag and five retirements, and a FastF1-built wet race with a red flag.
const RACES = [
  [2025, 3,  'Japan 2025: green all the way'],
  [2026, 19, 'Mexico City 2026: SC, VSC, red flag, retirements (OpenF1)'],
  [2024, 21, 'Sao Paulo 2024: wet, red flag, retirements (FastF1)'],
]

describe.each(RACES)('raceClock %i/%i (%s)', (year, round) => {
  const race = loadRace(year, round)
  const clock = buildRaceClock(race)
  const col = Object.fromEntries(race.rawLaps.columns.map((c, i) => [c, i]))

  it('has every driver that has laps', () => {
    const codes = new Set(race.rawLaps.rows.map(r => r[col.driver]))
    expect(clock.drivers.map(d => d.driver).sort()).toEqual([...codes].sort())
    expect(clock.totalLaps).toBe(race.replay.total_laps)
  })

  it('cumulative time is strictly increasing for every driver, and for the spine', () => {
    for (const d of clock.drivers) {
      for (let n = 1; n <= d.done; n++) expect(d.times[n], `${d.driver} lap ${n}`).toBeGreaterThan(d.times[n - 1])
    }
    for (let n = 1; n <= clock.totalLaps; n++) expect(clock.spine[n]).toBeGreaterThan(clock.spine[n - 1])
  })

  it('positions at every lap end equal the positions in laps.json', () => {
    let checked = 0
    for (const r of race.rawLaps.rows) {
      const d = clock.byCode[r[col.driver]], lap = r[col.lap], position = r[col.position]
      if (position == null || lap > d.done) continue      // the lap a retired car never finished
      const car = clock.stateAt(d.times[lap]).find(c => c.driver === d.driver)
      expect(car.position, `${d.driver} at the end of lap ${lap}`).toBe(position)
      checked++
    }
    expect(checked).toBeGreaterThan(race.rawLaps.rows.length * 0.95)
  })

  it('no car is more than a lap away from where its gap says it should be', () => {
    for (const lap of race.replay.laps) {
      const n = lap.lap_number
      for (const row of lap.drivers.slice(1)) {
        const gap = parseFloat(String(row.gap).replace('+', ''))
        const d = clock.byCode[row.driver]
        if (!Number.isFinite(gap) || n > d.done) continue
        // seconds: the clock's own gap at that instant against the data
        const t = d.times[n]
        const car = clock.stateAt(t).find(c => c.driver === d.driver)
        if (car.retired) continue                            // stopped on this line: no gap any more
        const leaderLap = clock.spine[n] - clock.spine[n - 1]
        expect(Math.abs(car.gap - gap), `${d.driver} lap ${n} gap`).toBeLessThan(leaderLap)
        // distance: laps behind the leader on track against where the gap puts the car
        const actualBehind = clock.playheadAt(t) - n
        const expectedBehind = clock.playheadAt(clock.spine[n] + gap) - n
        expect(Math.abs(actualBehind - expectedBehind), `${d.driver} lap ${n} distance`).toBeLessThan(1)
      }
    }
  })

  it('playhead and race time convert both ways', () => {
    for (const p of [0, 0.5, 1, 7.25, clock.totalLaps - 0.01, clock.totalLaps]) {
      expect(clock.playheadAt(clock.timeAt(p))).toBeCloseTo(p, 6)
    }
  })

  it('fractions stay in 0..1 and positions are 1..N at any time', () => {
    for (let p = 0; p <= clock.totalLaps; p += 0.37) {
      const cars = clock.stateAt(clock.timeAt(p))
      expect(cars.map(c => c.position)).toEqual(cars.map((_, i) => i + 1))
      for (const c of cars) {
        expect(c.fraction).toBeGreaterThanOrEqual(0)
        expect(c.fraction).toBeLessThanOrEqual(1)
      }
    }
  })

  // Not the classification order: time penalties reorder that after the flag
  it('ends with the running cars finished and the rest retired', () => {
    const final = clock.stateAt(clock.duration + 36000)
    const classified = r => !/retired|not start/i.test(r.status)
    const finishers = race.results.filter(r => classified(r) && clock.byCode[r.driver]).map(r => r.driver)
    expect(final.filter(c => c.finished).map(c => c.driver).sort()).toEqual(finishers.sort())
    const retired = race.results.filter(r => !classified(r) && clock.byCode[r.driver]).map(r => r.driver)
    expect(final.filter(c => c.retired).map(c => c.driver).sort()).toEqual(retired.sort())
  })
})

describe('raceClock pit stops', () => {
  const race = loadRace(2025, 3)
  const clock = buildRaceClock(race)
  it('holds a car in the pit lane at the start of its out-lap', () => {
    const d = clock.drivers.find(x => x.hold.some(h => h > 0))
    const lap = d.hold.findIndex(h => h > 0)
    const during = clock.stateAt(d.times[lap - 1] + d.hold[lap] / 2).find(c => c.driver === d.driver)
    expect(during.inPit).toBe(true)
    expect(during.fraction).toBe(0)
    const after = clock.stateAt(d.times[lap - 1] + d.hold[lap] + 5).find(c => c.driver === d.driver)
    expect(after.inPit).toBe(false)
    expect(after.fraction).toBeGreaterThan(0)
  })
})
