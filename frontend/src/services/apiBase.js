const rawBase = import.meta.env.VITE_API_URL || ''

function normalizeBase(value) {
  return value.replace(/\/+$/, '')
}

const base = rawBase ? normalizeBase(rawBase) : ''

export const API_ROOT = base ? `${base}/api` : '/api'

export function apiUrl(path) {
  if (!path.startsWith('/')) return `${API_ROOT}/${path}`
  return `${API_ROOT}${path}`
}
