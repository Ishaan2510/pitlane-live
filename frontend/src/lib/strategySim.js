// strategySim: what if one driver had run a different strategy?
//
// METHOD: change one driver, hold the field fixed.
// The chosen driver starts from the race they really drove. For every lap the only
// thing changed is the tyre they would have been on:
//
//   alt_lap = actual_lap - model(actual compound, actual tyre age) + model(alt compound, alt tyre age)
//
// with model() from tyre_model.json (lib/tyreModel.js). Everything the model does not
// know stays in: their real traffic, mistakes, fuel load, the weather.
// - Laps under Safety Car, VSC or red flag keep their real time whatever the tyres.
// - Real stops are taken out: the in-lap and out-lap are replaced by the driver's
//   modelled clean lap for the tyres they had (driver base + fuel x lap + tyre), or under
//   a neutralisation by the lap the cars that stayed out did.
// - New stops are put in: the pit loss from pit_loss.json, split over the in-lap and the
//   out-lap; the Safety Car or VSC figure when the stop falls in a real SC or VSC period
//   and that figure exists; nothing during a red flag (a free tyre change). A stop that
//   stays where it really was, or the driver's Nth green-flag stop moved to another
//   green-flag lap, keeps what that stop really cost (a slow stop stays slow).
// - Every other driver keeps their real race exactly: the "ghost field". The new
//   cumulative time is compared with theirs for a position at every lap and at the flag.
// So feeding a driver's real strategy back in gives their real race, to the millisecond.
//
// NOT MODELLED: overtaking and traffic. The result says who the driver would have
// rejoined behind and how many laps they would have sat behind a slower car, as a
// risk to read, not as lost time.
//
// SAFETY CARS AND RED FLAGS are where this method is weakest. A fixed field cannot
// close up behind a Safety Car, so seconds gained or lost before one are carried through
// it, when in the real race they would have been wiped out (places are kept, seconds are
// not). A real stop made under a neutralisation is therefore credited with no more than
// a stop there is charged (the Safety Car / VSC figure; nothing under a red flag), and a
// strategy that leaves the real one before the end of a Safety Car or red-flag period is
// flagged `neutralised` and is low confidence whatever the tyre model says.
//
// UNCERTAINTY: runs of Monte Carlo. Each run draws every compound's offset and deg rate
// from their standard errors, the loss of every new stop from the real stops of this
// race, per-lap noise from the model residual on each lap whose tyres changed, and, per
// changed stint, the model's own measured error on a stint it has not seen (the
// leave-one-driver-out stint error from tyre_model.json; without it the range would
// only reflect how well the fit is known, not how wrong it can be).
// The generator is seeded, so the same scenario always gives the same numbers.
//
// No UI code here. Everything takes the plain `race` object from buildSimRace(), which
// holds only data (typed arrays, numbers, strings), so it can be posted to a worker.

import { isPitStop } from './laps'
import { tyreEffect, lowestConfidence } from './tyreModel'

export const SIM_RUNS = 500
export const REJOIN_GAP_S = 1.5       // "rejoins within this far behind a car"
export const TRAFFIC_GAP_S = 1.0      // a lap within this far behind a slower car counts as traffic
const DEFAULT_PIT_LOSS_S = 22
const PIT_NOISE_S = 1.5               // spread of a stop when the race has too few to sample
const MIN_SAMPLES = 3
const STINT_ERROR_LAPS = 20           // the leave-one-driver-out stint error is for a stint of about this length
const DRY = ['SOFT', 'MEDIUM', 'HARD']
const LETTER = { S: 'SOFT', M: 'MEDIUM', H: 'HARD' }

// ── seeded random numbers ─────────────────────────────────────────────────────

export function makeRandom(seed) {
  let a = (seed >>> 0) || 1
  const uniform = () => {
    a = (a + 0x6D2B79F5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
  let spare = null
  const normal = () => {
    if (spare !== null) { const v = spare; spare = null; return v }
    let u = 0
    while (u === 0) u = uniform()
    const r = Math.sqrt(-2 * Math.log(u)), th = 2 * Math.PI * uniform()
    spare = r * Math.sin(th)
    return r * Math.cos(th)
  }
  return { uniform, normal }
}

// Value at share q (0..1) of an ascending array
function quantileSorted(sorted, q) {
  const i = (sorted.length - 1) * q, lo = Math.floor(i), hi = Math.ceil(i)
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (i - lo)
}

function median(values) {
  if (!values.length) return NaN
  const s = values.slice().sort((a, b) => a - b)
  return quantileSorted(s, 0.5)
}

// ── the race as plain data ────────────────────────────────────────────────────

/**
 * @param laps     parseLaps(laps.json)
 * @param clock    buildRaceClock(): its lap-end times are "the real race"
 * @param model    tyre_model.json (modelled: true)
 * @param pitLoss  pit_loss.json, may be null
 * @param results  results.json, may be null
 */
export function buildSimRace({ laps, clock, model, pitLoss = null, results = null }) {
  const resultOf = Object.fromEntries((results || []).map(r => [r.driver, r]))
  const cars = {}
  for (const d of clock.drivers) {
    const L = d.data, done = d.done
    const res = resultOf[d.driver]
    const stops = []
    for (let n = 1; n < done; n++) if (isPitStop(L, n)) stops.push(n)
    cars[d.driver] = {
      driver: d.driver, team: d.team, color: d.color,
      laps: done,
      retired: d.retired || done < 1,
      finish: res && /^\d+$/.test(String(res.classified_position)) ? res.position : null,
      times: d.times.slice(0, done + 1),
      compound: Array.from({ length: done + 1 }, (_, n) => L.compound[n] || null),
      life: Array.from({ length: done + 1 }, (_, n) => L.tyreLife[n] || 0),
      status: Array.from({ length: done + 1 }, (_, n) => L.status[n] || ''),
      pos: Array.from({ length: done + 1 }, (_, n) => L.position[n] || 0),
      stops,
    }
  }

  // The lap the cars that did not pit drove, per lap number (for neutralised pit laps)
  const totalLaps = clock.totalLaps
  const fieldLap = new Float64Array(totalLaps + 1)
  for (let n = 1; n <= totalLaps; n++) {
    const durs = []
    for (const c of Object.values(cars)) {
      if (c.laps >= n && !c.stops.includes(n) && !c.stops.includes(n - 1)) durs.push(c.times[n] - c.times[n - 1])
    }
    fieldLap[n] = median(durs)
  }

  // Every line crossing of every car, in time order (for "who is just ahead on track")
  const crossings = []
  for (const c of Object.values(cars)) {
    for (let n = 1; n <= c.laps; n++) crossings.push({ t: c.times[n], driver: c.driver, dur: c.times[n] - c.times[n - 1] })
  }
  crossings.sort((a, b) => a.t - b.t)

  const green = (pitLoss?.stops || []).filter(s => s.condition === 'green')
  const samples = cond => (pitLoss?.stops || []).filter(s => s.condition === cond).map(s => s.loss_s)
  const shares = green.filter(s => s.loss_s > 5).map(s => (s.in_lap_s - s.ref_lap_s) / s.loss_s)
  const fromRace = pitLoss?.median_loss_s > 0
  return {
    totalLaps,
    cars,
    order: Object.values(cars).sort((a, b) => (a.finish ?? 99) - (b.finish ?? 99) || b.laps - a.laps).map(c => c.driver),
    fieldLap,
    crossings,
    crossingTimes: Float64Array.from(crossings, c => c.t),
    compounds: DRY.filter(c => model.compounds[c]),
    model: {
      fuel: model.fuel_s_per_lap, compounds: model.compounds, base: model.drivers || {},
      // sd of the error on an unseen stint's total time (a mean absolute error is 0.8 sd)
      stintSd: 1.25 * (model.validation?.stint_mae_s || 0),
    },
    pit: {
      green: fromRace ? pitLoss.median_loss_s : DEFAULT_PIT_LOSS_S,
      source: fromRace ? 'race' : 'default',          // 'default': this race has no measured green stop
      greenStops: pitLoss?.green_stops || 0,
      sc: pitLoss?.median_loss_sc_s ?? null,
      vsc: pitLoss?.median_loss_vsc_s ?? null,
      inShare: shares.length >= MIN_SAMPLES ? Math.min(0.9, Math.max(0.1, median(shares))) : 0.3,
      samples: { green: samples('green'), sc: samples('sc'), vsc: samples('vsc') },
    },
  }
}

// 'green' | 'sc' | 'vsc' | 'red' for a stop at the end of lap p, from the track status
// the driver really had on that lap and the next (same rule as pipeline stop_condition;
// a stop only half under a neutralisation is charged as a green stop)
function conditionAt(car, p) {
  const a = car.status[p] || '', b = p + 1 <= car.laps ? car.status[p + 1] || '' : ''
  if (a.includes('5') || b.includes('5')) return 'red'
  if (a.includes('4') && b.includes('4')) return 'sc'
  if (!a.includes('4') && !b.includes('4') && /[67]/.test(a) && /[67]/.test(b)) return 'vsc'
  return 'green'
}

// Per-driver numbers every simulation of that driver reuses
const prepared = new WeakMap()
function prepare(race, code) {
  let byCode = prepared.get(race)
  if (!byCode) prepared.set(race, byCode = {})
  if (byCode[code]) return byCode[code]

  const car = race.cars[code], N = car.laps, T = car.times
  const comp = race.model.compounds, base = race.model.base[code]

  // The real stints, cut at the real stops: { compound, start, end, life0 }
  const stints = []
  let start = 1
  for (const p of [...car.stops, N]) {
    if (p < start) continue
    let compound = null
    for (let n = start; n <= p && !compound; n++) compound = car.compound[n]
    stints.push({ compound, start, end: p, life0: car.life[start] || 1 })
    start = p + 1
  }

  const actC = new Array(N + 1).fill(null), actLife = new Float64Array(N + 1)
  for (const s of stints) for (let n = s.start; n <= s.end; n++) { actC[n] = s.compound; actLife[n] = s.life0 + (n - s.start) }

  const neutral = new Uint8Array(N + 1), g = new Uint8Array(N + 1), mAct = new Float64Array(N + 1)
  for (let n = 1; n <= N; n++) {
    neutral[n] = /[4567]/.test(car.status[n]) ? 1 : 0
    if (!neutral[n] && comp[actC[n]]) { g[n] = 1; mAct[n] = tyreEffect(comp[actC[n]], actLife[n]) }
  }

  // The real race with the real stops taken out
  const clean = new Float64Array(N + 1), pitCost = new Float64Array(N + 1)
  for (let n = 1; n <= N; n++) {
    const dur = T[n] - T[n - 1]
    clean[n] = dur
    if (!car.stops.includes(n) && !car.stops.includes(n - 1)) continue
    let ref = race.fieldLap[n]
    if (g[n] && base != null) ref = base + race.model.fuel * n + mAct[n]
    if (!(ref > 0)) ref = dur
    clean[n] = Math.min(dur, ref)                  // a stop never made a lap quicker
    pitCost[n] = dur - clean[n]
  }
  const claimed = new Uint8Array(N + 2)
  const realStops = car.stops.map(p => {
    const cond = conditionAt(car, p)
    let inCost = claimed[p] ? 0 : pitCost[p], outCost = pitCost[p + 1]
    // Under a neutralisation the measured cost is mostly the car's place in the queue.
    // Credit no more than a stop there is charged, so taking it out and putting it back
    // elsewhere in the same period nets nothing. A red-flag tyre change is free.
    if (cond !== 'green') {
      const cap = cond === 'red' ? 0 : race.pit[cond] ?? race.pit.green
      const total = inCost + outCost
      if (total > cap) {
        const k = total > 0 ? cap / total : 0
        if (!claimed[p]) { clean[p] += inCost * (1 - k); inCost *= k }
        clean[p + 1] += outCost * (1 - k); outCost *= k
      }
    }
    claimed[p] = claimed[p + 1] = 1
    return { lap: p, cond, inCost, outCost }
  })
  // the last lap a Safety Car or red flag was out for this driver (0: never)
  let lastBunching = 0
  for (let n = 1; n <= N; n++) if (/[45]/.test(car.status[n])) lastBunching = n

  // Prefix sums over the laps the tyre model applies to: sum g, sum g*n, sum g*n^2
  const G0 = new Float64Array(N + 1), G1 = new Float64Array(N + 1), G2 = new Float64Array(N + 1)
  let K = 0
  for (let n = 1; n <= N; n++) {
    G0[n] = G0[n - 1] + g[n]; G1[n] = G1[n - 1] + g[n] * n; G2[n] = G2[n - 1] + g[n] * n * n
    K += clean[n] - mAct[n]
  }

  return (byCode[code] = { car, N, stints, actC, actLife, neutral, g, mAct, clean, realStops, G0, G1, G2, K, lastBunching })
}

// ── strategies ────────────────────────────────────────────────────────────────

// The driver's real strategy as stints: [{ compound, start, end, life0 }]
export function actualStints(race, code) {
  return prepare(race, code).stints.map(s => ({ ...s }))
}

/**
 * Stints from compounds and stop laps: compounds ['MEDIUM','HARD'], stops [18] means
 * mediums to the end of lap 18, then hards. A stint that starts where a real stint of
 * the same compound started keeps that set's real age; any other set is new.
 */
export function makeStints(race, code, compounds, stops) {
  const p = prepare(race, code)
  return compounds.map((compound, i) => {
    const start = i === 0 ? 1 : stops[i - 1] + 1
    const real = p.stints.find(s => s.start === start && s.compound === compound)
    return { compound, start, end: i < stops.length ? stops[i] : p.N, life0: real ? real.life0 : 1 }
  })
}

// 'M-18-H-41-S' <-> { compounds, stops }.  null when the text is not a strategy.
export function parseStrategy(text) {
  const parts = String(text || '').toUpperCase().split('-')
  if (parts.length % 2 === 0) return null
  const compounds = [], stops = []
  for (let i = 0; i < parts.length; i++) {
    if (i % 2 === 0) {
      if (!LETTER[parts[i]]) return null
      compounds.push(LETTER[parts[i]])
    } else {
      if (!/^\d{1,3}$/.test(parts[i])) return null
      stops.push(parseInt(parts[i], 10))
    }
  }
  return { compounds, stops }
}

export function formatStrategy(stints) {
  return stints.map((s, i) => (i ? `${s.start - 1}-` : '') + (s.compound ? s.compound[0] : '?')).join('-')
}

const sameStints = (a, b) => a.length === b.length && a.every((s, i) => s.compound === b[i].compound && s.start === b[i].start && s.life0 === b[i].life0)

/**
 * Rules, as flags (nothing is thrown):
 *   { code, level: 'error' | 'warning', text, ... }
 * errors: bad_order, compound_unavailable, stop_too_early, stop_too_late, one_compound
 * warnings: extrapolation (a stint longer than the oldest tyre of that compound seen)
 * The real strategy is what happened and is never flagged for the rules.
 */
export function checkStrategy(race, code, stints) {
  const p = prepare(race, code), flags = []
  const isActual = sameStints(stints, p.stints)
  const realStops = new Set(p.car.stops)
  for (let i = 0; i < stints.length; i++) {
    const s = stints[i]
    if (s.start > s.end || (i && s.start !== stints[i - 1].end + 1) || (i === 0 && s.start !== 1) || s.end > p.N) {
      flags.push({ code: 'bad_order', level: 'error', text: 'The stops are not in lap order.' })
      return flags
    }
  }
  if (stints.length && stints[stints.length - 1].end !== p.N) flags.push({ code: 'bad_order', level: 'error', text: 'The last stint does not reach the end.' })
  for (let i = 0; i < stints.length; i++) {
    const s = stints[i], m = race.model.compounds[s.compound]
    if (!m) {
      if (!isActual) flags.push({ code: 'compound_unavailable', level: 'error', compound: s.compound, text: `${name(s.compound)} tyres were not run enough in this race to model.` })
      continue
    }
    const life = s.life0 + (s.end - s.start)
    if (life > m.max_life_seen) {
      flags.push({ code: 'extrapolation', level: 'warning', compound: s.compound, life, max: m.max_life_seen,
        text: `${life} laps on the ${name(s.compound).toLowerCase()}s: nobody ran them past ${m.max_life_seen} laps in this race, so the last ${life - m.max_life_seen} are a guess.` })
    }
    if (i === 0 || isActual) continue
    const stop = s.start - 1
    if (realStops.has(stop)) continue
    if (stop <= 2) flags.push({ code: 'stop_too_early', level: 'error', lap: stop, text: `A stop on lap ${stop} is not allowed: no stops on the first two laps.` })
    if (stop >= p.N - 1) flags.push({ code: 'stop_too_late', level: 'error', lap: stop, text: `A stop on lap ${stop} is not allowed: no stops on the last two laps.` })
  }
  if (!isActual && !p.car.retired && new Set(stints.map(s => s.compound)).size < 2) {
    flags.push({ code: 'one_compound', level: 'error', text: 'A dry race needs two different dry compounds.' })
  }
  // The first lap on which this strategy differs from the real one
  if (!isActual && p.lastBunching) {
    let first = p.N + 1
    for (let i = 0; i < Math.max(stints.length, p.stints.length); i++) {
      const a = stints[i], b = p.stints[i]
      if (a && b && a.compound === b.compound && a.life0 === b.life0 && a.start === b.start) {
        if (a.end !== b.end) { first = Math.min(a.end, b.end); break }
      } else { first = (a || b).start - (i ? 1 : 0); break }
    }
    if (first <= p.lastBunching) {
      const red = /5/.test(p.car.status.join(''))
      flags.push({ code: 'neutralised', level: 'warning', lap: p.lastBunching,
        text: `A ${red ? 'red flag or Safety Car' : 'Safety Car'} (to lap ${p.lastBunching}) came after this strategy leaves the real one on lap ${Math.max(first, 1)}. It closed the field up, so seconds gained or lost before it would not have survived; the simulation keeps them.` })
    }
  }
  return flags
}

/**
 * How far to trust a simulated strategy: { level: 'high' | 'medium' | 'low', reason }.
 * Low when a rule is broken, a stint is extrapolated or the strategy diverges before a
 * Safety Car or red flag; otherwise the weakest tyre-model confidence among the
 * compounds the change involves.
 */
export function strategyConfidence(race, code, stints, flags = checkStrategy(race, code, stints)) {
  const p = prepare(race, code), comp = race.model.compounds
  const errors = flags.filter(f => f.level === 'error')
  if (errors.length) return { level: 'low', reason: errors[0].text }
  if (sameStints(stints, p.stints)) return { level: 'high', reason: 'This is the race as it happened.' }
  for (const kind of ['extrapolation', 'neutralised']) {
    const f = flags.find(x => x.code === kind)
    if (f) return { level: 'low', reason: f.text }
  }
  const used = new Set()
  for (const s of stints) {
    for (let n = s.start; n <= s.end; n++) {
      if (p.g[n] && (s.compound !== p.actC[n] || s.life0 + (n - s.start) !== p.actLife[n])) { used.add(s.compound); used.add(p.actC[n]) }
    }
  }
  const level = lowestConfidence([...used].map(c => comp[c].confidence))
  const weakest = [...used].find(c => comp[c].confidence === level)
  return {
    level,
    reason: weakest ? `${name(weakest)} tyres: ${comp[weakest].confidence_reason}.` : 'Only the stop laps change; the tyres are as raced.',
  }
}

const name = c => (c ? c[0] + c.slice(1).toLowerCase() : 'Unknown')

// What each stop of a strategy costs: [{ lap, cond, in, out, inherited, loss, fallback }]
function stopCosts(race, p, stints) {
  const out = []
  for (let k = 1; k < stints.length; k++) {
    const lap = stints[k].start - 1
    const cond = conditionAt(p.car, lap)
    const real = p.realStops[k - 1]
    if (real && (real.lap === lap || (real.cond === 'green' && cond === 'green'))) {
      out.push({ lap, cond, in: real.inCost, out: real.outCost, inherited: true, loss: real.inCost + real.outCost, fallback: false })
    } else if (cond === 'red') {
      out.push({ lap, cond, in: 0, out: 0, inherited: false, loss: 0, fallback: false })
    } else {
      const loss = race.pit[cond] ?? race.pit.green
      out.push({ lap, cond, in: loss * race.pit.inShare, out: loss * (1 - race.pit.inShare), inherited: false, loss, fallback: cond !== 'green' && race.pit[cond] == null })
    }
  }
  return out
}

// Tyre time of one stint over the modelled laps, in O(1) from the prefix sums.
// Exact while the stint stays within the tyre ages seen (no straight-line extension).
function stintTyreTime(p, c, s) {
  const k = s.start - s.life0                    // tyre age on lap n is n - k
  const d0 = p.G0[s.end] - p.G0[s.start - 1], d1 = p.G1[s.end] - p.G1[s.start - 1], d2 = p.G2[s.end] - p.G2[s.start - 1]
  const q = c.quad_s_per_lap2 || 0
  return c.offset_s * d0 + c.deg_s_per_lap * (d1 - k * d0) + q * (d2 - 2 * k * d1 + k * k * d0)
}

// Race time of a strategy without building the laps (the optimiser's inner loop)
function fastTime(race, p, stints) {
  let t = p.K
  for (const s of stints) t += stintTyreTime(p, race.model.compounds[s.compound], s)
  for (const c of stopCosts(race, p, stints)) t += c.in + c.out
  return t
}

// ── position against the ghost field ──────────────────────────────────────────

// 1 + the cars that finished lap n before time x
function rankAtLap(race, code, n, x) {
  let rank = 1
  for (const o of Object.values(race.cars)) if (o.driver !== code && o.laps >= n && o.times[n] < x) rank++
  return rank
}

// Rank at the chequered flag for cumulative times X (index = lap): by laps completed
// when the flag falls, then by time. Returns { rank, laps }.
function rankAtFlag(race, code, X, N) {
  let flag = Infinity
  for (const o of Object.values(race.cars)) if (o.driver !== code && o.laps === race.totalLaps) flag = Math.min(flag, o.times[o.laps])
  if (N === race.totalLaps) flag = Math.min(flag, X[N])
  // the lap in progress when the winner finishes is the last one
  let laps = N
  for (let n = 1; n <= N; n++) if (X[n] >= flag) { laps = n; break }
  let rank = 1
  for (const o of Object.values(race.cars)) {
    if (o.driver === code) continue
    if (o.laps > laps || (o.laps === laps && o.times[o.laps] < X[laps])) rank++
  }
  return { rank, laps }
}

// The car that crossed the line last before time x, if within `gap` seconds: { driver, gap, dur }
function carAhead(race, code, x, gap) {
  const times = race.crossingTimes
  let lo = 0, hi = times.length - 1
  while (lo <= hi) { const mid = (lo + hi) >> 1; if (times[mid] < x) lo = mid + 1; else hi = mid - 1 }
  for (let i = hi; i >= 0 && x - times[i] <= gap; i--) {
    const c = race.crossings[i]
    if (c.driver !== code) return { driver: c.driver, gap: x - c.t, dur: c.dur }
  }
  return null
}

function carsAhead(race, code, x, gap) {
  const times = race.crossingTimes, out = []
  let lo = 0, hi = times.length - 1
  while (lo <= hi) { const mid = (lo + hi) >> 1; if (times[mid] < x) lo = mid + 1; else hi = mid - 1 }
  for (let i = hi; i >= 0 && x - times[i] <= gap; i--) {
    const c = race.crossings[i]
    if (c.driver !== code && !out.some(o => o.driver === c.driver)) out.push({ driver: c.driver, gap: x - c.t })
  }
  return out
}

// Laps spent within TRAFFIC_GAP_S behind a car that was slower on that lap
function trafficLaps(race, code, p, X, lapTime) {
  const by = {}
  let laps = 0
  for (let n = 2; n <= p.N; n++) {
    if (p.neutral[n]) continue
    const ahead = carAhead(race, code, X[n], TRAFFIC_GAP_S)
    if (ahead && ahead.dur > lapTime(n)) { laps++; by[ahead.driver] = (by[ahead.driver] || 0) + 1 }
  }
  return { laps, cars: Object.entries(by).sort((a, b) => b[1] - a[1]).map(([driver, n]) => ({ driver, laps: n })) }
}

// ── simulate ──────────────────────────────────────────────────────────────────

/**
 * Simulate one driver on a strategy against the real field.
 * @param stints  [{ compound, start, end, life0 }]  (makeStints / actualStints)
 * @param seed    Monte Carlo seed;  runs  number of runs (0 = none)
 * Returns the result described field by field below.
 */
export function simulate(race, code, stints, { seed = 1, runs = SIM_RUNS } = {}) {
  const p = prepare(race, code), { car, N } = p
  const comp = race.model.compounds
  const flags = checkStrategy(race, code, stints)
  const broken = flags.some(f => f.code === 'bad_order')
  if (broken) stints = p.stints
  const isActual = sameStints(stints, p.stints)

  // Tyres on every lap of the alternative
  const altC = new Array(N + 1).fill(null), altLife = new Float64Array(N + 1)
  for (const s of stints) for (let n = s.start; n <= s.end; n++) { altC[n] = s.compound; altLife[n] = s.life0 + (n - s.start) }

  const costs = stopCosts(race, p, stints)
  const pitAt = new Float64Array(N + 2)
  for (const c of costs) { pitAt[c.lap] += c.in; pitAt[c.lap + 1] += c.out }

  // Lap by lap
  const changed = new Uint8Array(N + 1)
  const lap = new Float64Array(N + 1), alt = new Float64Array(N + 1), real = car.times
  for (let n = 1; n <= N; n++) {
    let delta = 0
    if (p.g[n] && comp[altC[n]] && (altC[n] !== p.actC[n] || altLife[n] !== p.actLife[n])) {
      delta = tyreEffect(comp[altC[n]], altLife[n]) - p.mAct[n]
      changed[n] = 1
    }
    lap[n] = p.clean[n] + delta + pitAt[n]
    alt[n] = alt[n - 1] + lap[n]
  }

  // Positions against the ghost field (as a change from the real one, so the real
  // strategy gives the real positions even where the data ranks by classification)
  const posReal = new Array(N + 1).fill(null), posAlt = new Array(N + 1).fill(null)
  for (let n = 1; n <= N; n++) {
    const was = rankAtLap(race, code, n, real[n])
    posReal[n] = car.pos[n] || was
    posAlt[n] = Math.max(1, posReal[n] + rankAtLap(race, code, n, alt[n]) - was)
  }
  const nCars = Object.keys(race.cars).length
  const flagReal = car.retired ? null : rankAtFlag(race, code, real, N)
  const realFinish = car.retired ? posReal[N] : car.finish ?? flagReal.rank
  const finishOf = X => {
    if (car.retired) return Math.max(1, posReal[N] + rankAtLap(race, code, N, X[N]) - rankAtLap(race, code, N, real[N]))
    return Math.min(nCars, Math.max(1, realFinish + rankAtFlag(race, code, X, N).rank - flagReal.rank))
  }
  const altFinish = finishOf(alt)

  // ── Monte Carlo ──
  const band = { p10: new Float64Array(N + 1), p50: new Float64Array(N + 1), p90: new Float64Array(N + 1) }
  const shares = {}
  let time = { delta: alt[N] - real[N], p10: alt[N] - real[N], p50: alt[N] - real[N], p90: alt[N] - real[N] }
  let finish = { real: realFinish, alt: altFinish, p10: altFinish, p50: altFinish, p90: altFinish, shares: { [altFinish]: 1 } }
  const anyNoise = !isActual && (changed.some(Boolean) || costs.some(c => !c.inherited && c.cond !== 'red'))
  if (runs > 0 && anyNoise) {
    const rng = makeRandom(seed)
    const names = race.compounds
    const perLap = Array.from({ length: N + 1 }, () => new Float32Array(runs))
    const finishes = new Float64Array(runs), X = new Float64Array(N + 1)
    const zOff = {}, zDeg = {}
    const stintOf = new Uint8Array(N + 1), stintChanged = new Float64Array(stints.length), stintDraw = new Float64Array(stints.length)
    stints.forEach((st, k) => { for (let n = st.start; n <= st.end; n++) { stintOf[n] = k; stintChanged[k] += changed[n] } })
    for (let r = 0; r < runs; r++) {
      for (const c of names) { zOff[c] = rng.normal() * (comp[c].offset_se || 0); zDeg[c] = rng.normal() * (comp[c].deg_se || 0) }
      const pitShift = new Float64Array(N + 2)
      for (const c of costs) {
        if (c.inherited || c.cond === 'red') continue
        const pool = race.pit.samples[c.cond] || []
        const drawn = pool.length >= MIN_SAMPLES && !c.fallback
          ? pool[Math.floor(rng.uniform() * pool.length)] - median(pool) + c.loss
          : c.loss + rng.normal() * PIT_NOISE_S
        pitShift[c.lap + 1] += Math.max(drawn, 0.5 * c.loss) - c.loss
      }
      // one draw per stint for what the model gets wrong about a stint it has not seen,
      // spread over the stint's changed laps
      for (let k = 0; k < stints.length; k++) {
        stintDraw[k] = stintChanged[k] ? rng.normal() * race.model.stintSd * Math.min(1, stintChanged[k] / STINT_ERROR_LAPS) / stintChanged[k] : 0
      }
      let shift = 0
      for (let n = 1; n <= N; n++) {
        if (changed[n]) {
          shift += stintDraw[stintOf[n]]
          const a = altC[n], b = p.actC[n]
          shift += zOff[a] - zOff[b] + zDeg[a] * altLife[n] - zDeg[b] * p.actLife[n] + rng.normal() * comp[a].residual_sd_s
        }
        shift += pitShift[n]
        X[n] = alt[n] + shift
        perLap[n][r] = X[n] - real[n]
      }
      finishes[r] = finishOf(X)
      shares[finishes[r]] = (shares[finishes[r]] || 0) + 1
    }
    for (let n = 1; n <= N; n++) {
      const s = perLap[n].sort()
      band.p10[n] = quantileSorted(s, 0.1); band.p50[n] = quantileSorted(s, 0.5); band.p90[n] = quantileSorted(s, 0.9)
    }
    const f = finishes.slice().sort()
    for (const k in shares) shares[k] /= runs
    time = { delta: alt[N] - real[N], p10: band.p10[N], p50: band.p50[N], p90: band.p90[N] }
    finish = { real: realFinish, alt: Math.round(quantileSorted(f, 0.5)), p10: Math.round(quantileSorted(f, 0.1)), p90: Math.round(quantileSorted(f, 0.9)), shares }
  } else {
    for (let n = 1; n <= N; n++) band.p10[n] = band.p50[n] = band.p90[n] = alt[n] - real[n]
  }

  // ── Traffic (reported, never charged) ──
  const traffic = trafficLaps(race, code, p, alt, n => lap[n])
  const realTraffic = trafficLaps(race, code, p, real, n => real[n] - real[n - 1])
  const rejoins = costs.filter(c => !(c.inherited && p.realStops.some(r => r.lap === c.lap)) && c.lap + 1 <= N)
    .map(c => ({ lap: c.lap, cars: carsAhead(race, code, alt[c.lap + 1], REJOIN_GAP_S) }))
  const atFlag = carsAhead(race, code, alt[N], REJOIN_GAP_S)

  const errors = flags.filter(f => f.level === 'error')
  const confidence = strategyConfidence(race, code, stints, flags)

  return {
    driver: code,
    valid: !errors.length,
    isActual,
    flags,
    confidence,
    laps: N,
    retiredAt: car.retired ? N : null,
    strategy: formatStrategy(stints),
    stints: stints.map(s => ({ ...s })),
    lapTime: { real: Float64Array.from(real, (t, n) => (n ? t - real[n - 1] : 0)), alt: lap },
    compound: { real: p.actC, alt: altC },
    gap: Float64Array.from(alt, (t, n) => t - real[n]),     // alt minus real race time, per lap: below zero = ahead
    band,
    position: { real: posReal, alt: posAlt },
    finish,
    time,
    stops: { real: car.stops.slice(), alt: costs.map(c => c.lap) },
    pit: costs,
    traffic: { laps: traffic.laps, realLaps: realTraffic.laps, cars: traffic.cars, rejoins, atFlag },
  }
}

// ── optimiser ─────────────────────────────────────────────────────────────────

// Every 1-stop and 2-stop strategy that passes the rules and stays within the tyre ages
// seen, plus the real strategy; calls visit(stints, time) for each
function search(race, code, visit) {
  const p = prepare(race, code), N = p.N
  const comp = race.model.compounds, names = race.compounds
  const first = 3, last = N - 2
  const life0 = (c, start) => { const r = p.stints.find(s => s.start === start && s.compound === c); return r ? r.life0 : 1 }
  const fits = s => s.life0 + (s.end - s.start) <= comp[s.compound].max_life_seen
  visit(p.stints, p.car.times[N], true)          // the real race, exactly
  for (const a of names) {
    for (let p1 = first; p1 <= last; p1++) {
      const s1 = { compound: a, start: 1, end: p1, life0: life0(a, 1) }
      if (!fits(s1)) break
      for (const b of names) {
        const one = { compound: b, start: p1 + 1, end: N, life0: life0(b, p1 + 1) }
        if (a !== b && fits(one)) { const st = [s1, one]; visit(st, fastTime(race, p, st), false) }
        for (let p2 = p1 + 1; p2 <= last; p2++) {
          const s2 = { compound: b, start: p1 + 1, end: p2, life0: one.life0 }
          if (!fits(s2)) break
          for (const c of names) {
            if (a === b && b === c) continue
            const s3 = { compound: c, start: p2 + 1, end: N, life0: life0(c, p2 + 1) }
            if (fits(s3)) { const st = [s1, s2, s3]; visit(st, fastTime(race, p, st), false) }
          }
        }
      }
    }
  }
}

/**
 * The fastest strategies for a driver: every 1-stop and 2-stop combination of the
 * compounds in the model and every pit lap, within the rules and the tyre ages seen.
 * Returns the top `top` by median simulated time, each with its range:
 *   { strategy, stints, isActual, time: { delta, p10, p50, p90 }, finish, confidence }
 * The real strategy is always a candidate, so the best is never slower than what happened.
 * `stops` (1 or 2) limits the search to strategies with that many stops (the real one
 * is then not a candidate, and the list can be empty).
 */
export function bestStrategies(race, code, { top = 5, seed = 1, runs = SIM_RUNS, stops = null } = {}) {
  const best = []
  let searched = 0
  search(race, code, (stints, time, isActual) => {
    if (stops != null && (isActual || stints.length - 1 !== stops)) return   // only strategies with this many stops
    searched++
    if (best.length === top && time >= best[top - 1].time) return
    const entry = { time, isActual, stints: stints.map(s => ({ ...s })) }
    let i = best.length
    while (i > 0 && best[i - 1].time > time) i--
    best.splice(i, 0, entry)
    if (best.length > top) best.pop()
  })
  const out = best.map(b => {
    const r = simulate(race, code, b.stints, { seed, runs })
    return { strategy: r.strategy, stints: b.stints, isActual: b.isActual, time: r.time, finish: r.finish, confidence: r.confidence }
  })
  out.sort((a, b) => a.time.p50 - b.time.p50)
  out.searched = searched
  return out
}

/**
 * For choosing who to open the page on: each driver's best strategy by the model
 * (no Monte Carlo).  { VER: { strategy, delta, confidence } }  delta <= 0, seconds gained.
 */
export function bestGains(race, codes) {
  const out = {}
  for (const code of codes) {
    if (!race.cars[code] || race.cars[code].retired) continue
    const p = prepare(race, code), realTime = p.car.times[p.N]
    let best = null
    search(race, code, (stints, time) => { if (!best || time < best.time) best = { time, stints: stints.map(s => ({ ...s })) } })
    out[code] = { strategy: formatStrategy(best.stints), delta: Math.min(0, best.time - realTime), confidence: strategyConfidence(race, code, best.stints).level }
  }
  return out
}

// Exposed for the tests: the O(1) race time must equal the lap-by-lap one
export function modelTime(race, code, stints) {
  return fastTime(race, prepare(race, code), stints)
}
