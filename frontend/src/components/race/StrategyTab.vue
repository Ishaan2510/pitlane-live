<template>
  <div v-if="loading" class="lab" aria-busy="true" aria-label="Loading the strategy lab">
    <div class="skeleton lab-skel-title"></div>
    <div class="skeleton lab-skel-editor"></div>
    <div class="skeleton-stack"><div class="skeleton" v-for="i in 5" :key="i"></div></div>
  </div>

  <div v-else-if="error" class="lab">
    <StatePanel label="Strategy lab unavailable" text="The lap data for this race could not be loaded." action="Retry" @action="load" />
  </div>

  <div v-else-if="refusal" class="lab">
    <StatePanel label="This race cannot be simulated" :text="refusal" action="Open the debrief" :to="`/race/${year}/${round}/debrief`" />
  </div>

  <div v-else class="lab">
    <!-- 1. The question -->
    <header class="q">
      <h2 class="q-title">WHAT IF <span class="q-driver" :style="{ borderColor: current?.color }">{{ driver }}</span> HAD RUN A DIFFERENT RACE?</h2>
      <div class="q-pick" role="group" aria-label="Driver, in finishing order">
        <button
          v-for="d in drivers"
          :key="d.driver"
          type="button"
          class="drv"
          :class="{ on: d.driver === driver }"
          :style="{ borderLeftColor: d.color }"
          :aria-pressed="d.driver === driver"
          :title="`${d.driver}, ${d.team}${d.finish ? ', P' + d.finish : ''}`"
          @click="pickDriver(d.driver)"
        ><span class="drv-pos">{{ d.finish ? 'P' + d.finish : 'DNF' }}</span>{{ d.driver }}</button>
      </div>
    </header>

    <!-- 2. The editor -->
    <StrategyEditor
      v-model="call"
      :actual="actual"
      :laps="car.laps"
      :compounds="race.compounds"
      :bands="bands"
    />

    <!-- 3. Presets -->
    <div class="presets" role="group" aria-label="Preset strategies">
      <button type="button" class="preset-btn" :disabled="!call.stops.length" @click="shift(-3)">PIT 3 LAPS EARLIER</button>
      <button type="button" class="preset-btn" :disabled="!call.stops.length" @click="shift(3)">PIT 3 LAPS LATER</button>
      <button type="button" class="preset-btn" :disabled="!presets?.one" :title="presetTitle(presets?.one, 'one-stop')" @click="use(presets.one)">ONE STOP</button>
      <button type="button" class="preset-btn" :disabled="!presets?.two" :title="presetTitle(presets?.two, 'two-stop')" @click="use(presets.two)">TWO STOP</button>
      <button type="button" class="preset-btn accent" :disabled="!presets?.fastest?.length" :title="presetTitle(presets?.fastest?.[0], 'model')" @click="use(presets.fastest[0])">MODEL'S FASTEST</button>
      <button type="button" class="preset-btn" :disabled="result?.isActual" @click="reset">RESET</button>
      <span v-if="presets" class="presets-note">{{ presets.searched.toLocaleString('en-GB') }} strategies searched in {{ Math.round(presets.searchMs) }} ms</span>
    </div>

    <!-- 4. The verdict -->
    <VerdictCard :result="result" :driver="driver" :pending="pending" />

    <!-- 5. Charts -->
    <div v-if="result" class="charts">
      <LapLineChart
        class="wide"
        title="Gap to the real race"
        :caption="`${driver}'s race time on your call minus their real race time, lap by lap. Below zero is ahead of where they really were. The band is where 80% of the simulations fall; ticks mark the stops (solid: your call, dashed: real).`"
        note="Cumulative time of the alternative minus cumulative time of the real race at the end of each lap. The line is the model's own value; the band runs from the 10th to the 90th percentile of the Monte Carlo runs at that lap. Laps under Safety Car, VSC or red flag keep their real times."
        :aria-label="`Gap of ${driver}'s alternative race to their real race by lap`"
        :drivers="gapLines"
        :series="gapSeries"
        :y-domain="gapDomain"
        :y-ticks="gapTicks"
        :format="v => (Math.abs(v) < 0.05 ? 'Level with the real race' : `${Math.abs(v).toFixed(1)} s ${v < 0 ? 'ahead of' : 'behind'} the real race`)"
        :height="300"
        :start-labels="false"
        :end-labels="false"
        :pickable="false"
      >
        <template #underlay="{ x, y, innerH }">
          <path class="gap-band" :d="bandPath(x, y)" />
          <line class="gap-zero" :x1="x(0)" :x2="x(race.totalLaps)" :y1="y(0)" :y2="y(0)" />
          <line v-for="n in result.stops.real" :key="'r' + n" class="stop-tick real" :x1="x(n)" :x2="x(n)" y1="0" :y2="innerH" />
          <line v-for="n in result.stops.alt" :key="'a' + n" class="stop-tick alt" :x1="x(n)" :x2="x(n)" y1="0" :y2="innerH" />
        </template>
      </LapLineChart>

      <LapLineChart
        title="Position by lap"
        :caption="`${driver}'s real position (dashed) and on your call (red), with the rest of the field as it raced.`"
        note="The alternative's position at each lap is the real position plus the places gained or lost when the new cumulative time is compared with every other car's real time at the end of the same lap. Nobody else reacts: there is no overtaking model."
        :aria-label="`Position by lap: ${driver} real and alternative against the field`"
        :drivers="posLines"
        :series="posSeries"
        :y-domain="[0.5, drivers.length + 0.5]"
        :y-ticks="posTicks"
        :format="p => 'P' + p"
        :height="Math.max(240, drivers.length * 13 + 30)"
        :start-labels="false"
        :end-labels="false"
        :pickable="false"
      />

      <LapLineChart
        title="Lap times"
        :caption="`${driver}'s real laps (dashed) and on your call (solid), coloured by the tyre on the car. Pit laps and Safety Car laps run off the top.`"
        note="Each alternative lap is the real lap minus the model's time for the tyres really on the car plus the model's time for the tyres on your call. Where the two lines sit on top of each other the tyres are the same as in the real race."
        :aria-label="`Lap times by lap: ${driver} real and alternative, by compound`"
        :drivers="timeLines"
        :series="timeSeries"
        :y-domain="timeDomain"
        :y-ticks="timeTicks"
        :format="v => fmtLapTime(v)"
        :height="Math.max(240, drivers.length * 13 + 30) - 26"
        :start-labels="false"
        :end-labels="false"
        :pickable="false"
      >
        <template #controls>
          <div class="tyre-legend" aria-label="Tyre colours">
            <span v-for="c in race.compounds" :key="c"><span class="tyre-key" :class="tyreClass(c)"></span> {{ tyreName(c) }}</span>
          </div>
        </template>
      </LapLineChart>
    </div>

    <!-- 6. Assumptions: always on the page -->
    <section class="assume" aria-label="Assumptions">
      <h3 class="assume-title">WHAT THIS ASSUMES</h3>
      <dl class="assume-list">
        <div>
          <dt>The field</dt>
          <dd>Every other car is held exactly as it raced. Only {{ driver }}'s lap times change, and nobody reacts to them.</dd>
        </div>
        <div>
          <dt>Overtaking and traffic</dt>
          <dd>
            Not modelled: no time is added for being stuck behind a car or for passing one.
            <template v-if="result">
              <strong>Traffic risk:</strong> {{ lapsWord(result.traffic.laps) }} within 1.0 s behind a slower car<template v-if="!result.isActual"> ({{ result.traffic.realLaps }} in the real race)</template><template v-if="result.traffic.cars.length">: {{ result.traffic.cars.map(c => `${c.driver} for ${c.laps}`).join(', ') }}</template>.
              <span v-for="r in result.traffic.rejoins" :key="r.lap" class="assume-line">After the stop on lap {{ r.lap }}: {{ rejoinText(r.cars) }}.</span>
              <span v-if="!result.isActual" class="assume-line">At the flag: {{ rejoinText(result.traffic.atFlag) }}.</span>
            </template>
          </dd>
        </div>
        <div>
          <dt>Pit loss</dt>
          <dd>
            {{ race.pit.green.toFixed(1) }} s for a green-flag stop<template v-if="race.pit.source === 'race'">, the median of this race's {{ race.pit.greenStops }} green-flag stops</template><template v-else>, a default figure: this race has no measured green-flag stop</template>.
            Under the Safety Car: {{ race.pit.sc != null ? race.pit.sc.toFixed(1) + ' s' : 'not measured here, the green figure is used' }}.
            Under the VSC: {{ race.pit.vsc != null ? race.pit.vsc.toFixed(1) + ' s' : 'not measured here, the green figure is used' }}.
            A tyre change during a red flag is free. A stop left where it really was keeps what it really cost.
          </dd>
        </div>
        <div>
          <dt>Tyres</dt>
          <dd>
            <span v-for="c in race.compounds" :key="c" class="assume-tyre" :title="race.model.compounds[c].confidence_reason">
              <span class="tyre-key" :class="tyreClass(c)"></span> {{ tyreName(c) }} {{ fmtGap(race.model.compounds[c].avg_deg_s_per_lap, 3) }} s per lap of age
              <span class="conf-tag" :class="race.model.compounds[c].confidence">{{ race.model.compounds[c].confidence }}</span>
            </span>
            <span class="assume-line">Fitted on this race's clean laps. Oldest tyre seen: {{ race.compounds.map(c => `${tyreName(c).toLowerCase()} ${race.model.compounds[c].max_life_seen} laps`).join(', ') }}; a longer stint is a guess.</span>
          </dd>
        </div>
        <div>
          <dt>Safety Car, VSC and red flag</dt>
          <dd>Laps under them keep their real times whatever the tyres. A fixed field cannot close up behind a Safety Car, so a call that leaves the real race before one is marked low confidence: the seconds it gains or loses before the field bunches would not have survived.</dd>
        </div>
        <div>
          <dt>The range</dt>
          <dd>{{ runs }} simulations, seed {{ seed }}. Each draws the tyre numbers from their standard errors, new stops from this race's real stops, lap-to-lap scatter, and the model's measured error on a stint it has not seen ({{ (race.model.stintSd / 1.25).toFixed(1) }} s on average in this race).</dd>
        </div>
      </dl>
      <router-link to="/about/strategy-model" class="assume-link">HOW THIS WORKS, AND HOW WRONG IT CAN BE →</router-link>
    </section>

    <!-- 7. Share -->
    <div class="share">
      <button type="button" class="share-btn" @click="copy('link')">{{ copied === 'link' ? 'COPIED' : 'COPY LINK' }}</button>
      <button type="button" class="share-btn" :disabled="!result" @click="copy('result')">{{ copied === 'result' ? 'COPIED' : 'COPY RESULT' }}</button>
      <span class="share-text" aria-live="polite">{{ resultText }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, provide, ref, shallowRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ticks as niceTicks, quantile } from 'd3-array'
import { getReplay, getLaps, getTrackStatus, getPitLoss, getTyreModel } from '@/services/data'
import { buildRaceClock } from '@/lib/raceClock'
import { statusBands } from '@/lib/raceEvents'
import { driverList } from '@/lib/debrief'
import { notSimulable } from '@/lib/tyreModel'
import { buildSimRace, actualStints, makeStints, parseStrategy, formatStrategy, SIM_RUNS } from '@/lib/strategySim'
import { fmtGap, fmtLapTime, tyreClass, tyreName } from '@/lib/format'
import { DEBRIEF } from '@/composables/useChart'
import StatePanel from '@/components/StatePanel.vue'
import LapLineChart from '@/components/charts/LapLineChart.vue'
import StrategyEditor from '@/components/strategy/StrategyEditor.vue'
import VerdictCard from '@/components/strategy/VerdictCard.vue'

const props = defineProps({
  year:    { type: Number, required: true },
  round:   { type: Number, required: true },
  event:   { type: Object, default: null },
  results: { type: Array, default: null },
})

const route = useRoute(), router = useRouter()
const runs = SIM_RUNS
const DEBOUNCE_MS = 90

const loading = ref(true)
const error   = ref(false)
const refusal = ref(null)          // why this race cannot be simulated

// Built once per race
const race    = shallowRef(null)   // buildSimRace()
const bands   = shallowRef([])
const drivers = shallowRef([])     // driverList(), finishing order, only cars that can be simulated

// The scenario: it all lives in the URL (?d=HAM&s=M-18-H-41-S&seed=1)
const driver = ref(null)
const call   = ref({ compounds: [], stops: [] })
const seed   = ref(1)

const result  = shallowRef(null)   // simulate()
const presets = shallowRef(null)   // { fastest, one, two, searched, searchMs, ms }
const pending = ref(false)

const shared = { totalLaps: 0, bands: [], highlight: ref(null), toggleHighlight: () => {}, replayLink: lap => ({ path: `/race/${props.year}/${props.round}`, query: { lap } }) }
provide(DEBRIEF, shared)

const car     = computed(() => race.value.cars[driver.value])
const current = computed(() => drivers.value.find(d => d.driver === driver.value))
const actual  = computed(() => actualStints(race.value, driver.value))
const toCall  = stints => ({ compounds: stints.map(s => s.compound), stops: stints.slice(0, -1).map(s => s.end) })

// ── The worker: the search and the Monte Carlo runs stay off the main thread ──
let worker = null, nextId = 0
const waiting = new Map()
function ask(type, payload = {}) {
  return new Promise((resolve, reject) => {
    const id = ++nextId
    waiting.set(id, { resolve, reject })
    worker.postMessage({ id, type, ...payload })
  })
}
function startWorker(simRace) {
  worker?.terminate()
  worker = new Worker(new URL('../../lib/strategyWorker.js', import.meta.url), { type: 'module' })
  worker.onmessage = ({ data }) => {
    const w = waiting.get(data.id)
    waiting.delete(data.id)
    if (w) data.error ? w.reject(new Error(data.error)) : w.resolve(data)
  }
  return ask('init', { race: simRace })
}
onBeforeUnmount(() => worker?.terminate())

// ── Loading ──
async function load() {
  loading.value = true
  error.value = false
  refusal.value = null
  try {
    const [replay, laps, trackStatus, pitLoss, model] = await Promise.all([
      getReplay(props.year, props.round),
      getLaps(props.year, props.round),
      getTrackStatus(props.year, props.round),
      getPitLoss(props.year, props.round),
      getTyreModel(props.year, props.round),
    ])
    refusal.value = notSimulable(model)
    if (refusal.value) return
    const clock = buildRaceClock({ laps, replay, results: props.results, pitLoss })
    const sim = buildSimRace({ laps, clock, model, pitLoss, results: props.results })
    await startWorker(sim)

    shared.totalLaps = sim.totalLaps
    shared.bands = bands.value = statusBands(trackStatus, sim.totalLaps)
    race.value = sim
    drivers.value = driverList(laps, props.results).filter(d => sim.cars[d.driver]?.laps >= 6)

    // The scenario from the URL, or somewhere interesting to start
    const wanted = String(route.query.d || '').toUpperCase()
    seed.value = parseInt(route.query.seed, 10) > 0 ? parseInt(route.query.seed, 10) : 1
    if (drivers.value.some(d => d.driver === wanted)) {
      driver.value = wanted
      call.value = fromQuery(route.query.s) || toCall(actual.value)
    } else {
      // the driver the model finds the most time for among the top ten (a result it trusts, if there is one)
      const top = drivers.value.slice(0, 10).map(d => d.driver)
      const gains = (await ask('gains', { codes: top })).result
      const ranked = top.filter(c => gains[c]).sort((a, b) => gains[a].delta - gains[b].delta)
      driver.value = ranked.find(c => gains[c].confidence !== 'low' && gains[c].delta < -0.5) || ranked[0] || drivers.value[0].driver
      const best = parseStrategy(gains[driver.value]?.strategy)
      call.value = best ? best : toCall(actual.value)
    }
    loadPresets()
  } catch (e) {
    console.error(e)
    error.value = true
  } finally {
    loading.value = false
  }
}
onMounted(load)

// A strategy from the URL, if it is one this driver could run
function fromQuery(text) {
  const parsed = parseStrategy(text)
  if (!parsed) return null
  const N = car.value.laps
  const ordered = parsed.stops.every((lap, i) => lap >= 1 && lap < N && (i === 0 || lap > parsed.stops[i - 1]))
  return ordered ? parsed : null
}

async function loadPresets() {
  presets.value = null
  const code = driver.value
  const { result: r, ms } = await ask('presets', { code, seed: seed.value })
  if (code === driver.value) presets.value = { ...r, ms }
}

// ── Simulating: debounced, newest request wins ──
let timer = null, latest = 0
watch([driver, call, seed], () => {
  if (!race.value || !driver.value) return
  pending.value = true
  clearTimeout(timer)
  timer = setTimeout(async () => {
    const mine = ++latest
    const stints = makeStints(race.value, driver.value, call.value.compounds, call.value.stops).map(s => ({ ...s }))
    const query = { d: driver.value, s: formatStrategy(stints), seed: String(seed.value) }
    if (['d', 's', 'seed'].some(k => route.query[k] !== query[k])) router.replace({ query })
    try {
      const { result: r } = await ask('simulate', { code: driver.value, stints, seed: seed.value })
      if (mine === latest) { result.value = r; pending.value = false }
    } catch (e) {
      console.error(e)
      if (mine === latest) pending.value = false
    }
  }, DEBOUNCE_MS)
}, { deep: true })
onBeforeUnmount(() => clearTimeout(timer))

// ── Driver and presets ──
function pickDriver(code) {
  if (code === driver.value) return
  result.value = null
  driver.value = code
  call.value = toCall(actualStints(race.value, code))
  loadPresets()
}
function reset() { call.value = toCall(actual.value) }
function use(entry) { if (entry) call.value = toCall(entry.stints) }
function shift(by) {
  const N = car.value.laps
  const stops = call.value.stops.map(lap => Math.min(N - 2, Math.max(3, lap + by)))
  for (let i = 1; i < stops.length; i++) if (stops[i] <= stops[i - 1]) stops[i] = stops[i - 1] + 1   // keep them in order
  if (stops.length && stops[stops.length - 1] >= N) return
  call.value = { compounds: call.value.compounds, stops }
}
function presetTitle(entry, kind) {
  if (!presets.value) return 'Searching…'
  if (!entry) return `No ${kind} strategy stays within the tyre ages seen in this race`
  return `${entry.strategy}: ${fmtGap(entry.time.p50, 1)} s against the real race`
}

// ── Chart data ──
const withStart = values => [0, ...Array.from(values).slice(1)]
const gapLines = [{ driver: 'call', label: 'YOUR CALL', color: 'var(--accent)', cls: 'strong' }]
const gapSeries = computed(() => ({ call: withStart(result.value.gap) }))
const gapDomain = computed(() => {
  const r = result.value
  let lo = -1, hi = 1
  for (let n = 1; n <= r.laps; n++) { lo = Math.min(lo, r.band.p10[n], r.gap[n]); hi = Math.max(hi, r.band.p90[n], r.gap[n]) }
  const pad = (hi - lo) * 0.08
  return [hi + pad, lo - pad]                 // behind the real race at the top, ahead at the bottom
})
const gapTicks = computed(() => niceTicks(gapDomain.value[1], gapDomain.value[0], 6).map(v => ({ value: v, label: v === 0 ? '0' : fmtGap(v, 0) })))
function bandPath(x, y) {
  const r = result.value, up = [], down = []
  for (let n = 0; n <= r.laps; n++) {
    up.push(`${x(n).toFixed(1)},${y(n ? r.band.p90[n] : 0).toFixed(1)}`)
    down.push(`${x(n).toFixed(1)},${y(n ? r.band.p10[n] : 0).toFixed(1)}`)
  }
  return 'M' + up.concat(down.reverse()).join('L') + 'Z'
}

const posLines = computed(() => [
  ...drivers.value.filter(d => d.driver !== driver.value).map(d => ({ driver: d.driver, color: 'var(--text-secondary)', cls: 'faint' })),
  { driver: driver.value, label: `${driver.value} real`, color: current.value.color, cls: 'dashed strong' },
  { driver: 'call', label: `${driver.value} your call`, color: 'var(--accent)', cls: 'strong' },
])
const posSeries = computed(() => {
  const out = {}
  for (const d of drivers.value) out[d.driver] = [d.grid, ...race.value.cars[d.driver].pos.slice(1).map(p => p || null)]
  out[driver.value] = [current.value.grid, ...result.value.position.real.slice(1)]
  out.call = [current.value.grid, ...result.value.position.alt.slice(1)]
  return out
})
const posTicks = computed(() => drivers.value.map((_, i) => ({ value: i + 1, label: (i + 1) % 5 === 0 || i === 0 ? 'P' + (i + 1) : '' })))

// Lap times, one line per stint so each can take its compound's colour
const tyreColor = c => (c === 'SOFT' ? 'var(--tyre-soft)' : c === 'MEDIUM' ? 'var(--tyre-medium-line)' : c === 'HARD' ? 'var(--tyre-hard-line)' : 'var(--text-muted)')
function segments(compounds, times, kind) {
  const lines = [], series = {}
  let start = 1
  for (let n = 2; n <= compounds.length; n++) {
    if (n < compounds.length && compounds[n] === compounds[start] && !(kind.stops.includes(n - 1))) continue
    const id = `${kind.id}${start}`
    lines.push({ driver: id, label: `${kind.label} · ${tyreName(compounds[start])}`, color: tyreColor(compounds[start]), cls: kind.cls })
    series[id] = Array.from({ length: compounds.length }, (_, lap) => (lap >= start && lap < n ? times[lap] : null))
    start = n
  }
  return { lines, series }
}
const timeParts = computed(() => {
  const r = result.value
  const real = segments(r.compound.real, r.lapTime.real, { id: 'r', label: 'Real', cls: 'dashed', stops: r.stops.real })
  const alt = segments(r.compound.alt, r.lapTime.alt, { id: 'a', label: 'Your call', cls: 'strong', stops: r.stops.alt })
  return { lines: [...real.lines, ...alt.lines], series: { ...real.series, ...alt.series } }
})
const timeLines = computed(() => timeParts.value.lines)
const timeSeries = computed(() => timeParts.value.series)
const timeDomain = computed(() => {
  const r = result.value
  const values = [...Array.from(r.lapTime.real).slice(2), ...Array.from(r.lapTime.alt).slice(2)].filter(Number.isFinite).sort((a, b) => a - b)
  const lo = quantile(values, 0.02), hi = quantile(values, 0.85)        // pit and Safety Car laps sit above this
  return [hi + 1.5, lo - 0.5]                                           // slower at the top
})
const timeTicks = computed(() => niceTicks(timeDomain.value[1], timeDomain.value[0], 5).map(v => ({ value: v, label: fmtLapTime(v).slice(0, -2) })))

// ── Words ──
const lapsWord = n => `${n} lap${n === 1 ? '' : 's'}`
const rejoinText = cars => (cars.length ? cars.map(c => `${c.gap.toFixed(1)} s behind ${c.driver}`).join(', ') : 'clear air, nobody within 1.5 s ahead')

const shareUrl = () => `${window.location.host}${route.path}?d=${driver.value}&s=${result.value.strategy}&seed=${seed.value}`
const resultText = computed(() => {
  const r = result.value
  if (!r || r.isActual) return ''
  const stops = r.stops.alt
  const pitted = !stops.length ? 'not pitted at all'
    : `pitted on lap ${stops.length > 1 ? stops.slice(0, -1).join(', ') + ' and ' + stops[stops.length - 1] : stops[0]}`
  const where = `${props.year} ${(props.event?.name || '').replace('Grand Prix', 'GP')}`
  const f = r.finish
  const place = f.alt === f.real ? `Still P${f.real}` : `P${f.alt} instead of P${f.real}`
  const range = f.p10 === f.p90 ? `P${f.p10}` : `P${f.p10} to P${f.p90}`
  return `What if ${driver.value} had ${pitted} at the ${where}? ${place} (range ${range}${r.confidence.level === 'low' ? ', low confidence' : ''}). ${shareUrl()}`
})

const copied = ref(null)
async function copy(what) {
  try {
    await navigator.clipboard.writeText(what === 'link' ? window.location.href : resultText.value || window.location.href)
    copied.value = what
    setTimeout(() => { copied.value = null }, 2000)
  } catch { /* clipboard blocked: the link is in the address bar and the text is on the page */ }
}
</script>

<style scoped>
.lab { max-width: 1280px; margin: 0 auto; padding: 1.25rem 1.5rem 3rem; display: grid; grid-template-columns: minmax(0, 1fr); gap: 1.1rem; }
.lab-skel-title { height: 3rem; width: min(30rem, 90%); }
.lab-skel-editor { height: 150px; }

/* ── 1. The question ── */
.q-title { font-family: 'Bebas Neue', sans-serif; font-weight: 400; font-size: clamp(1.9rem, 4.4vw, 3rem); line-height: 1; letter-spacing: 0.03em; color: var(--text-primary); }
.q-driver { padding: 0 0.3rem; border-bottom: 4px solid var(--border-secondary); }      /* team colour set inline */
.q-pick { display: flex; flex-wrap: wrap; gap: 0.3rem; margin-top: 0.8rem; }
.drv {
  display: inline-flex;
  align-items: baseline;
  gap: 0.35rem;
  padding: 0.28rem 0.5rem 0.28rem 0.45rem;
  background: none;
  border: 1px solid var(--border-secondary);
  border-left: 3px solid var(--border-secondary);       /* team colour set inline */
  color: var(--text-primary);
  font-family: 'DM Mono', monospace;
  font-size: 0.68rem;
  letter-spacing: 0.06em;
  cursor: pointer;
  transition: background var(--dur-fast) var(--ease), color var(--dur-fast) var(--ease), scale var(--dur-fast) var(--ease);
}
.drv-pos { font-size: 0.54rem; color: var(--text-secondary); }
.drv:hover { background: var(--bg-hover); }
.drv.on { background: var(--text-primary); color: var(--bg-primary); }
.drv.on .drv-pos { color: var(--bg-primary); }

/* ── 3. Presets ── */
.presets { display: flex; flex-wrap: wrap; align-items: center; gap: 0.35rem; }
.preset-btn, .share-btn {
  padding: 0.42rem 0.75rem;
  background: none;
  border: 1px solid var(--border-secondary);
  color: var(--text-primary);
  font-family: 'DM Mono', monospace;
  font-size: 0.58rem;
  letter-spacing: 0.14em;
  cursor: pointer;
  transition: border-color var(--dur-fast) var(--ease), color var(--dur-fast) var(--ease), scale var(--dur-fast) var(--ease);
}
.preset-btn:hover:not(:disabled), .share-btn:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
.preset-btn:disabled, .share-btn:disabled { opacity: 0.35; cursor: default; }
.preset-btn.accent { border-color: var(--accent); color: var(--accent-hover); }
.presets-note { margin-left: 0.4rem; font-family: 'DM Mono', monospace; font-size: 0.56rem; letter-spacing: 0.08em; color: var(--text-secondary); }

/* ── 5. Charts ── */
.charts { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1.1rem; align-items: start; }
.charts .wide { grid-column: 1 / -1; }
.charts :deep(.gap-band) { fill: color-mix(in srgb, var(--accent) 16%, transparent); }
.charts :deep(.gap-zero) { stroke: var(--text-secondary); stroke-width: 1; }
.charts :deep(.stop-tick) { stroke-width: 1; }
.charts :deep(.stop-tick.real) { stroke: var(--text-secondary); stroke-dasharray: 3 3; }
.charts :deep(.stop-tick.alt) { stroke: var(--accent); }

/* ── 6. Assumptions ── */
.assume { border: 1px solid var(--border-primary); padding: 1rem 1.1rem; }
.assume-title { font-family: 'Bebas Neue', sans-serif; font-weight: 400; font-size: 1.35rem; letter-spacing: 0.05em; color: var(--text-primary); }
.assume-list { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.9rem 2rem; margin-top: 0.7rem; }
.assume-list dt { font-family: 'DM Mono', monospace; font-size: 0.58rem; letter-spacing: 0.16em; text-transform: uppercase; color: var(--text-secondary); }
.assume-list dd { margin-top: 0.2rem; font-family: 'Work Sans', sans-serif; font-size: 0.82rem; line-height: 1.5; color: var(--text-primary); }
.assume-list strong { font-weight: 600; }
.assume-line { display: block; margin-top: 0.2rem; color: var(--text-secondary); }
.assume-tyre { display: inline-flex; align-items: center; gap: 0.35rem; margin-right: 0.9rem; white-space: nowrap; }
.assume-link { display: inline-block; margin-top: 0.9rem; font-family: 'DM Mono', monospace; font-size: 0.62rem; letter-spacing: 0.14em; color: var(--accent-hover); text-decoration: none; }
.assume-link:hover { text-decoration: underline; }

/* ── 7. Share ── */
.share { display: flex; flex-wrap: wrap; align-items: center; gap: 0.35rem 0.6rem; }
.share-text { flex: 1 1 20rem; font-family: 'Work Sans', sans-serif; font-size: 0.78rem; line-height: 1.4; color: var(--text-secondary); overflow-wrap: anywhere; }

@media (max-width: 1000px) {
  .charts { grid-template-columns: minmax(0, 1fr); }
  .assume-list { grid-template-columns: minmax(0, 1fr); }
}
@media (max-width: 720px) {
  .lab { padding: 1rem 0.75rem 2.5rem; }
  .q-pick { flex-wrap: nowrap; overflow-x: auto; padding-bottom: 0.3rem; }
  .drv { flex: none; }
  .presets-note { flex-basis: 100%; margin-left: 0; }
  .assume-tyre { white-space: normal; }
}
</style>
