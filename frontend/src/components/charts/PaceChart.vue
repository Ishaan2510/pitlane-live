<template>
  <ChartFrame
    title="Race pace"
    :caption="caption"
    note="Clean laps only: green flag for the whole lap, is_accurate, not an in-lap or out-lap, not lap 1. The box runs from the first to the third quartile with the median marked; the whiskers reach the furthest laps within 1.5 times the box width. Drivers are sorted by median, and the number on the right is the gap to the fastest median with the count of laps used."
    :chart="chart"
    :empty="rows.length ? '' : 'No clean laps to compare for the selected drivers.'"
  >
    <svg :viewBox="`0 0 ${chart.width.value} ${chart.height.value}`" :height="chart.height.value" role="img" aria-label="Lap-time distribution of clean laps per driver">
      <g :transform="`translate(${M.left},${M.top})`">
        <g v-for="t in ticks" :key="t">
          <line class="grid-line" :x1="chart.x.value(t)" :x2="chart.x.value(t)" y1="0" :y2="chart.innerH.value" />
          <text class="axis-text" :x="chart.x.value(t)" :y="chart.innerH.value + 14" text-anchor="middle">{{ fmtLapTime(t).slice(0, -2) }}</text>
        </g>

        <g
          v-for="(r, i) in rows"
          :key="r.driver"
          class="pace-row fade"
          :class="{ dim: chart.dimmed(r.driver) }"
          @pointermove="e => chart.showTip(e, tipLines(r))"
          @click="chart.pick(r.driver)"
        >
          <rect class="hit" :x="-M.left" :y="i * ROW" :width="chart.width.value" :height="ROW" />
          <text class="driver-label" x="-8" :y="i * ROW + ROW / 2" text-anchor="end" dominant-baseline="central">{{ r.driver }}</text>
          <line class="whisker" :x1="chart.x.value(r.low)" :x2="chart.x.value(r.high)" :y1="i * ROW + ROW / 2" :y2="i * ROW + ROW / 2" />
          <rect class="box" :x="chart.x.value(r.q1)" :y="i * ROW + 4" :width="Math.max(1, chart.x.value(r.q3) - chart.x.value(r.q1))" :height="ROW - 8" :style="{ fill: r.color }" />
          <line class="median" :x1="chart.x.value(r.median)" :x2="chart.x.value(r.median)" :y1="i * ROW + 2" :y2="i * ROW + ROW - 2" />
          <text class="axis-text" :x="chart.innerW.value + 6" :y="i * ROW + ROW / 2" dominant-baseline="central">{{ i === 0 ? 'FASTEST' : fmtGap(r.delta) }} · {{ r.n }}</text>
        </g>
      </g>
    </svg>
  </ChartFrame>
</template>

<script setup>
import { computed } from 'vue'
import { ticks as niceTicks } from 'd3-array'
import { useChart } from '@/composables/useChart'
import { fmtGap, fmtLapTime } from '@/lib/format'
import ChartFrame from './ChartFrame.vue'

const props = defineProps({
  drivers: { type: Array, required: true },    // the drivers to draw (for colour and filter)
  pace:    { type: Array, required: true },    // racePace(), sorted by median
  wet:     { type: Boolean, default: false },  // someone ran intermediates or wets
})

const ROW = 20
const M = { top: 4, right: 92, bottom: 20, left: 40 }

const rows = computed(() => {
  const meta = Object.fromEntries(props.drivers.map(d => [d.driver, d]))
  return props.pace.filter(p => meta[p.driver]).map(p => ({ ...p, color: meta[p.driver].color }))
})
const domain = computed(() => {
  if (!rows.value.length) return [0, 1]
  const lo = Math.min(...rows.value.map(r => r.low)), hi = Math.max(...rows.value.map(r => r.high))
  const pad = Math.max(0.2, (hi - lo) * 0.04)
  return [lo - pad, hi + pad]
})
const chart = useChart({ margin: M, height: () => rows.value.length * ROW + M.top + M.bottom, xDomain: () => domain.value })
const ticks = computed(() => niceTicks(domain.value[0], domain.value[1], chart.innerW.value < 420 ? 3 : 6))

const caption = computed(() => {
  const base = 'How fast each driver was on clean laps: the box is the middle half of their laps, the line through it the median. Left is faster.'
  return props.wet
    ? base + ' This race had running on intermediate or wet tyres, so laps from different track conditions are mixed: read the boxes with care.'
    : base
})

function tipLines(r) {
  return [
    `${r.driver} · ${r.n} clean lap${r.n > 1 ? 's' : ''}`,
    `Median ${fmtLapTime(r.median)}`,
    `Middle half ${fmtLapTime(r.q1)} – ${fmtLapTime(r.q3)}`,
    `Range ${fmtLapTime(r.low)} – ${fmtLapTime(r.high)}`,
    r.delta ? `${fmtGap(r.delta)} s to the fastest median` : 'Fastest median',
  ]
}
</script>

<style scoped>
.pace-row { cursor: pointer; }
.hit { fill: transparent; }
.whisker { stroke: var(--text-secondary); stroke-width: 1; }
.box { stroke: var(--border-secondary); stroke-width: 1; }
.median { stroke: var(--text-primary); stroke-width: 2; }
</style>
