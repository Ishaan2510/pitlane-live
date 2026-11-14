// Static race data built by pipeline/build.py and served from the CDN under /data/.
// File shapes: pipeline/SCHEMA.md.

const BASE = '/data/'
const SESSION_DIR = { R: 'race', Q: 'quali', S: 'sprint', SQ: 'sprint_quali' }

export function dataUrl(path) {
  return BASE + String(path).replace(/^\/+/, '')
}

// One request per file per page load. Failures are not cached, so a retry refetches.
const cache = new Map()

function getJson(path) {
  if (!cache.has(path)) {
    const request = fetch(dataUrl(path)).then(res => {
      // A missing file falls through to the SPA's index.html, so check the type too.
      const isJson = (res.headers.get('content-type') || '').includes('json')
      if (!res.ok || !isJson) throw new Error(`No static data at ${dataUrl(path)}`)
      return res.json()
    })
    request.catch(() => cache.delete(path))
    cache.set(path, request)
  }
  return cache.get(path)
}

export function getManifest() {
  return getJson('manifest.json')
}

export function getReplay(year, round) {
  return getJson(`${year}/${round}/race/replay.json`)
}

// Circuit and weather are optional extras: null when the file is missing.
export function getCircuit(year, round) {
  return getJson(`${year}/${round}/circuit.json`).catch(() => null)
}

export function getWeather(year, round) {
  return getJson(`${year}/${round}/race/weather.json`).catch(() => null)
}

export function getResults(year, round, session = 'R') {
  return getJson(`${year}/${round}/${SESSION_DIR[session] || session}/results.json`)
}

// Races that have a built Race session, newest first (the manifest's own order).
export function getRaces() {
  return getManifest().then(m => m.events.filter(e => e.sessions.includes('R')))
}

// Session coverage tags shown on race cards and in the Race Room header
const COVERAGE = [['R', 'RACE'], ['Q', 'QUALI'], ['S', 'SPRINT']]
export function coverageTags(event) {
  return COVERAGE.filter(([code]) => event.sessions.includes(code)).map(([, label]) => label)
}
