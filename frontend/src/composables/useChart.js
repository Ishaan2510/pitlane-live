// Shared plumbing for the Debrief charts (src/components/charts/): sizing, the lap
// axis, Safety Car shading, the hover tooltip, and the driver highlight that every
// chart shares. The Debrief tab provides the shared state under DEBRIEF:
//   { totalLaps, bands, highlight (ref), toggleHighlight(code), isVisible(code),
//     replayLink(lap, driver) }

import { computed, inject, onBeforeUnmount, onMounted, ref } from 'vue'
import { scaleLinear } from 'd3-scale'

export const DEBRIEF = Symbol('debrief')

/**
 * @param margin  { top, right, bottom, left } in px around the plot area
 * @param height  total SVG height in px, or a function of the width
 * @param xDomain optional function returning the x domain; default is laps [0, totalLaps]
 */
export function useChart({ margin, height, xDomain = null }) {
  const debrief = inject(DEBRIEF)

  // ── Sizing: the SVG is as wide as its container ──
  const el = ref(null)
  const width = ref(640)
  let observer = null
  onMounted(() => {
    if (!el.value) return
    width.value = el.value.clientWidth || width.value
    observer = new ResizeObserver(([entry]) => { width.value = Math.round(entry.contentRect.width) || width.value })
    observer.observe(el.value)
  })
  onBeforeUnmount(() => observer?.disconnect())

  const fullHeight = computed(() => (typeof height === 'function' ? height(width.value) : height))
  const innerW = computed(() => Math.max(10, width.value - margin.left - margin.right))
  const innerH = computed(() => Math.max(10, fullHeight.value - margin.top - margin.bottom))

  // ── Axes ──
  const x = computed(() => scaleLinear().domain(xDomain ? xDomain() : [0, debrief.totalLaps]).range([0, innerW.value]))
  // Lap numbers along the bottom: every 5 or 10 laps, fewer on a narrow chart
  const lapTicks = computed(() => {
    const step = innerW.value < 420 ? 10 : debrief.totalLaps > 60 ? 10 : 5
    const ticks = []
    for (let n = step; n <= debrief.totalLaps; n += step) ticks.push(n)
    return ticks
  })
  // Safety Car, VSC and red-flag laps as rectangles on the lap axis (a lap spans n-1..n)
  const shading = computed(() => debrief.bands.filter(b => b.type !== 'yellow').map(b => ({
    type: b.type,
    x: x.value(b.startLap - 1),
    width: Math.max(1, x.value(b.endLap) - x.value(b.startLap - 1)),
  })))

  // ── Hover tooltip ──
  const tip = ref(null)   // { left, top, lines: [] } in px inside the chart element
  function pointer(e) {
    const rect = el.value.getBoundingClientRect()
    return { px: e.clientX - rect.left - margin.left, py: e.clientY - rect.top - margin.top, cx: e.clientX - rect.left, cy: e.clientY - rect.top }
  }
  function showTip(e, lines) {
    const { cx, cy } = pointer(e)
    tip.value = { left: Math.min(cx + 12, width.value - 170), top: cy + 14, lines }
  }
  const hideTip = () => { tip.value = null }

  // ── Driver highlight (shared) and the picked lap (per chart) ──
  const picked = ref(null)   // { driver, lap } -> "Open in replay at lap N"
  function pick(driver, lap = null) {
    const wasOn = debrief.highlight.value === driver
    if (wasOn && (lap == null || picked.value?.lap === lap)) {
      debrief.toggleHighlight(driver)   // second click on the same thing clears it
      picked.value = null
      return
    }
    if (!wasOn) debrief.toggleHighlight(driver)
    picked.value = lap != null ? { driver, lap } : null
  }
  const dimmed = code => !!debrief.highlight.value && debrief.highlight.value !== code
  const isOn = code => debrief.highlight.value === code

  return {
    debrief, el, width, height: fullHeight, innerW, innerH, margin,
    x, lapTicks, shading,
    tip, pointer, showTip, hideTip,
    picked, pick, dimmed, isOn,
  }
}
