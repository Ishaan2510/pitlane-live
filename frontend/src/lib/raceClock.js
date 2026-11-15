// raceClock: where every car is at any moment of a finished race.
//
// The data only knows lap ends: laps.json has each driver's lap times and positions,
// replay.json has each driver's gap to the leader at the end of every lap. From those
// this builds, for every driver, the race time at which they finished each lap, T[d][n].
//
// METHOD
// 1. Missing lap times (lap 1 and red-flag laps in FastF1 races, the odd dropped lap)
//    are filled by linear interpolation between the driver's nearest timed laps.
// 2. The spine S[n] is the race time at which the leader finished lap n:
//      S[n] = T[leader of lap n][n-1] + that driver's lap n time,   S[0] = 0.
//    The leader of a lap is P1 in replay.json, so the spine follows lead changes.
//    If the leader's lap time is missing (FastF1 drops the lap a red flag fell in), the
//    lap's length is taken from the rest of the field instead: the largest, over the
//    other drivers, of  their lap time - (their gap now - their gap a lap earlier),
//    which is how long the leader must have taken for every one of those gaps to be true.
// 3. Every other driver is placed by their gap:  T[d][n] = S[n] + gap[d][n].
//    Where the gap is missing the driver's own cumulative sum is used instead:
//      T[d][n] = T[d][n-1] + lap time.
//    A gap that would give a lap shorter than 25% of the driver's lap time is clamped
//    to that 25%, so a car that was placed late catches up over the next laps instead
//    of staying out of step for the rest of the race.
// 4. At each lap end the times are nudged (by 1 ms steps, later only) so their order is
//    the order of the positions in laps.json. Positions in the data always win.
// So T is strictly increasing for each driver, and at every lap end the order of the
// cars is the order in laps.json.
//
// TIME AXES
// - race time `t`, in seconds from lights out
// - the playhead, in leader laps: 0 = lights out, 23.5 = the leader is halfway round
//   lap 24. Playback and the timeline use the playhead, so a red-flag lap that lasted
//   40 minutes plays as fast as any other lap. timeAt() / playheadAt() convert.
//
// WITHIN A LAP a car moves at constant speed: fraction = time into the lap / lap time.
// Its place on the map is fraction * circuit.total_distance. Exceptions:
// - Pit stop: the car is held at fraction 0 of its out-lap (the pit-entry end of the
//   in-lap) for the measured loss from pit_loss.json (track median, else 22 s; never
//   more than 60% of the out-lap), flagged inPit, then runs the rest of the out-lap.
// - Retirement: a retired car's last row is usually an unfinished lap. It runs that lap
//   as far as the sectors it completed (0, 1/3 or 2/3 of the lap; to the pit entry if
//   it retired in the pits) and stops there, flagged retired.
//
// LIMITS: no data on where on track a car was inside a lap, so speed is uniform and
// the start is not staggered by grid slot (all cars leave the line at t = 0).
//
// RETIRED CARS IN THE ORDER
// Running cars are ranked by distance covered. A car that has stopped for good has no
// distance to compare: the timing feeds keep it in its place for a while and then drop
// it, sooner or later than the cars behind actually pass where it stopped. So a stopped
// car's rank comes from the data instead. Every lap end of every other car says how
// many cars were ahead of it; whatever the running cars do not account for must be
// stopped cars, and the stopped cars are moved just ahead of or just behind that line
// to make the count right. Between lap ends a stopped car keeps the rank it last had.

import { TEAM_COLORS } from '@/data/drivers'
import { isPitStop } from './laps'

const DEFAULT_PIT_LOSS_S = 22
const MAX_HOLD_SHARE = 0.6     // a pit hold never takes more than this share of the out-lap
const MIN_LAP_SHARE = 0.25     // a gap that implies a lap shorter than this share is a glitch
const NUDGE_S = 0.001
const RANK_STEP = 1e-6       // how far past a car a stopped car is ranked, in laps

function parseGap(gap) {
  if (typeof gap === 'number') return gap
  const v = parseFloat(String(gap ?? '').replace('+', ''))
  return Number.isFinite(v) ? v : NaN     // "LEADER" (P1, or unknown) -> NaN
}

// Lap times with the holes filled: linear between the nearest timed laps, nearest at the ends
function fillLapTimes(time, laps, fallback) {
  const out = new Float64Array(laps + 1)
  let prev = 0
  for (let n = 1; n <= laps; n++) {
    if (Number.isFinite(time[n])) { out[n] = time[n]; prev = n; continue }
    let next = n + 1
    while (next <= laps && !Number.isFinite(time[next])) next++
    const a = prev ? time[prev] : NaN, b = next <= laps ? time[next] : NaN
    if (Number.isFinite(a) && Number.isFinite(b)) out[n] = a + (b - a) * (n - prev) / (next - prev)
    else out[n] = Number.isFinite(a) ? a : Number.isFinite(b) ? b : fallback
  }
  return out
}

// Index of the first element of the ascending array `arr` (in [lo, hi]) greater than x
function upperBound(arr, x, lo, hi) {
  while (lo <= hi) {
    const mid = (lo + hi) >> 1
    if (arr[mid] > x) hi = mid - 1
    else lo = mid + 1
  }
  return lo
}

/**
 * @param laps     parseLaps(laps.json)
 * @param replay   replay.json
 * @param results  results.json (team colours, grid, who retired); may be null
 * @param pitLoss  pit_loss.json; may be null
 */
export function buildRaceClock({ laps, replay, results = null, pitLoss = null }) {
  const totalLaps = replay.total_laps || laps.totalLaps
  const resultOf = Object.fromEntries((results || []).map(r => [r.driver, r]))

  // gap[d][n] and the leader of each lap, from replay.json
  const gap = {}, leaderOf = new Array(totalLaps + 1).fill(null)
  for (const lap of replay.laps) {
    const n = lap.lap_number
    lap.drivers.forEach((d, i) => {
      if (i === 0 && n <= totalLaps) leaderOf[n] = d.driver;
      (gap[d.driver] ||= new Float64Array(totalLaps + 2).fill(NaN))[n] = i === 0 ? 0 : parseGap(d.gap)
    })
  }

  const lossOf = {}
  for (const s of pitLoss?.stops || []) lossOf[`${s.driver}:${s.lap}`] = s.loss_s
  const medianLoss = pitLoss?.median_loss_s > 0 ? pitLoss.median_loss_s : DEFAULT_PIT_LOSS_S

  // A typical lap, for drivers with no timed lap at all
  const allTimes = []
  for (const code in laps.drivers) for (const v of laps.drivers[code].time) if (Number.isFinite(v)) allTimes.push(v)
  allTimes.sort((a, b) => a - b)
  const typicalLap = allTimes[allTimes.length >> 1] || 90

  const drivers = Object.values(laps.drivers).map(d => {
    const res = resultOf[d.driver]
    // Stopped before the flag. A car can retire late and still be classified, so this
    // reads the status, not the classification.
    const retired = res ? /retired|not start/i.test(res.status) : false
    // A retired car's last row without a lap time is the lap it did not finish
    const partialLap = retired && d.laps >= 1 && !Number.isFinite(d.time[d.laps])
    const done = Math.min(partialLap ? d.laps - 1 : d.laps, totalLaps)
    return {
      driver:  d.driver,
      team:    d.team,
      color:   res?.team_color || TEAM_COLORS[d.team] || '#888888',
      grid:    res?.grid_position > 0 ? res.grid_position : 99,   // 0 = pit lane start
      retired,
      done,                                           // laps completed
      data:    d,                                     // the parsed lap arrays
      filled:  fillLapTimes(d.time, d.laps, typicalLap),
      times:   new Float64Array(done + 1),            // T[n]: race time at the end of lap n
      hold:    new Float64Array(d.laps + 2),          // pit hold at the start of lap n, seconds
      partial: null,                                  // { frac, dur } of the unfinished last lap
      rankT:   [],                                    // once stopped for good: from race time rankT[i]
      rankV:   [],                                    //   the car ranks as if it had covered rankV[i] laps
      _partialLap: partialLap,
    }
  })
  const byCode = Object.fromEntries(drivers.map(d => [d.driver, d]))

  // ── Lap end times, lap by lap ──
  const spine = new Float64Array(totalLaps + 1)
  const stats = { fallbacks: 0, clamps: 0, nudges: 0, maxNudge: 0 }
  for (let n = 1; n <= totalLaps; n++) {
    const running = drivers.filter(d => d.done >= n)
    if (!running.length) { spine[n] = spine[n - 1] + typicalLap; continue }

    let leader = byCode[leaderOf[n]]
    if (!leader || leader.done < n) {
      // no usable P1 in replay.json: the car that gets there first on its own lap times
      leader = running.reduce((a, b) => (a.times[n - 1] + a.filled[n] <= b.times[n - 1] + b.filled[n] ? a : b))
    }
    let leaderEnd = leader.times[n - 1] + leader.filled[n]
    if (!Number.isFinite(leader.data.time[n])) {
      // no lap time for the leader: how long the field's gaps say the lap took
      for (const d of running) {
        const g1 = gap[d.driver]?.[n], g0 = n > 1 ? gap[d.driver]?.[n - 1] : 0
        if (d !== leader && Number.isFinite(g1) && Number.isFinite(g0)) {
          leaderEnd = Math.max(leaderEnd, spine[n - 1] + d.filled[n] - (g1 - g0))
        }
      }
    }
    spine[n] = Math.max(leaderEnd, spine[n - 1] + NUDGE_S)

    for (const d of running) {
      const own = d.times[n - 1] + d.filled[n]
      const g = gap[d.driver]?.[n]
      let t = d === leader ? spine[n] : spine[n] + g
      if (!Number.isFinite(t)) { t = own; stats.fallbacks++ }
      const earliest = d.times[n - 1] + MIN_LAP_SHARE * d.filled[n]
      if (t < earliest) { t = earliest; stats.clamps++ }
      d.times[n] = t
    }

    // The order at the line is the order of the positions in laps.json. A car with no
    // position on a lap (a retiring car's last lap, usually) crosses after those that have one.
    const ranked = running.slice().sort((a, b) => (a.data.position[n] || 99) - (b.data.position[n] || 99) || a.times[n] - b.times[n])
    for (let i = 1; i < ranked.length; i++) {
      const floor = ranked[i - 1].times[n] + NUDGE_S
      if (ranked[i].times[n] < floor) {
        stats.nudges++
        stats.maxNudge = Math.max(stats.maxNudge, floor - ranked[i].times[n])
        ranked[i].times[n] = floor
      }
    }
    // Belt and braces: T must increase for every driver
    for (const d of running) if (d.times[n] <= d.times[n - 1]) d.times[n] = d.times[n - 1] + NUDGE_S
  }

  // ── Pit holds and unfinished last laps ──
  for (const d of drivers) {
    const L = d.data
    for (let n = 2; n <= d.done; n++) {
      if (!isPitStop(L, n - 1)) continue
      const loss = lossOf[`${d.driver}:${n - 1}`]
      const dur = d.times[n] - d.times[n - 1]
      d.hold[n] = Math.min(loss > 0 ? loss : medianLoss, MAX_HOLD_SHARE * dur)
    }
    if (d._partialLap) {
      const n = d.done + 1
      const frac = L.pitIn[n] ? 1 : Math.min(L.sectors[n], 2) / 3
      if (frac > 0) d.partial = { frac, dur: frac * d.filled[n] }
    }
    delete d._partialLap
  }

  const duration = spine[totalLaps]

  // Race time at which the leader had covered `p` laps (the playhead -> seconds)
  function timeAt(p) {
    if (p <= 0) return 0
    if (p >= totalLaps) return duration
    const n = Math.floor(p)
    return spine[n] + (p - n) * (spine[n + 1] - spine[n])
  }

  // Inverse of timeAt
  function playheadAt(t) {
    if (t <= 0) return 0
    if (t >= duration) return totalLaps
    const n = upperBound(spine, t, 0, totalLaps) - 1
    return n + (t - spine[n]) / (spine[n + 1] - spine[n])
  }

  /**
   * Every car at race time t, sorted by position. Each entry:
   *   driver, team, color
   *   lap        lap the car is on (1-based; its last lap once it has stopped)
   *   fraction   share of that lap completed, 0..1: map distance = fraction * total_distance
   *   progress   laps covered, as a number (completed laps + fraction)
   *   position   1-based rank by progress
   *   gap        seconds behind the leader (0 for the leader, null once retired)
   *   interval   seconds behind the car ahead (null for the leader and retired cars)
   *   lapsDown   whole laps behind the leader
   *   compound, tyreAge   tyre on the current lap (compound is null when unknown)
   *   inPit      in the pit lane (held at the pit-entry end of the lap)
   *   retired    out of the race and stopped;  finished  took the flag
   *   stoppedFor seconds since the car stopped (0 while running), for fading it out
   */
  function stateAt(t) {
    const cars = rank(carsAt(t))
    const lead = cars[0]
    let ahead = null
    cars.forEach((c, i) => {
      c.position = i + 1
      if (!c.retired) {
        c.gap = i === 0 ? 0 : c.finished ? c._finalGap : Math.max(0, t - timeAt(c.progress))
        c.lapsDown = Math.max(0, Math.floor(lead.progress - c.progress + 1e-9))
        if (ahead) c.interval = Math.max(0, c.gap - ahead.gap)
        ahead = c
      }
      delete c._key
      delete c._reached
      delete c._grid
      delete c._finalGap
    })
    return cars
  }

  // Where every car is at race time t, unranked
  function carsAt(t) {
    return drivers.map(d => {
      const L = d.data, T = d.times
      let lap, fraction = 0, progress, inPit = false, stoppedFor = 0
      let reached = T[d.done]                                // when it got to `progress`, for ties

      if (t < T[d.done]) {
        lap = Math.max(1, upperBound(T, t, 0, d.done))      // T[lap-1] <= t < T[lap]
        const into = t - T[lap - 1], dur = T[lap] - T[lap - 1], hold = d.hold[lap]
        if (into < hold) inPit = true
        else fraction = (into - hold) / (dur - hold)
        if (fraction > 0.97 && isPitStop(L, lap)) inPit = true   // rolling into the pit lane
        progress = lap - 1 + fraction
        reached = T[lap - 1]
      } else if (d.partial && t - T[d.done] < d.partial.dur) {
        // the lap it will not finish
        lap = d.done + 1
        fraction = (t - T[d.done]) / d.partial.dur * d.partial.frac
        progress = d.done + fraction
      } else {
        // stopped: at the flag, or retired
        lap = d.partial ? d.done + 1 : Math.max(d.done, 1)
        fraction = d.partial ? d.partial.frac : d.done ? 1 : 0
        progress = d.done + (d.partial ? d.partial.frac : 0)
        stoppedFor = t - T[d.done] - (d.partial?.dur || 0)
        inPit = d.retired && !!L.pitIn[Math.min(lap, L.laps)]
      }

      const row = Math.min(lap, L.laps)
      const stopped = t >= T[d.done] + (d.partial?.dur || 0)
      const retired = d.retired && stopped
      // Rank key: laps covered, or for a stopped car the rank the data last gave it
      let key = progress
      if (retired && d.rankT.length) {
        const i = upperBound(d.rankT, t, 0, d.rankT.length - 1) - 1
        if (i >= 0) key = d.rankV[i]
      }
      return {
        driver: d.driver, team: d.team, color: d.color,
        lap, fraction, progress, position: 0, gap: null, interval: null, lapsDown: 0,
        compound: L.compound[row], tyreAge: L.tyreLife[row],
        inPit, retired, finished: !d.retired && stopped, stoppedFor,
        _key: key, _reached: reached, _grid: d.grid, _finalGap: T[d.done] - spine[d.done],
      }
    })
  }

  // By distance covered (stopped cars by their data rank); level cars by who got there
  // first, then by grid slot
  function rank(cars) {
    return cars.sort((a, b) => b._key - a._key || a._reached - b._reached || a._grid - b._grid)
  }

  // ── Where the data puts each stopped car (see RETIRED CARS IN THE ORDER) ──
  if (drivers.some(d => d.retired)) {
    const lapEnds = []
    for (const d of drivers) {
      for (let n = 1; n <= d.done; n++) if (d.data.position[n] > 0) lapEnds.push({ t: d.times[n], d, n, p: d.data.position[n] })
    }
    lapEnds.sort((a, b) => a.t - b.t)
    // nothing to place until the first car has stopped
    let firstStop = Infinity
    for (const d of drivers) if (d.retired) firstStop = Math.min(firstStop, d.times[d.done] + (d.partial?.dur || 0))
    for (const e of lapEnds) {
      if (e.t < firstStop) continue
      let aheadRunning = 0
      const stopped = []
      for (const car of carsAt(e.t)) {
        if (car.driver === e.d.driver) continue
        if (car.retired) stopped.push(car)
        else if (car.progress > e.n || (car.progress === e.n && car._reached < e.t)) aheadRunning++
      }
      if (!stopped.length) continue
      rank(stopped)
      // this many stopped cars are still ahead of the car that just crossed the line
      const k = Math.min(stopped.length, Math.max(0, e.p - 1 - aheadRunning))
      stopped.forEach((car, i) => {
        const isAhead = car._key > e.n || (car._key === e.n && car._reached < e.t)
        if (i < k === isAhead) return
        const x = byCode[car.driver]
        x.rankT.push(e.t)
        x.rankV.push(i < k ? e.n + RANK_STEP * (stopped.length - i) : e.n - RANK_STEP * (i + 1))
      })
    }
  }

  return { totalLaps, duration, drivers, byCode, spine, stats, timeAt, playheadAt, stateAt }
}
