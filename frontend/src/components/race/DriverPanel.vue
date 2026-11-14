<template>
  <div class="driver-panel" :class="{ compare: views.length === 2 }">
    <div class="dp-top">
      <span class="dp-title">{{ views.length === 2 ? 'COMPARE' : 'DRIVER' }}</span>
      <button type="button" class="dp-close" aria-label="Close driver panel" @click="$emit('close')">
        <svg viewBox="0 0 12 12" aria-hidden="true"><path d="M2.5 2.5l7 7M9.5 2.5l-7 7" /></svg>
      </button>
    </div>

    <p v-if="!views.length" class="dp-empty">
      Select a driver in the timing tower or on the map. Shift-click, or use the pin, to compare a second driver.
    </p>

    <template v-else>
      <div class="dp-cols">
        <section v-for="v in views" :key="v.code" class="dp-col">
          <header class="dp-head" :style="{ borderColor: v.color }">
            <span class="dp-code">{{ v.code }}</span>
            <span class="dp-pos">{{ v.car.retired ? 'OUT' : 'P' + v.car.position }}</span>
            <span class="dp-team">{{ v.team }}</span>
          </header>

          <dl class="dp-stats">
            <div><dt>Gap</dt><dd>{{ gapText(v.car) }}</dd></div>
            <div><dt>Interval</dt><dd>{{ v.car.position === 1 || v.car.retired ? '—' : fmtGap(v.car.interval) }}</dd></div>
            <div>
              <dt>Tyre</dt>
              <dd :title="v.car.compound || 'Unknown compound'"><span class="tyre-key" :class="tyreClass(v.car.compound)"></span> <template v-if="views.length === 1">{{ tyreName(v.car.compound) }} · </template>{{ v.car.tyreAge || '—' }} L</dd>
            </div>
            <div><dt>Status</dt><dd>{{ v.car.retired ? 'Retired' : v.car.finished ? 'Finished' : v.car.inPit ? 'In pit' : 'Lap ' + v.car.lap }}</dd></div>
            <div><dt>Last lap</dt><dd>{{ fmtLapTime(v.last) }}</dd></div>
            <div><dt>Best</dt><dd>{{ fmtLapTime(v.best) }}</dd></div>
          </dl>

          <div class="dp-label">STINTS</div>
          <div class="dp-stints" role="img" :aria-label="stintLabel(v)">
            <span
              v-for="s in v.stints"
              :key="s.startLap"
              class="tyre-fill"
              :class="tyreClass(s.compound)"
              :style="{ left: pct(s.startLap - 1), width: pct(s.shownEnd - s.startLap + 1) }"
              :title="`${tyreName(s.compound)} · laps ${s.startLap}–${s.shownEnd}`"
            ></span>
          </div>
        </section>
      </div>

      <div v-if="views.length === 2" class="dp-delta">
        <span>LAST LAP</span>
        <strong>{{ deltaText }}</strong>
      </div>

      <div class="dp-label">LAP TIMES <span v-if="views.length === 2" class="dp-legend">
        <i :style="{ background: views[0].color }"></i>{{ views[0].code }}
        <i class="dash" :style="{ borderColor: views[1].color }"></i>{{ views[1].code }}
      </span></div>
      <svg class="dp-spark" :viewBox="`0 0 ${W} ${H}`" role="img" :aria-label="`Lap times so far for ${views.map(v => v.code).join(' and ')}`">
        <line class="spark-now" :x1="x(nowLap)" :x2="x(nowLap)" y1="0" :y2="H" />
        <template v-for="(v, i) in views" :key="v.code">
          <path class="spark-line" :class="{ second: i === 1 }" :d="spark.paths[i]" :style="{ stroke: v.color }" />
          <circle v-if="spark.dots[i]" class="spark-dot" :cx="spark.dots[i][0]" :cy="spark.dots[i][1]" r="2.5" :style="{ fill: v.color }" />
        </template>
      </svg>
      <div class="dp-spark-axis"><span>LAP 1</span><span>{{ fmtLapTime(spark.min) }} – {{ fmtLapTime(spark.max) }}</span><span>{{ clock.totalLaps }}</span></div>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { scaleLinear } from 'd3-scale'
import { line } from 'd3-shape'
import { quantile } from 'd3-array'
import { stints } from '@/lib/raceEvents'
import { fmtGap, fmtLapTime, tyreClass, tyreName } from '@/lib/format'

const props = defineProps({
  clock:   { type: Object, required: true },      // buildRaceClock()
  cars:    { type: Array, default: () => [] },    // clock.stateAt() at the current time
  driver:  { type: String, default: null },
  compare: { type: String, default: null },
})
defineEmits(['close'])

const W = 280, H = 56

// What is known about a driver at the current moment of the replay
function view(code) {
  const car = props.cars.find(c => c.driver === code)
  const d = props.clock.byCode[code]
  if (!car || !d) return null
  const completed = car.finished || car.retired ? d.done : car.lap - 1
  let best = NaN
  for (let n = 1; n <= completed; n++) {
    const t = d.data.time[n]
    if (Number.isFinite(t) && !d.data.deleted[n] && !(t >= best)) best = t
  }
  const shownLap = Math.min(car.lap, d.data.laps)
  return {
    code, car, d, completed,
    team: d.team, color: d.color,
    last: completed >= 1 ? d.data.time[completed] : NaN,
    best,
    // stints up to the lap the car is on, not the ones still to come
    stints: stints(d.data).filter(s => s.startLap <= shownLap).map(s => ({ ...s, shownEnd: Math.min(s.endLap, shownLap) })),
  }
}

const views = computed(() => [props.driver, props.compare].filter((c, i, all) => c && all.indexOf(c) === i).map(view).filter(Boolean))
const nowLap = computed(() => (views.value[0] ? views.value[0].car.lap : 1))

const pct = laps => `${(laps / props.clock.totalLaps) * 100}%`
const x = lap => (lap - 1) / Math.max(1, props.clock.totalLaps - 1) * W

function gapText(car) {
  if (car.retired) return '—'
  if (car.position === 1) return 'Leader'
  return car.lapsDown >= 1 ? `+${car.lapsDown} lap${car.lapsDown > 1 ? 's' : ''}` : fmtGap(car.gap)
}
const stintLabel = v => 'Stints: ' + v.stints.map(s => `${tyreName(s.compound)} laps ${s.startLap} to ${s.shownEnd}`).join(', ')

const deltaText = computed(() => {
  const [a, b] = views.value
  if (!Number.isFinite(a.last) || !Number.isFinite(b.last)) return '—'
  const delta = a.last - b.last
  return `${a.code} ${fmtGap(delta)} vs ${b.code}`
})

// Lap-time sparkline: laps completed so far, y clipped so one slow lap (pit stop,
// Safety Car) does not flatten the rest
const spark = computed(() => {
  const series = views.value.map(v => {
    const pts = []
    for (let n = 1; n <= v.completed; n++) if (Number.isFinite(v.d.data.time[n])) pts.push([n, v.d.data.time[n]])
    return pts
  })
  const all = series.flat().map(p => p[1]).sort((a, b) => a - b)
  const min = all[0] ?? 0
  const max = all.length ? Math.max(min + 1, quantile(all, 0.9) * 1.02) : 1
  const y = scaleLinear().domain([min, max]).range([H - 4, 4]).clamp(true)
  const path = line().x(p => x(p[0])).y(p => y(p[1]))
  return {
    min, max,
    paths: series.map(pts => path(pts) || ''),
    dots: series.map(pts => (pts.length ? [x(pts[pts.length - 1][0]), y(pts[pts.length - 1][1])] : null)),
  }
})
</script>

<style scoped>
.driver-panel { padding: 0.6rem 0.75rem 0.75rem; font-family: 'DM Mono', monospace; }

.dp-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem; }
.dp-title, .dp-label { font-size: 0.62rem; letter-spacing: 0.18em; color: var(--text-secondary); text-transform: uppercase; }
.dp-close { display: none; width: 32px; height: 32px; background: none; border: 1px solid var(--border-secondary); color: var(--text-primary); cursor: pointer; align-items: center; justify-content: center; }
.dp-close svg { width: 12px; height: 12px; fill: none; stroke: currentColor; stroke-width: 1.4; stroke-linecap: round; }

.dp-empty { font-family: 'Work Sans', sans-serif; font-size: 0.8rem; line-height: 1.5; color: var(--text-secondary); padding: 0.5rem 0 0.25rem; }

.dp-cols { display: grid; grid-template-columns: 1fr; gap: 0.75rem; }
.compare .dp-cols { grid-template-columns: 1fr 1fr; }
.dp-col { min-width: 0; }

.dp-head { display: grid; grid-template-columns: auto 1fr; align-items: baseline; column-gap: 0.5rem; padding-left: 0.5rem; border-left: 3px solid var(--border-secondary); margin-bottom: 0.5rem; }
.dp-code { font-family: 'Bebas Neue', sans-serif; font-size: 1.7rem; line-height: 1; letter-spacing: 0.05em; color: var(--text-primary); }
.dp-pos  { font-family: 'Bebas Neue', sans-serif; font-size: 1.2rem; line-height: 1; color: var(--accent); text-align: right; }
.dp-team { grid-column: 1 / -1; font-size: 0.58rem; letter-spacing: 0.1em; text-transform: uppercase; color: var(--text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.dp-stats { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1px; background: var(--border-primary); border: 1px solid var(--border-primary); margin-bottom: 0.6rem; }
.compare .dp-stats { grid-template-columns: 1fr; }
.dp-stats div { background: var(--bg-primary); padding: 0.3rem 0.45rem; min-width: 0; }
.compare .dp-stats div { display: flex; justify-content: space-between; align-items: baseline; gap: 0.4rem; }
.dp-stats dt { font-size: 0.52rem; letter-spacing: 0.14em; text-transform: uppercase; color: var(--text-secondary); }
.dp-stats dd { font-size: 0.76rem; color: var(--text-primary); white-space: nowrap; font-variant-numeric: tabular-nums; }

.dp-label { display: flex; align-items: center; justify-content: space-between; margin: 0.2rem 0 0.3rem; }
.dp-stints { position: relative; height: 10px; background: var(--bg-secondary); border: 1px solid var(--border-primary); }
.dp-stints span { position: absolute; top: 0; bottom: 0; border-right: 1px solid var(--bg-primary); }

.dp-delta { display: flex; justify-content: space-between; align-items: baseline; margin-top: 0.6rem; padding: 0.4rem 0.5rem; border: 1px solid var(--border-primary); font-size: 0.58rem; letter-spacing: 0.14em; color: var(--text-secondary); }
.dp-delta strong { font-size: 0.78rem; font-weight: 500; letter-spacing: 0.02em; color: var(--text-primary); }

.dp-label { margin-top: 0.7rem; }
.dp-legend { display: inline-flex; align-items: center; gap: 0.3rem; letter-spacing: 0.08em; }
.dp-legend i { display: inline-block; width: 12px; height: 2px; margin-left: 0.4rem; }
.dp-legend i.dash { height: 0; border-top: 2px dashed; background: none; }
.dp-spark { display: block; width: 100%; height: auto; border: 1px solid var(--border-primary); background: var(--bg-secondary); }
.spark-line { fill: none; stroke-width: 1.5; vector-effect: non-scaling-stroke; }
.spark-line.second { stroke-dasharray: 4 3; }
.spark-now { stroke: var(--border-secondary); stroke-width: 1; vector-effect: non-scaling-stroke; }
.dp-spark-axis { display: flex; justify-content: space-between; margin-top: 0.2rem; font-size: 0.55rem; letter-spacing: 0.08em; color: var(--text-secondary); }
</style>
