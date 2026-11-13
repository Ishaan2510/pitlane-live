// /api/schedule, shared so the intro and Home use one request between them.
import { apiUrl } from '@/services/apiBase'

const TTL_MS = 5 * 60 * 1000   // race status (live / upcoming) goes stale, so do not keep it for ever
const cache = new Map()

export function getSchedule(year) {
  const hit = cache.get(year)
  if (hit && Date.now() - hit.at < TTL_MS) return hit.request

  const request = fetch(apiUrl(`/schedule?year=${year}`)).then(res => res.json())
  request.catch(() => cache.delete(year))
  cache.set(year, { at: Date.now(), request })
  return request
}
