// strategySim against real races (identity, optimiser, reproducibility) and against a
// synthetic race where the right answer is known by construction.
import { describe, expect, it } from 'vitest'
import { buildRaceClock } from '../raceClock'
import { parseLaps } from '../laps'
import {
  buildSimRace, actualStints, makeStints, parseStrategy, formatStrategy, checkStrategy,
  simulate, bestStrategies, bestGains, modelTime, makeRandom,
} from '../strategySim'
import { tyreEffect, notSimulable, lowestConfidence } from '../tyreModel'
import { loadRace } from './helpers'

function simRace(year, round) {
  const race = loadRace(year, round)
  const clock = buildRaceClock(race)
  return { raw: race, clock, sim: buildSimRace({ laps: race.laps, clock, model: race.tyreModel, pitLoss: race.pitLoss, results: race.results }) }
}

// ── a synthetic race with known tyres ─────────────────────────────────────────

const COLS = ['driver', 'team', 'lap', 'lap_time_s', 'sector1_s', 'sector2_s', 'sector3_s', 'compound', 'tyre_life', 'stint',
  'fresh_tyre', 'pit_in', 'pit_out', 'position', 'track_status', 'is_accurate', 'deleted', 'pit_stop']
const PIT_LOSS = 20

function compound(offset, deg, extra = {}) {
  return { offset_s: offset, offset_se: 0.05, deg_s_per_lap: deg, quad_s_per_lap2: 0, avg_deg_s_per_lap: deg, deg_se: 0.005,
    laps: 400, drivers: 10, max_life_seen: 40, residual_sd_s: 0.3, confidence: 'high', confidence_reason: 'synthetic', ...extra }
}

// plans: { CODE: { base, stints: [[compound, last lap], ...] } }; lap = base + fuel*n + tyre (+ pit loss)
function synthetic(plans, { total = 50, deg = { MEDIUM: 0.08, HARD: 0.04 }, offset = { MEDIUM: 0, HARD: 0.4 }, sc = [] } = {}) {
  const fuel = -0.03
  const model = {
    modelled: true, wet_running: false, wet_share: 0, fuel_s_per_lap: fuel,
    compounds: Object.fromEntries(Object.keys(deg).map(c => [c, compound(offset[c], deg[c])])),
    drivers: Object.fromEntries(Object.entries(plans).map(([code, p]) => [code, p.base])),
  }
  const rows = [], cum = {}, stops = []
  const codes = Object.keys(plans)
  for (let n = 1; n <= total; n++) {
    const lapRows = []
    for (const code of codes) {
      const p = plans[code]
      const i = p.stints.findIndex(s => n <= s[1])
      const start = i ? p.stints[i - 1][1] + 1 : 1
      const [c, end] = p.stints[i]
      const life = n - start + 1
      const pitIn = n === end && end !== total, pitOut = n === start && i > 0
      let time = p.base + fuel * n + offset[c] + deg[c] * life
      if (sc.includes(n)) time = 130
      if (pitIn) time += PIT_LOSS * 0.3
      if (pitOut) time += PIT_LOSS * 0.7
      if (pitIn) stops.push({ driver: code, lap: n, in_lap_s: 96, out_lap_s: 104, ref_lap_s: 90, loss_s: PIT_LOSS, condition: sc.includes(n) ? 'sc' : 'green' })
      cum[code] = (cum[code] || 0) + time
      lapRows.push({ code, row: [code, 'T', n, +time.toFixed(6), 1, 1, 1, c, life, i + 1, true, pitIn, pitOut, 0, sc.includes(n) ? '4' : '1', true, false, pitIn], t: cum[code] })
    }
    lapRows.sort((a, b) => a.t - b.t).forEach((r, k) => { r.row[13] = k + 1; rows.push(r.row) })
  }
  const laps = parseLaps({ columns: COLS, rows })
  const order = codes.slice().sort((a, b) => cum[a] - cum[b])
  const results = order.map((code, i) => ({ driver: code, position: i + 1, classified_position: String(i + 1), status: 'Finished', grid_position: i + 1, laps: total, team_color: '#888888' }))
  // replay.json: gaps to the leader at every lap end
  const replay = { total_laps: total, laps: [] }
  const run = {}
  for (let n = 1; n <= total; n++) {
    const at = codes.map(code => { run[code] = (run[code] || 0) + laps.drivers[code].time[n]; return { driver: code, t: run[code] } }).sort((a, b) => a.t - b.t)
    replay.laps.push({ lap_number: n, drivers: at.map((d, i) => ({ driver: d.driver, gap: i ? `+${(d.t - at[0].t).toFixed(6)}s` : 'LEADER' })) })
  }
  const pitLoss = { median_loss_s: PIT_LOSS, median_loss_sc_s: 8, median_loss_vsc_s: null, green_stops: stops.length, stops }
  const clock = buildRaceClock({ laps, replay, results, pitLoss })
  return { sim: buildSimRace({ laps, clock, model, pitLoss, results }), clock, model }
}

const FIELD = {
  AAA: { base: 90.0, stints: [['MEDIUM', 20], ['HARD', 50]] },
  BBB: { base: 90.2, stints: [['MEDIUM', 24], ['HARD', 50]] },
  CCC: { base: 90.4, stints: [['HARD', 28], ['MEDIUM', 50]] },
  DDD: { base: 90.6, stints: [['MEDIUM', 15], ['HARD', 33], ['MEDIUM', 50]] },
}

// ── identity ──────────────────────────────────────────────────────────────────

describe.each([[2024, 1], [2025, 14], [2026, 3], [2026, 19], [2025, 8]])('identity %i/%i', (year, round) => {
  const { sim, raw } = simRace(year, round)

  it('the real strategy gives the real race time and finishing position', () => {
    let checked = 0
    for (const code of sim.order) {
      const car = sim.cars[code]
      if (car.laps < 2) continue
      const r = simulate(sim, code, actualStints(sim, code))
      expect(Math.abs(r.gap[car.laps]), `${code} race time`).toBeLessThan(0.01)
      expect(Math.max(...Array.from(r.gap, Math.abs)), `${code} every lap`).toBeLessThan(0.01)
      expect(r.isActual).toBe(true)
      expect(r.time.p10).toBeCloseTo(0, 6)
      expect(r.time.p90).toBeCloseTo(0, 6)
      if (!car.retired) {
        const classified = raw.results.find(x => x.driver === code).position
        expect(r.finish.alt, `${code} finish`).toBe(classified)
        expect(r.finish.real).toBe(classified)
        expect(r.finish.shares).toEqual({ [classified]: 1 })
      }
      expect(r.position.alt).toEqual(r.position.real)
      expect(r.stops.alt).toEqual(r.stops.real)
      expect(r.traffic.laps).toBe(r.traffic.realLaps)
      checked++
    }
    expect(checked).toBeGreaterThanOrEqual(15)
  })

  it('the strategy text round-trips', () => {
    for (const code of sim.order.slice(0, 10)) {
      const stints = actualStints(sim, code)
      if (stints.some(s => !['SOFT', 'MEDIUM', 'HARD'].includes(s.compound))) continue
      const parsed = parseStrategy(formatStrategy(stints))
      expect(makeStints(sim, code, parsed.compounds, parsed.stops)).toEqual(stints)
    }
  })
})

// ── synthetic: the right answers are known ────────────────────────────────────

describe('synthetic race', () => {
  const { sim } = synthetic(FIELD)

  it('identity holds and the fast time equals the lap-by-lap time', () => {
    for (const code of Object.keys(FIELD)) {
      const stints = actualStints(sim, code)
      expect(Math.abs(simulate(sim, code, stints).gap[50])).toBeLessThan(1e-6)
      const moved = makeStints(sim, code, stints.map(s => s.compound), stints.slice(0, -1).map(s => s.end + 3))
      const r = simulate(sim, code, moved, { runs: 0 })
      expect(modelTime(sim, code, moved)).toBeCloseTo(sim.cars[code].times[50] + r.gap[50], 6)
    }
  })

  it('moving a stop one lap changes the time by the difference of the two tyres on that lap', () => {
    // AAA really pitted on lap 20 (mediums then hards). One lap later: lap 21 is on
    // 21-lap-old mediums instead of new hards, and every later lap is on hards one lap younger.
    const later = simulate(sim, 'AAA', makeStints(sim, 'AAA', ['MEDIUM', 'HARD'], [21]), { runs: 0 })
    const expected = (0 + 0.08 * 21) - (0.4 + 0.04 * 1) - 0.04 * 29
    expect(later.gap[50]).toBeCloseTo(expected, 6)
    expect(later.gap[50]).toBeGreaterThan(-2)
    expect(later.gap[50]).toBeLessThan(2)                 // a plausible size: a fraction of a second per lap moved
    const earlier = simulate(sim, 'AAA', makeStints(sim, 'AAA', ['MEDIUM', 'HARD'], [19]), { runs: 0 })
    expect(earlier.gap[50]).toBeCloseTo((0.4 + 0.04 * 1) - (0.08 * 20) + 0.04 * 30, 6)
    expect(later.stops).toEqual({ real: [20], alt: [21] })
    // The sign follows the deg rates. BBB stayed out to lap 24 on mediums that wear twice
    // as fast as the hards: a lap earlier gains, a lap later loses.
    const sooner = simulate(sim, 'BBB', makeStints(sim, 'BBB', ['MEDIUM', 'HARD'], [23]), { runs: 0 })
    const longer = simulate(sim, 'BBB', makeStints(sim, 'BBB', ['MEDIUM', 'HARD'], [25]), { runs: 0 })
    expect(sooner.gap[50]).toBeCloseTo((0.4 + 0.04) - 0.08 * 24 + 0.04 * 26, 6)      // -0.44 s
    expect(sooner.gap[50]).toBeLessThan(0)
    expect(longer.gap[50]).toBeGreaterThan(0)
    // with the rates the other way round (hards wearing faster) the sign flips
    const flipped = synthetic(FIELD, { deg: { MEDIUM: 0.02, HARD: 0.09 } }).sim
    expect(simulate(flipped, 'BBB', makeStints(flipped, 'BBB', ['MEDIUM', 'HARD'], [25]), { runs: 0 }).gap[50]).toBeLessThan(0)
  })

  it('an extra stop costs one pit loss when the tyres do not wear', () => {
    const flat = synthetic(FIELD, { deg: { MEDIUM: 0, HARD: 0 }, offset: { MEDIUM: 0, HARD: 0 } }).sim
    const two = simulate(flat, 'AAA', makeStints(flat, 'AAA', ['MEDIUM', 'HARD', 'MEDIUM'], [20, 35]), { runs: 0 })
    expect(two.gap[50]).toBeCloseTo(PIT_LOSS, 6)
    expect(two.pit.map(c => [c.lap, c.inherited, Math.round(c.loss)])).toEqual([[20, true, 20], [35, false, 20]])
    // and one stop fewer saves one (DDD really stopped twice)
    const one = simulate(flat, 'DDD', makeStints(flat, 'DDD', ['MEDIUM', 'HARD'], [15]), { runs: 0 })
    expect(one.gap[50]).toBeCloseTo(-PIT_LOSS, 6)
  })

  it('positions follow the time against the ghost field', () => {
    // DDD without the second stop gains 20 s of pit loss minus old-tyre time
    const r = simulate(sim, 'DDD', makeStints(sim, 'DDD', ['MEDIUM', 'HARD'], [15]), { runs: 0 })
    expect(r.finish.real).toBe(4)
    expect(r.gap[50]).toBeLessThan(0)
    for (let n = 1; n <= 50; n++) {
      const ahead = Object.values(sim.cars).filter(o => o.driver !== 'DDD' && o.times[n] < sim.cars.DDD.times[n] + r.gap[n]).length
      expect(r.position.alt[n]).toBe(ahead + 1)
    }
    expect(r.finish.alt).toBe(r.position.alt[50])
  })

  it('Safety Car laps keep their real time and a stop under it uses the Safety Car loss', () => {
    const { sim: s } = synthetic(FIELD, { sc: [30, 31, 32] })
    const r = simulate(s, 'AAA', makeStints(s, 'AAA', ['MEDIUM', 'HARD', 'MEDIUM'], [20, 30]), { runs: 0 })
    expect(r.pit[1]).toMatchObject({ lap: 30, cond: 'sc', inherited: false, loss: 8 })
    for (const n of [30, 31, 32]) expect(r.lapTime.alt[n] - r.lapTime.real[n]).toBeCloseTo(n === 30 ? 8 * 0.3 : n === 31 ? 8 * 0.7 : 0, 6)
    // the same stop two laps after the restart costs the full green loss
    const green = simulate(s, 'AAA', makeStints(s, 'AAA', ['MEDIUM', 'HARD', 'MEDIUM'], [20, 34]), { runs: 0 })
    expect(green.pit[1]).toMatchObject({ cond: 'green', loss: PIT_LOSS })
  })

  it('a strategy that leaves the real one before a Safety Car is flagged and low confidence', () => {
    const { sim: s } = synthetic(FIELD, { sc: [30, 31, 32] })
    // AAA really stopped on lap 20, ten laps before the Safety Car
    const before = simulate(s, 'AAA', makeStints(s, 'AAA', ['MEDIUM', 'HARD'], [17]), { runs: 50 })
    expect(before.flags.map(f => f.code)).toEqual(['neutralised'])
    expect(before.flags[0].text).toMatch(/Safety Car \(to lap 32\).*leaves the real one on lap 17/)
    expect(before.confidence.level).toBe('low')
    expect(before.valid).toBe(true)
    // DDD's second stop (lap 33) is after it: moving that one is not affected
    const after = simulate(s, 'DDD', makeStints(s, 'DDD', ['MEDIUM', 'HARD', 'MEDIUM'], [15, 36]), { runs: 50 })
    expect(after.flags).toEqual([])
    expect(after.confidence.level).toBe('high')
    // no Safety Car, no flag
    expect(simulate(sim, 'AAA', makeStints(sim, 'AAA', ['MEDIUM', 'HARD'], [17]), { runs: 0 }).flags).toEqual([])
  })

  it('a real stop under the Safety Car is credited no more than a stop there is charged', () => {
    // EEE pits under the Safety Car and (as in a real queue) loses far more time on paper
    const field = { ...FIELD, EEE: { base: 90.8, stints: [['MEDIUM', 30], ['HARD', 50]] } }
    const { sim: s } = synthetic(field, { sc: [30, 31, 32] })
    const moved = simulate(s, 'EEE', makeStints(s, 'EEE', ['MEDIUM', 'HARD'], [31]), { runs: 0 })
    // out of lap 30 and into lap 31 of the same Safety Car period: the stop costs the same
    expect(moved.pit[0]).toMatchObject({ lap: 31, cond: 'sc', loss: 8 })
    expect(Math.abs(moved.gap[50])).toBeLessThan(1)
    // made under green instead it costs the green loss, less the 8 s credited
    const green = simulate(s, 'EEE', makeStints(s, 'EEE', ['MEDIUM', 'HARD'], [26]), { runs: 0 })
    expect(green.gap[50]).toBeGreaterThan(PIT_LOSS - 8 - 4)
    expect(green.gap[50]).toBeLessThan(PIT_LOSS - 8 + 4)
  })

  it('reports traffic without charging for it', () => {
    // AAA stops a lap later and rejoins among the cars it had cleared
    const r = simulate(sim, 'AAA', makeStints(sim, 'AAA', ['MEDIUM', 'HARD'], [26]), { runs: 0 })
    expect(r.traffic.rejoins).toHaveLength(1)
    expect(r.traffic.rejoins[0].lap).toBe(26)
    for (const c of r.traffic.rejoins[0].cars) { expect(c.gap).toBeGreaterThan(0); expect(c.gap).toBeLessThanOrEqual(1.5) }
    expect(r.traffic.laps).toBe(r.traffic.cars.reduce((n, c) => n + c.laps, 0))
    // no penalty: the time is exactly the tyre and pit arithmetic
    expect(modelTime(sim, 'AAA', r.stints)).toBeCloseTo(sim.cars.AAA.times[50] + r.gap[50], 6)
  })
})

// ── rules ─────────────────────────────────────────────────────────────────────

describe('rules and warnings', () => {
  const { sim } = synthetic(FIELD)
  const codes = (compounds, stops) => checkStrategy(sim, 'AAA', makeStints(sim, 'AAA', compounds, stops)).map(f => f.code)

  it('flags instead of throwing', () => {
    expect(codes(['MEDIUM', 'HARD'], [20])).toEqual([])                       // what happened
    expect(codes(['MEDIUM', 'MEDIUM'], [25])).toEqual(['one_compound'])
    expect(codes(['MEDIUM', 'HARD'], [2])).toContain('stop_too_early')
    expect(codes(['MEDIUM', 'HARD'], [49])).toContain('stop_too_late')
    expect(codes(['MEDIUM', 'HARD'], [3])).toEqual(['extrapolation'])         // 47 laps on hards, 40 seen
    expect(codes(['MEDIUM', 'SOFT'], [25])).toContain('compound_unavailable') // nobody ran softs
    expect(codes(['MEDIUM', 'HARD', 'MEDIUM'], [30, 20])).toEqual(['bad_order'])
  })

  it('an extrapolated stint or a broken rule forces low confidence', () => {
    const long = simulate(sim, 'AAA', makeStints(sim, 'AAA', ['MEDIUM', 'HARD'], [5]), { runs: 50 })
    expect(long.valid).toBe(true)
    expect(long.confidence.level).toBe('low')
    expect(long.confidence.reason).toMatch(/nobody ran them past 40 laps/)
    const bad = simulate(sim, 'AAA', makeStints(sim, 'AAA', ['MEDIUM', 'MEDIUM'], [25]), { runs: 50 })
    expect(bad.valid).toBe(false)
    expect(bad.confidence.level).toBe('low')
    expect(simulate(sim, 'AAA', makeStints(sim, 'AAA', ['MEDIUM', 'HARD'], [22]), { runs: 50 }).confidence.level).toBe('high')
  })

  it('parses and rejects strategy text', () => {
    expect(parseStrategy('M-18-H-41-S')).toEqual({ compounds: ['MEDIUM', 'HARD', 'SOFT'], stops: [18, 41] })
    expect(parseStrategy('h')).toEqual({ compounds: ['HARD'], stops: [] })
    for (const bad of ['', 'M-18', 'X-18-H', 'M-H', 'M-1e3-H', null]) expect(parseStrategy(bad)).toBeNull()
  })
})

// ── uncertainty ───────────────────────────────────────────────────────────────

describe('Monte Carlo', () => {
  const { sim } = simRace(2026, 3)
  const code = sim.order[3]
  const real = actualStints(sim, code)
  const alt = makeStints(sim, code, real.map(s => s.compound), real.slice(0, -1).map(s => s.end - 4))

  it('is reproducible for a seed and different for another', () => {
    const a = simulate(sim, code, alt, { seed: 7 }), b = simulate(sim, code, alt, { seed: 7 }), c = simulate(sim, code, alt, { seed: 8 })
    expect(a.time).toEqual(b.time)
    expect(a.finish).toEqual(b.finish)
    expect(Array.from(a.band.p10)).toEqual(Array.from(b.band.p10))
    expect(c.time.p10).not.toBe(a.time.p10)
    expect(Math.abs(c.time.p50 - a.time.p50)).toBeLessThan(1)          // but the same answer
  })

  it('gives a range around the model value and position shares that add up', () => {
    const r = simulate(sim, code, alt, { seed: 3 })
    expect(r.time.p10).toBeLessThan(r.time.p50)
    expect(r.time.p50).toBeLessThan(r.time.p90)
    expect(Math.abs(r.time.p50 - r.time.delta)).toBeLessThan(1.5)
    expect(r.time.p90 - r.time.p10).toBeGreaterThan(1)
    // the range is at least as wide as the model's measured error on an unseen stint
    expect(r.time.p90 - r.time.p10).toBeGreaterThan(sim.model.stintSd * Math.min(1, real[0].end / 20))
    expect(r.time.p90 - r.time.p10).toBeLessThan(40)
    expect(Object.values(r.finish.shares).reduce((a, b) => a + b, 0)).toBeCloseTo(1, 9)
    expect(r.finish.p10).toBeLessThanOrEqual(r.finish.alt)
    expect(r.finish.alt).toBeLessThanOrEqual(r.finish.p90)
    for (let n = 1; n <= r.laps; n++) expect(r.band.p10[n]).toBeLessThanOrEqual(r.band.p90[n])
    // nothing changes before the first moved stop
    expect(r.band.p90[alt[0].end - 1]).toBeCloseTo(0, 6)
  })

  it('the generator is deterministic and roughly normal', () => {
    const a = makeRandom(42), b = makeRandom(42)
    const xs = Array.from({ length: 4000 }, () => a.normal())
    expect(xs.slice(0, 5)).toEqual(Array.from({ length: 5 }, () => b.normal()))
    const mean = xs.reduce((s, x) => s + x, 0) / xs.length
    const sd = Math.sqrt(xs.reduce((s, x) => s + (x - mean) ** 2, 0) / xs.length)
    expect(Math.abs(mean)).toBeLessThan(0.06)
    expect(Math.abs(sd - 1)).toBeLessThan(0.06)
  })
})

// ── optimiser ─────────────────────────────────────────────────────────────────

describe('optimiser', () => {
  it('finds the known best on the synthetic race', () => {
    const { sim } = synthetic(FIELD)
    const best = bestStrategies(sim, 'CCC', { runs: 100 })
    expect(best.length).toBe(5)
    // brute force over every one-stop with the same rules
    let fastest = Infinity
    for (const [a, b] of [['MEDIUM', 'HARD'], ['HARD', 'MEDIUM']]) {
      for (let p = 3; p <= 48; p++) {
        const st = makeStints(sim, 'CCC', [a, b], [p])
        if (checkStrategy(sim, 'CCC', st).length) continue
        fastest = Math.min(fastest, simulate(sim, 'CCC', st, { runs: 0 }).gap[50])
      }
    }
    expect(Math.min(...best.map(b => b.time.delta))).toBeLessThanOrEqual(fastest + 1e-6)
    for (const b of best) expect(checkStrategy(sim, 'CCC', b.stints).filter(f => f.level === 'error')).toEqual([])
  })

  it.each([[2024, 1], [2026, 3], [2026, 19]])('%i/%i: the best is never slower than what happened, and stays within the rules', (year, round) => {
    const { sim } = simRace(year, round)
    for (const code of sim.order.slice(0, 6)) {
      const best = bestStrategies(sim, code, { seed: 1 })
      expect(best.length).toBeGreaterThan(0)
      const noise = Math.max(...best.map(b => b.time.p90 - b.time.p10), 0.5)
      expect(best[0].time.p50, code).toBeLessThanOrEqual(noise)
      expect(Math.min(...best.map(b => b.time.delta)), code).toBeLessThanOrEqual(1e-6)
      for (const b of best) {
        expect(checkStrategy(sim, code, b.stints).filter(f => f.level === 'error' || f.code === 'extrapolation' && !b.isActual), `${code} ${b.strategy}`).toEqual([])
        expect(b.finish.p10).toBeLessThanOrEqual(b.finish.p90)
      }
    }
    const gains = bestGains(sim, sim.order.slice(0, 10))
    for (const g of Object.values(gains)) expect(g.delta).toBeLessThanOrEqual(0)
  })

  it('can be limited to one-stop or two-stop strategies', () => {
    const { sim } = synthetic(FIELD)
    const one = bestStrategies(sim, 'DDD', { stops: 1, top: 3, runs: 0 })
    const two = bestStrategies(sim, 'DDD', { stops: 2, top: 3, runs: 0 })
    expect(one.length).toBe(3)
    expect(one.every(b => b.stints.length === 2 && !b.isActual)).toBe(true)
    expect(two.every(b => b.stints.length === 3)).toBe(true)
    expect(one[0].time.delta).toBeLessThan(two[0].time.delta)       // 20 s of pit loss buys little on these tyres
  })

  it('searches a 78 lap race quickly', () => {
    const { sim } = simRace(2025, 8)                       // Monaco, 78 laps
    const code = sim.order[0]
    bestStrategies(sim, code)                              // warm up
    const t = performance.now()
    const best = bestStrategies(sim, code)
    const ms = performance.now() - t
    expect(best.searched).toBeGreaterThan(1000)
    expect(ms).toBeLessThan(300)
  })
})

// ── tyre model helpers ────────────────────────────────────────────────────────

describe('tyreModel', () => {
  it('evaluates the fit and extends a curve in a straight line past the oldest tyre seen', () => {
    const lin = compound(0.4, 0.05)
    expect(tyreEffect(lin, 10)).toBeCloseTo(0.9, 9)
    expect(tyreEffect(lin, 60)).toBeCloseTo(3.4, 9)
    const curve = compound(0, 0.02, { quad_s_per_lap2: 0.002, max_life_seen: 20 })
    expect(tyreEffect(curve, 20)).toBeCloseTo(0.4 + 0.8, 9)
    expect(tyreEffect(curve, 25)).toBeCloseTo(1.2 + 5 * (0.02 + 2 * 0.002 * 20), 9)
    expect(tyreEffect(curve, 21) - tyreEffect(curve, 20)).toBeCloseTo(0.1, 9)
  })

  it('refuses wet and unmodelled races', () => {
    expect(notSimulable(null)).toMatch(/No tyre model/)
    expect(notSimulable(loadRace(2024, 21).tyreModel)).toMatch(/wet/)
    expect(notSimulable(loadRace(2024, 9).tyreModel)).toMatch(/Intermediate or wet tyres were used on 67%/)
    expect(notSimulable(loadRace(2026, 3).tyreModel)).toBeNull()
    expect(lowestConfidence(['high', 'low', 'medium'])).toBe('low')
    expect(lowestConfidence([])).toBe('high')
  })
})
