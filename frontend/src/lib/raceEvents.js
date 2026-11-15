// What happened in a race, derived from the static files: track-status bands,
// pit stops, and the event list the replay feed fills in as the race plays.
// Pure functions; inputs are parseLaps() output and the raw JSON files.

import { isPitStop } from './laps'

export const STATUS_LABEL = {
  red: 'Red flag', sc: 'Safety Car', vsc: 'Virtual Safety Car', yellow: 'Yellow flag',
}
const SEVERITY = { red: 4, sc: 3, vsc: 2, yellow: 1 }

/**
 * Track-status bands by lap: [{ type: 'red'|'sc'|'vsc'|'yellow', startLap, endLap }].
 * Safety Car and VSC come from sc_periods; red and yellow flags from the lap fields of
 * periods (which start at lights out: the pipeline drops what happened before).
 */
export function statusBands(trackStatus, totalLaps) {
  const raw = []
  for (const p of trackStatus?.sc_periods || []) raw.push({ type: p.type, startLap: p.start_lap, endLap: p.end_lap })
  for (const p of trackStatus?.periods || []) {
    if (p.status !== 'red' && p.status !== 'yellow') continue
    raw.push({ type: p.status, startLap: p.start_lap, endLap: p.end_lap })
  }
  const bands = []
  raw.sort((a, b) => SEVERITY[b.type] - SEVERITY[a.type] || a.startLap - b.startLap)
  for (const b of raw) {
    if (!(b.type in SEVERITY) || !(b.startLap >= 1)) continue
    const band = { type: b.type, startLap: b.startLap, endLap: Math.min(Math.max(b.endLap ?? b.startLap, b.startLap), totalLaps) }
    const last = bands[bands.length - 1]
    // back-to-back periods of one kind are one band
    if (last && last.type === band.type && band.startLap <= last.endLap + (band.type === 'yellow' ? 0 : 1)) last.endLap = Math.max(last.endLap, band.endLap)
    else bands.push(band)
  }
  return bands.sort((a, b) => a.startLap - b.startLap || SEVERITY[b.type] - SEVERITY[a.type])
}

// The most serious status on a lap: 'red' | 'sc' | 'vsc' | 'yellow' | null (green)
export function lapStatus(bands, lap) {
  let best = null
  for (const b of bands) {
    if (lap >= b.startLap && lap <= b.endLap && (!best || SEVERITY[b.type] > SEVERITY[best])) best = b.type
  }
  return best
}

/**
 * A driver's stints, from the stint column of laps.json:
 *   [{ stint, compound, startLap, endLap, startAge }]   (startAge: tyre age on the first lap)
 */
export function stints(d) {
  const out = []
  for (let n = 1; n <= d.laps; n++) {
    if (!d.has[n]) continue
    const last = out[out.length - 1]
    if (last && last.stint === d.stint[n]) {
      last.endLap = n
      last.compound ||= d.compound[n]
    } else {
      out.push({ stint: d.stint[n], compound: d.compound[n], startLap: n, endLap: n, startAge: d.tyreLife[n] })
    }
  }
  return out
}

/**
 * Every pit stop: the lap a driver came in on and what they left with.
 *   { driver, lap, from, to, tyreAge, loss, condition, status, posBefore, posAfter }
 * loss is the measured time lost from pit_loss.json (null when it was not measured);
 * status is the track status around the stop; a "stop" under a red flag is a free change.
 */
export function pitStops(laps, pitLoss, bands) {
  const measured = {}
  for (const s of pitLoss?.stops || []) measured[`${s.driver}:${s.lap}`] = s
  const stops = []
  for (const d of Object.values(laps.drivers)) {
    for (let n = 1; n < d.laps; n++) {
      if (!isPitStop(d, n)) continue
      const m = measured[`${d.driver}:${n}`]
      const here = lapStatus(bands, n), next = lapStatus(bands, n + 1)
      const status = [here, next].sort((a, b) => (SEVERITY[b] || 0) - (SEVERITY[a] || 0))[0] || null
      stops.push({
        driver: d.driver,
        lap: n,
        from: d.compound[n],
        to: d.compound[n + 1],
        tyreAge: d.tyreLife[n] || null,
        loss: m ? m.loss_s : null,
        condition: m ? m.condition : null,
        status: status === 'yellow' ? null : status,
        posBefore: d.position[n - 1] || d.position[n] || null,
        posAfter: d.position[n + 1] || null,
      })
    }
  }
  return stops.sort((a, b) => a.lap - b.lap || (a.posBefore || 99) - (b.posBefore || 99))
}

// The driver in P1 at the end of each lap (index = lap; index 0 = pole, when known)
export function leaders(laps, results) {
  const out = new Array(laps.totalLaps + 1).fill(null)
  out[0] = (results || []).find(r => r.grid_position === 1)?.driver || null
  for (const d of Object.values(laps.drivers)) {
    for (let n = 1; n <= d.laps; n++) if (d.position[n] === 1) out[n] = d.driver
  }
  for (let n = 1; n < out.length; n++) out[n] ||= out[n - 1]   // a lap with no P1 row: nobody passed anybody
  return out
}

/**
 * The replay feed. Each event has `p`, the playhead (in leader laps) at which it
 * happens, so the feed can show the ones already passed and jump to any of them.
 *   type: 'pit' | 'status' | 'clear' | 'lead' | 'retired' | 'fastest'
 */
export function raceEvents({ clock, laps, results, bands, stops }) {
  const events = []
  const at = (driver, lap) => clock.playheadAt(clock.byCode[driver].times[Math.min(lap, clock.byCode[driver].done)])

  for (const s of stops) {
    if (s.status === 'red') continue   // tyres changed in the pit lane during the stoppage
    events.push({ type: 'pit', p: at(s.driver, s.lap), lap: s.lap, driver: s.driver, from: s.from, to: s.to, loss: s.loss })
  }

  for (const b of bands) {
    events.push({ type: 'status', p: b.startLap - 1, lap: b.startLap, status: b.type })
    if (b.type !== 'yellow' && b.endLap < clock.totalLaps) {
      events.push({ type: 'clear', p: b.endLap, lap: b.endLap, status: b.type })
    }
  }

  const lead = leaders(laps, results)
  for (let n = 1; n <= clock.totalLaps; n++) {
    if (lead[n] && lead[n - 1] && lead[n] !== lead[n - 1]) {
      events.push({ type: 'lead', p: n, lap: n, driver: lead[n], from: lead[n - 1] })
    }
  }

  for (const d of clock.drivers) {
    if (!d.retired) continue
    events.push({ type: 'retired', p: clock.playheadAt(d.times[d.done] + (d.partial?.dur || 0)), lap: Math.min(d.done + 1, clock.totalLaps), driver: d.driver })
  }

  // Fastest lap so far: every time the race's best lap is beaten
  const timed = []
  for (const d of clock.drivers) {
    for (let n = 2; n <= d.done; n++) {
      const t = d.data.time[n]
      if (Number.isFinite(t) && !d.data.deleted[n] && !d.data.pitIn[n] && !d.data.pitOut[n]) timed.push({ driver: d.driver, lap: n, time: t, at: d.times[n] })
    }
  }
  timed.sort((a, b) => a.at - b.at)
  let best = Infinity
  for (const l of timed) {
    if (l.time >= best) continue
    best = l.time
    events.push({ type: 'fastest', p: clock.playheadAt(l.at), lap: l.lap, driver: l.driver, time: l.time })
  }

  return events.sort((a, b) => a.p - b.p)
}
