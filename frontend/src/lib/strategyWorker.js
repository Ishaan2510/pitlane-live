// Web Worker around lib/strategySim.js: the optimiser search and the Monte Carlo runs
// stay off the main thread. Messages: { id, type, ... } in, { id, result, ms } out.
//   init      { race }                    the buildSimRace() object, kept for later calls
//   simulate  { code, stints, seed }      -> simulate()
//   best      { code, seed }              -> bestStrategies()
//   gains     { codes }                   -> bestGains()
//   presets   { code, seed }              -> { fastest: bestStrategies(), one, two } (best 1-stop and 2-stop, or null)
import { simulate, bestStrategies, bestGains } from './strategySim'

let race = null

self.onmessage = ({ data }) => {
  const started = performance.now()
  let result = null, error = null
  try {
    if (data.type === 'init') race = data.race
    else if (!race) throw new Error('worker not initialised')
    else if (data.type === 'simulate') result = simulate(race, data.code, data.stints, { seed: data.seed })
    else if (data.type === 'best') result = bestStrategies(race, data.code, { seed: data.seed })
    else if (data.type === 'gains') result = bestGains(race, data.codes)
    else if (data.type === 'presets') {
      const pick = stops => bestStrategies(race, data.code, { seed: data.seed, top: 1, stops })[0] || null
      const fastest = bestStrategies(race, data.code, { seed: data.seed })
      result = { fastest, searched: fastest.searched, one: pick(1), two: pick(2) }
    }
  } catch (e) {
    error = String(e?.message || e)
  }
  self.postMessage({ id: data.id, result, error, ms: performance.now() - started })
}
