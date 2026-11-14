// Small display formatters shared by the Race Room.

// 83.456 -> "1:23.456"
export function fmtLapTime(s) {
  if (!Number.isFinite(s)) return '—'
  const m = Math.floor(s / 60)
  return `${m}:${(s - m * 60).toFixed(3).padStart(6, '0')}`
}

// 12.3456 -> "+12.346", 0 -> "+0.000"; pass digits for a shorter form
export function fmtGap(s, digits = 3) {
  if (!Number.isFinite(s)) return '—'
  return `${s < 0 ? '−' : '+'}${Math.abs(s).toFixed(digits)}`
}

// CSS class for a compound: 'soft' ... 'wet', or 'unknown'
export function tyreClass(compound) {
  return compound ? String(compound).toLowerCase() : 'unknown'
}

export const TYRE_LEGEND = [
  ['soft', 'Soft'], ['medium', 'Medium'], ['hard', 'Hard'], ['intermediate', 'Inter'], ['wet', 'Wet'],
]

// 'INTERMEDIATE' -> 'Inter', null -> '?'
export function tyreName(compound) {
  if (!compound) return '?'
  return compound === 'INTERMEDIATE' ? 'Inter' : compound[0] + compound.slice(1).toLowerCase()
}
