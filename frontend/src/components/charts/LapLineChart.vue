<template>
  <!-- One line per driver against the lap number. Used by the position chart and the
       gap chart: they differ only in their y values and how those are labelled. -->
  <ChartFrame :title="title" :caption="caption" :note="note" :chart="chart" :empty="lines.length ? '' : 'No drivers selected.'">
    <template v-if="$slots.controls" #controls><slot name="controls" /></template>

    <svg
      :viewBox="`0 0 ${chart.width.value} ${chart.height.value}`"
      :height="chart.height.value"
      role="img"
      :aria-label="ariaLabel"
      @pointermove="onMove"
      @click="onClick"
    >
      <defs>
        <clipPath :id="clipId"><rect x="0" y="-2" :width="chart.innerW.value" :height="chart.innerH.value + 4" /></clipPath>
      </defs>
      <g :transform="`translate(${M.left},${M.top})`">
        <rect v-for="(s, i) in chart.shading.value" :key="'sh' + i" class="shade" :class="s.type" :x="s.x" y="0" :width="s.width" :height="chart.innerH.value" />

        <g v-for="t in yTicks" :key="'y' + t.value">
          <line class="grid-line" x1="0" :x2="chart.innerW.value" :y1="y(t.value)" :y2="y(t.value)" />
          <text v-if="t.label" class="axis-text" x="-6" :y="y(t.value)" text-anchor="end" dominant-baseline="central">{{ t.label }}</text>
        </g>

        <g :clip-path="`url(#${clipId})`">
          <!-- drawn under the lines, in the chart's own scales (bands, markers) -->
          <slot name="underlay" :x="chart.x.value" :y="y" :inner-w="chart.innerW.value" :inner-h="chart.innerH.value" />
          <path
            v-for="l in lines"
            :key="l.driver"
            class="line fade"
            :class="[l.cls, { dim: chart.dimmed(l.driver), on: chart.isOn(l.driver), second: l.second }]"
            :d="l.d"
            :style="{ stroke: l.color }"
          />
          <circle v-if="hover" class="hover-dot" :cx="hover.cx" :cy="hover.cy" r="3.5" :style="{ fill: hover.color }" />
        </g>

        <!-- Driver codes at both ends -->
        <template v-for="l in (endLabels ? lines : [])" :key="'lb' + l.driver">
          <text v-if="startLabels && l.startY != null" class="driver-label fade" :class="{ dim: chart.dimmed(l.driver) }" x="-6" :y="l.startY" text-anchor="end" dominant-baseline="central" @click.stop="chart.pick(l.driver)">{{ l.driver }}</text>
          <text v-if="l.endY != null" class="driver-label fade" :class="{ dim: chart.dimmed(l.driver) }" :x="l.endX + 6" :y="l.endY" dominant-baseline="central" @click.stop="chart.pick(l.driver)">{{ l.driver }}</text>
        </template>

        <g :transform="`translate(0,${chart.innerH.value})`">
          <line class="axis-line" x1="0" :x2="chart.innerW.value" />
          <text v-for="n in chart.lapTicks.value" :key="n" class="axis-text" :x="chart.x.value(n)" y="14" text-anchor="middle">{{ n }}</text>
          <text class="axis-text" x="0" y="14">LAP</text>
        </g>
      </g>
    </svg>
  </ChartFrame>
</template>

<script setup>
import { computed, ref } from 'vue'
import { scaleLinear } from 'd3-scale'
import { line } from 'd3-shape'
import { useChart } from '@/composables/useChart'
import ChartFrame from './ChartFrame.vue'

const props = defineProps({
  title:     { type: String, required: true },
  caption:   { type: String, required: true },
  note:      { type: String, required: true },
  ariaLabel: { type: String, required: true },
  drivers:   { type: Array, required: true },      // driverList() entries to draw
  series:    { type: Object, required: true },     // driver -> values by lap (index 0 = start); null = gap in the line
  yDomain:   { type: Array, required: true },      // [top value, bottom value]
  yTicks:    { type: Array, default: () => [] },   // [{ value, label }]
  format:    { type: Function, required: true },   // value -> text for the tooltip
  height:    { type: Number, default: 420 },
  startLabels: { type: Boolean, default: true },   // driver codes at the left end too (off when the y axis is labelled there)
  endLabels:   { type: Boolean, default: true },   // driver codes at the line ends at all
  pickable:    { type: Boolean, default: true },   // a click highlights the driver and offers "open in replay"
})
// A `drivers` entry may also carry `cls` (extra classes for its line: 'faint', 'strong',
// 'dashed') and `label` (the name shown in the tooltip instead of the driver code).

const M = { top: 8, right: 34, bottom: 20, left: 34 }
const chart = useChart({ margin: M, height: () => props.height })
const clipId = 'clip-' + Math.random().toString(36).slice(2, 8)

const y = computed(() => scaleLinear().domain(props.yDomain).range([0, chart.innerH.value]))
const clampY = v => Math.min(chart.innerH.value, Math.max(0, y.value(v)))
const inDomain = v => v >= Math.min(...props.yDomain) && v <= Math.max(...props.yDomain)

// Nudge labels apart (min 10 px) keeping their order
function spread(items, key) {
  const sorted = items.filter(i => i[key] != null).sort((a, b) => a[key] - b[key])
  for (let i = 1; i < sorted.length; i++) if (sorted[i][key] - sorted[i - 1][key] < 10) sorted[i][key] = sorted[i - 1][key] + 10
}

const lines = computed(() => {
  const path = line().defined(p => p[1] != null).x(p => chart.x.value(p[0])).y(p => y.value(p[1]))
  const out = props.drivers.map(d => {
    const values = props.series[d.driver] || []
    const pts = values.map((v, lap) => [lap, v])
    const known = pts.filter(p => p[1] != null)
    const first = known[0], last = known[known.length - 1]
    return {
      driver: d.driver, color: d.color, second: d.second, cls: d.cls, label: d.label || d.driver, values,
      d: path(pts) || '',
      startY: first && first[0] === 0 ? clampY(first[1]) : null,
      endY: last && inDomain(last[1]) ? y.value(last[1]) : null,   // no label for a line that left the chart
      endX: last ? chart.x.value(last[0]) : 0,
    }
  })
  spread(out, 'startY')
  // only labels that end at the same lap can collide
  const byEnd = {}
  for (const l of out) (byEnd[Math.round(l.endX)] ||= []).push(l)
  Object.values(byEnd).forEach(group => spread(group, 'endY'))
  return out
})

// The line nearest the pointer at the lap under it
const hover = ref(null)
function nearest(e) {
  const { px, py } = chart.pointer(e)
  const lap = Math.round(chart.x.value.invert(px))
  if (lap < 0 || lap > chart.debrief.totalLaps) return null
  let best = null
  for (const l of lines.value) {
    const v = l.values[lap]
    if (v == null) continue
    const dist = Math.abs(y.value(v) - py)
    if (!best || dist < best.dist) best = { dist, driver: l.driver, label: l.label, color: l.color, lap, value: v }
  }
  return best && best.dist < 24 ? best : null
}
function onMove(e) {
  const n = nearest(e)
  if (!n) { hover.value = null; chart.hideTip(); return }
  hover.value = { cx: chart.x.value(n.lap), cy: y.value(n.value), color: n.color }
  chart.showTip(e, [`${n.label} · ${n.lap === 0 ? 'START' : 'LAP ' + n.lap}`, props.format(n.value, n)])
}
function onClick(e) {
  const n = props.pickable && nearest(e)
  if (n) chart.pick(n.driver, Math.max(1, n.lap))
}
</script>

<style scoped>
.line { fill: none; stroke-width: 1.5; stroke-linejoin: round; }
.line.second { stroke-dasharray: 5 3; }
.line.on { stroke-width: 3; }
.line.faint { stroke-width: 1; opacity: 0.28; }
.line.strong { stroke-width: 2.5; }
.line.dashed { stroke-dasharray: 4 3; }
.hover-dot { stroke: var(--bg-primary); stroke-width: 1.5; pointer-events: none; }
svg { cursor: crosshair; }
</style>
