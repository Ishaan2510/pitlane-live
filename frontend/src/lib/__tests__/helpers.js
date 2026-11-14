// Loads a real race folder from public/data for the lib tests.
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { parseLaps } from '../laps'

const DATA = fileURLToPath(new URL('../../../public/data/', import.meta.url))
const read = path => JSON.parse(readFileSync(DATA + path, 'utf8'))

export function loadRace(year, round) {
  const dir = `${year}/${round}/race/`
  const rawLaps = read(dir + 'laps.json')
  return {
    year, round,
    rawLaps,
    laps:        parseLaps(rawLaps),
    replay:      read(dir + 'replay.json'),
    results:     read(dir + 'results.json'),
    trackStatus: read(dir + 'track_status.json'),
    pitLoss:     read(dir + 'pit_loss.json'),
  }
}

export const manifest = () => read('manifest.json')
