// Web Worker around lib/strategySim.js: the optimiser search and the Monte Carlo runs
// stay off the main thread. Messages: { id, type, ... } in, { id, result, ms } out.
//   init      { race }                    the buildSimRace() object, kept for later calls
//   simulate  { code, stints, seed }      -> simulate()
//   best      { code, seed }              -> bestStrategies()
//   gains     { codes }                   -> bestGains()
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
  } catch (e) {
    error = String(e?.message || e)
  }
  self.postMessage({ id: data.id, result, error, ms: performance.now() - started })
}
