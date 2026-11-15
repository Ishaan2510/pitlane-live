<template>
  <ChartFrame
    title="Tyre degradation"
    :caption="caption"
    note="From tyre_model.json: one least-squares fit across the field, lap time = driver pace + fuel × lap + compound offset + deg × tyre age. Only clean laps are used (green all lap, accurate, not deleted, no in or out laps, not lap 1, not the first lap after a restart, within 107% of the driver's median). Each point is a lap with the driver's pace and the fuel effect taken out, so what is left is the tyre. Zero is a new set of the most-used compound. Confidence follows the laps and drivers behind each compound and how tightly the deg rate is known."
    :chart="chart"
    :empty="empty"
  >
    <template v-if="!empty" #controls>
      <ul class="deg-key" aria-label="Degradation rate per compound">
        <li v-for="c in compounds" :key="c.name" :title="c.reason">
          <span class="tyre-key" :class="c.cls"></span>
          <span class="deg-name">{{ c.name }}</span>
          <span class="deg-rate">{{ fmtGap(c.rate, 3) }} s/lap</span>
          <span class="conf-tag" :class="c.confidence">{{ c.confidence }}</span>
          <span class="deg-meta">{{ c.laps }} laps · {{ c.drivers }} drivers{{ c.curved ? ' · curve' : '' }}</span>
        </li>
      </ul>
    </template>

    <svg :viewBox="`0 0 ${chart.width.value} ${chart.height.value}`" :height="chart.height.value" role="img" :aria-label="ariaLabel">
      <defs>
        <clipPath :id="clipId"><rect x="0" y="0" :width="chart.innerW.value" :height="chart.innerH.value" /></clipPath>
      </defs>
      <g :transform="`translate(${M.left},${M.top})`">
        <g v-for="t in yTicks" :key="'y' + t">
          <line class="grid-line" :class="{ zero: t === 0 }" x1="0" :x2="chart.innerW.value" :y1="y(t)" :y2="y(t)" />
          <text class="axis-text" x="-6" :y="y(t)" text-anchor="end" dominant-baseline="central">{{ t === 0 ? '0' : fmtGap(t, 1) }}</text>
        </g>

        <g :clip-path="`url(#${clipId})`">
          <g v-for="c in compounds" :key="c.name">
            <path class="band tyre-dot" :class="c.cls" :d="c.band" />
            <circle v-for="(p, i) in c.points" :key="i" class="pt tyre-dot" :class="c.cls" :cx="chart.x.value(p[0])" :cy="y(p[1])" r="1.6" />
          </g>
          <!-- lines last, so they sit on top of every compound's points -->
          <path v-for="c in compounds" :key="'l' + c.name" class="fit tyre-line" :class="[c.cls, { low: c.confidence === 'low' }]" :d="c.line" />
        </g>

        <g :transform="`translate(0,${chart.innerH.value})`">
          <line class="axis-line" x1="0" :x2="chart.innerW.value" />
          <text v-for="n in xTicks" :key="n" class="axis-text" :x="chart.x.value(n)" y="14" text-anchor="middle">{{ n }}</text>
        </g>
        <text class="axis-text" :x="chart.innerW.value" :y="chart.innerH.value - 5" text-anchor="end">TYRE AGE (LAPS)</text>
        <text class="axis-text" x="-6" y="-8" text-anchor="end">S</text>
      </g>
    </svg>
  </ChartFrame>
</template>

<script setup>
import { computed } from 'vue'
import { scaleLinear } from 'd3-scale'
import { quantile, ticks as niceTicks } from 'd3-array'
import { useChart } from '@/composables/useChart'
import { fmtGap, tyreClass, tyreName } from '@/lib/format'
import { tyreEffect } from '@/lib/tyreModel'
import ChartFrame from './ChartFrame.vue'

const props = defineProps({
  model:   { type: Object, default: null },   // tyre_model.json, null when missing
  weather: { type: Object, default: null },   // weather.json
})

const M = { top: 14, right: 12, bottom: 20, left: 40 }
const ORDER = ['SOFT', 'MEDIUM', 'HARD']
const clipId = 'deg-' + Math.random().toString(36).slice(2, 8)

const fitted = computed(() => (props.model?.modelled ? ORDER.filter(c => props.model.compounds[c]) : []))
const empty = computed(() => {
  if (!props.model) return 'No tyre model has been built for this race yet.'
  if (!props.model.modelled) return `No tyre model for this race: ${props.model.reason}.`
  return ''
})
const maxLife = computed(() => Math.max(5, ...fitted.value.map(c => props.model.compounds[c].max_life_seen)))
const chart = useChart({ margin: M, height: 340, xDomain: () => [0, maxLife.value + 1] })

// y axis: seconds against a new set of the reference compound, slower upwards.
// Trimmed to the middle 98% of the points so one odd lap does not flatten the rest.
const yDomain = computed(() => {
  const values = fitted.value.flatMap(c => props.model.compounds[c].points.map(p => p[1])).sort((a, b) => a - b)
  if (!values.length) return [1, -1]
  const lo = quantile(values, 0.01), hi = quantile(values, 0.99)
  const pad = Math.max(0.2, (hi - lo) * 0.08)
  return [hi + pad, lo - pad]
})
const y = computed(() => scaleLinear().domain(yDomain.value).range([0, chart.innerH.value]))
const yTicks = computed(() => niceTicks(yDomain.value[1], yDomain.value[0], 6))
const xTicks = computed(() => {
  const step = maxLife.value > 40 ? 10 : 5
  const out = []
  for (let n = step; n <= maxLife.value; n += step) out.push(n)
  return out
})

const compounds = computed(() => fitted.value.map(name => {
  const c = props.model.compounds[name]
  const xs = []
  for (let age = 1; age <= c.max_life_seen; age++) xs.push(age)
  const at = age => tyreEffect(c, age)
  const px = age => chart.x.value(age).toFixed(1)
  const upper = xs.map(a => `${px(a)},${y.value(at(a) + c.residual_sd_s).toFixed(1)}`)
  const lower = xs.map(a => `${px(a)},${y.value(at(a) - c.residual_sd_s).toFixed(1)}`).reverse()
  return {
    name: tyreName(name), cls: tyreClass(name),
    rate: c.avg_deg_s_per_lap, confidence: c.confidence, reason: c.confidence_reason,
    laps: c.laps, drivers: c.drivers, curved: c.form === 'quadratic',
    points: c.points,
    line: 'M' + xs.map(a => `${px(a)},${y.value(at(a)).toFixed(1)}`).join('L'),
    band: 'M' + upper.concat(lower).join('L') + 'Z',
  }
}))

const tempRange = computed(() => {
  const col = props.weather?.laps?.columns?.indexOf('track_temp')
  const temps = col >= 0 ? props.weather.laps.rows.map(r => r[col]).filter(Number.isFinite) : []
  return temps.length ? [Math.min(...temps), Math.max(...temps)] : null
})
const caption = computed(() => {
  const m = props.model
  let text = 'Clean laps with driver pace and fuel taken out, against the age of the tyre. Each line is the fitted wear of a compound and the band is where most of its laps fall (one standard deviation either side).'
  if (m?.modelled) {
    text += m.fuel_source === 'prior'
      ? ` Fuel effect: ${Math.abs(m.fuel_s_per_lap).toFixed(3)} s per lap, assumed (this race could not separate fuel from tyres).`
      : ` Fuel effect: ${Math.abs(m.fuel_s_per_lap).toFixed(3)} s per lap, fitted.`
    if (m.wet_running) text += ` Dry-tyre laps from lap ${m.dry_from_lap} only: the track was wet before that.`
  }
  if (tempRange.value) text += ` Track temperature ${tempRange.value[0].toFixed(0)} to ${tempRange.value[1].toFixed(0)} °C.`
  return text
})
const ariaLabel = computed(() => 'Tyre degradation per compound: ' + compounds.value.map(c => `${c.name} ${fmtGap(c.rate, 3)} seconds per lap, ${c.confidence} confidence`).join('; '))
</script>

<style scoped>
.deg-key { display: flex; flex-wrap: wrap; gap: 0.4rem 1.4rem; list-style: none; font-family: 'DM Mono', monospace; font-size: 0.66rem; letter-spacing: 0.06em; color: var(--text-secondary); }
.deg-key li { display: inline-flex; align-items: center; gap: 0.4rem; }
.deg-name { text-transform: uppercase; color: var(--text-primary); letter-spacing: 0.12em; }
.deg-rate { color: var(--text-primary); white-space: nowrap; }
.deg-meta { font-size: 0.6rem; }

.pt { opacity: 0.3; }
.band { opacity: 0.1; stroke: none; }
.fit { fill: none; stroke-width: 2; }
.fit.low { stroke-dasharray: 5 4; }
.grid-line.zero { stroke: var(--border-secondary); }
</style>
