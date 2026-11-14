<template>
  <div v-if="loading" class="debrief" aria-busy="true" aria-label="Loading debrief">
    <div class="cards"><div class="skeleton card-skel" v-for="i in 6" :key="i"></div></div>
    <div class="skeleton-stack"><div class="skeleton" v-for="i in 6" :key="i"></div></div>
  </div>

  <div v-else-if="error" class="debrief">
    <StatePanel label="Debrief unavailable" text="The lap data for this race could not be loaded." action="Retry" @action="load" />
  </div>

  <div v-else class="debrief">
    <p v-if="!results" class="notice">The classification for this race is missing, so drivers are ordered by laps completed and the winner, margin and climber cards are empty.</p>

    <!-- Headline cards -->
    <dl class="cards">
      <div class="card">
        <dt>WINNER</dt>
        <dd>{{ head.winner?.driver || '—' }}</dd>
        <dd class="sub" v-if="head.winner">{{ head.winner.margin != null ? `${fmtGap(head.winner.margin)} s over ${head.winner.runnerUp}` : head.winner.team }}</dd>
      </div>
      <div class="card">
        <dt>BIGGEST CLIMBER</dt>
        <dd>{{ head.climber?.driver || '—' }}</dd>
        <dd class="sub" v-if="head.climber">P{{ head.climber.grid }} to P{{ head.climber.finish }}, up {{ head.climber.gained }}</dd>
        <dd class="sub" v-else>Nobody finished ahead of their grid slot</dd>
      </div>
      <div class="card">
        <dt>MOST LAPS LED</dt>
        <dd>{{ head.mostLed?.driver || '—' }}</dd>
        <dd class="sub" v-if="head.mostLed">{{ head.mostLed.laps }} of {{ head.mostLed.total }} laps</dd>
      </div>
      <div class="card">
        <dt>FASTEST LAP</dt>
        <dd>{{ head.fastest?.driver || '—' }}</dd>
        <dd class="sub" v-if="head.fastest">{{ fmtLapTime(head.fastest.time) }} on lap {{ head.fastest.lap }}</dd>
      </div>
      <div class="card">
        <dt>WINNER'S STOPS</dt>
        <dd>{{ head.winnerStops ?? '—' }}</dd>
        <dd class="sub" v-if="head.winner">{{ winnerTyres }}</dd>
      </div>
      <div class="card">
        <dt>SAFETY CARS</dt>
        <dd>{{ head.safetyCars }}</dd>
        <dd class="sub">{{ head.virtualSafetyCars }} virtual · {{ head.redFlags }} red flag{{ head.redFlags === 1 ? '' : 's' }}</dd>
      </div>
    </dl>

    <!-- Driver filter -->
    <section class="filter" aria-label="Driver filter">
      <div class="filter-top">
        <span class="filter-title">DRIVERS</span>
        <button type="button" class="filter-btn" :class="{ active: preset === 'all' }" @click="showAll">ALL</button>
        <button type="button" class="filter-btn" :class="{ active: preset === 'top10' }" @click="showTop10">TOP 10</button>
        <button v-if="highlight" type="button" class="filter-btn" @click="highlight = null">CLEAR HIGHLIGHT · {{ highlight }}</button>
        <span class="filter-hint">Click a driver in any chart to highlight them everywhere.</span>
      </div>
      <div class="teams">
        <div v-for="team in teams" :key="team.name" class="team">
          <span class="team-name" :style="{ borderColor: team.color }">{{ team.name }}</span>
          <button
            v-for="d in team.drivers"
            :key="d.driver"
            type="button"
            class="chip"
            :class="{ off: !shown.has(d.driver), on: highlight === d.driver }"
            :aria-pressed="shown.has(d.driver)"
            :title="shown.has(d.driver) ? `Hide ${d.driver}` : `Show ${d.driver}`"
            @click="toggleDriver(d.driver)"
          >{{ d.driver }}</button>
        </div>
      </div>
    </section>

    <div class="charts">
      <StrategyChart :drivers="visible" :plan="plan" :laps="laps" />
      <PositionChart :drivers="visible" :series="positions" :count="drivers.length" />
      <GapChart v-model:reference="reference" :drivers="visible" :all-drivers="drivers" :clock="clock" />
      <PaceChart :drivers="visible" :pace="pace" :wet="wet" />
      <PitTable class="wide" :drivers="visible" :table="table" :pit-loss="pitLoss" />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, provide, ref, shallowRef } from 'vue'
import { getReplay, getLaps, getTrackStatus, getPitLoss } from '@/services/data'
import { buildRaceClock } from '@/lib/raceClock'
import { statusBands, pitStops } from '@/lib/raceEvents'
import { driverList, strategy, positionSeries, racePace, hadWetRunning, pitTable, headlines } from '@/lib/debrief'
import { fmtGap, fmtLapTime, tyreName } from '@/lib/format'
import { DEBRIEF } from '@/composables/useChart'
import StatePanel from '@/components/StatePanel.vue'
import StrategyChart from '@/components/charts/StrategyChart.vue'
import PositionChart from '@/components/charts/PositionChart.vue'
import GapChart from '@/components/charts/GapChart.vue'
import PaceChart from '@/components/charts/PaceChart.vue'
import PitTable from '@/components/charts/PitTable.vue'

const props = defineProps({
  year:    { type: Number, required: true },
  round:   { type: Number, required: true },
  event:   { type: Object, default: null },
  results: { type: Array, default: null },
})

const loading = ref(true)
const error   = ref(false)

// Computed once per race, read-only afterwards
const laps      = shallowRef(null)
const clock     = shallowRef(null)
const pitLoss   = shallowRef(null)
const drivers   = shallowRef([])
const plan      = shallowRef({})
const positions = shallowRef({})
const pace      = shallowRef([])
const table     = shallowRef([])
const head      = shallowRef({})
const wet       = ref(false)

// Shared by every chart
const highlight = ref(null)
const shown     = ref(new Set())
const reference = ref(null)     // gap chart: null = the leader
const shared = {
  totalLaps: 0,
  bands: [],
  highlight,
  toggleHighlight: code => { highlight.value = highlight.value === code ? null : code },
  replayLink: (lap, driver) => ({ path: `/race/${props.year}/${props.round}`, query: { lap, ...(driver ? { driver } : {}) } }),
}
provide(DEBRIEF, shared)

async function load() {
  loading.value = true
  error.value = false
  try {
    const [replay, lapData, trackStatus, loss] = await Promise.all([
      getReplay(props.year, props.round),
      getLaps(props.year, props.round),
      getTrackStatus(props.year, props.round),
      getPitLoss(props.year, props.round),
    ])
    const c = buildRaceClock({ laps: lapData, replay, results: props.results, pitLoss: loss })
    const bands = statusBands(trackStatus, c.totalLaps)
    const stops = pitStops(lapData, loss, bands)
    const list = driverList(lapData, props.results)

    shared.totalLaps = c.totalLaps
    shared.bands = bands

    laps.value      = lapData
    clock.value     = c
    pitLoss.value   = loss
    drivers.value   = list
    plan.value      = strategy(lapData)
    positions.value = positionSeries(lapData, list)
    pace.value      = racePace(lapData)
    table.value     = pitTable(stops, loss)
    head.value      = headlines({ laps: lapData, results: props.results, bands, stops })
    wet.value       = hadWetRunning(lapData)
    shown.value     = new Set(list.map(d => d.driver))
  } catch (e) {
    console.error(e)
    error.value = true
  } finally {
    loading.value = false
  }
}
onMounted(load)

// ── Driver filter ──
const visible = computed(() => drivers.value.filter(d => shown.value.has(d.driver)))
const teams = computed(() => {
  const byTeam = new Map()
  for (const d of drivers.value) {
    if (!byTeam.has(d.team)) byTeam.set(d.team, { name: d.team, color: d.color, drivers: [] })
    byTeam.get(d.team).drivers.push(d)
  }
  return [...byTeam.values()]
})
const top10 = computed(() => drivers.value.slice(0, 10).map(d => d.driver))
const preset = computed(() => {
  if (shown.value.size === drivers.value.length) return 'all'
  if (shown.value.size === top10.value.length && top10.value.every(c => shown.value.has(c))) return 'top10'
  return null
})
function showAll()   { shown.value = new Set(drivers.value.map(d => d.driver)) }
function showTop10() { shown.value = new Set(top10.value) }
function toggleDriver(code) {
  const next = new Set(shown.value)
  next.has(code) ? next.delete(code) : next.add(code)
  shown.value = next
}

// "Medium → Hard" for the winner's card
const winnerTyres = computed(() => (plan.value[head.value.winner?.driver] || []).map(s => tyreName(s.compound)).join(' → '))
</script>

<style scoped>
.debrief { max-width: 1500px; margin: 0 auto; padding: 1.25rem 1.5rem 3rem; }
.notice { margin-bottom: 1rem; padding: 0.6rem 0.8rem; border: 1px solid var(--border-secondary); font-size: 0.82rem; color: var(--text-secondary); }

/* ── Headline cards ── */
.cards { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 1px; background: var(--border-primary); border: 1px solid var(--border-primary); margin-bottom: 1.25rem; }
.card { background: var(--bg-primary); padding: 0.8rem 0.9rem; min-width: 0; }
.card dt { font-family: 'DM Mono', monospace; font-size: 0.56rem; letter-spacing: 0.16em; color: var(--text-secondary); }
.card dd { font-family: 'Bebas Neue', sans-serif; font-size: 2.2rem; line-height: 1.1; letter-spacing: 0.04em; color: var(--text-primary); }
.card dd.sub { font-family: 'Work Sans', sans-serif; font-size: 0.74rem; line-height: 1.35; letter-spacing: 0; color: var(--text-secondary); }
.card-skel { height: 96px; }

/* ── Driver filter ── */
.filter { border: 1px solid var(--border-primary); padding: 0.75rem 0.9rem; margin-bottom: 1.25rem; font-family: 'DM Mono', monospace; }
.filter-top { display: flex; flex-wrap: wrap; align-items: center; gap: 0.4rem; margin-bottom: 0.65rem; }
.filter-title { font-size: 0.62rem; letter-spacing: 0.18em; color: var(--text-secondary); margin-right: 0.4rem; }
.filter-hint { margin-left: auto; font-family: 'Work Sans', sans-serif; font-size: 0.74rem; color: var(--text-secondary); }
.filter-btn, .chip {
  background: none;
  border: 1px solid var(--border-secondary);
  color: var(--text-primary);
  font: inherit;
  cursor: pointer;
  transition: border-color var(--dur-fast) var(--ease), color var(--dur-fast) var(--ease), background var(--dur-fast) var(--ease), scale var(--dur-fast) var(--ease);
}
.filter-btn { padding: 0.3rem 0.65rem; font-size: 0.58rem; letter-spacing: 0.14em; }
.filter-btn:hover { border-color: var(--text-primary); }
.filter-btn.active { background: var(--text-primary); color: var(--bg-primary); border-color: var(--text-primary); }

.teams { display: flex; flex-wrap: wrap; gap: 0.5rem 1.1rem; }
.team { display: inline-flex; align-items: center; gap: 0.25rem; }
.team-name { padding-left: 0.4rem; margin-right: 0.2rem; border-left: 3px solid; font-size: 0.56rem; letter-spacing: 0.1em; text-transform: uppercase; color: var(--text-secondary); white-space: nowrap; }
.chip { padding: 0.22rem 0.45rem; font-size: 0.66rem; letter-spacing: 0.05em; }
.chip:hover { border-color: var(--text-primary); }
.chip.off { color: var(--text-secondary); border-style: dashed; text-decoration: line-through; }
.chip.on { border-color: var(--accent); color: var(--accent); }

/* ── Charts ── */
.charts { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1.25rem; align-items: start; }
.charts .wide { grid-column: 1 / -1; }

@media (max-width: 1100px) {
  .cards { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .charts { grid-template-columns: minmax(0, 1fr); }
}
@media (max-width: 720px) {
  .debrief { padding: 1rem 0.75rem 2.5rem; }
  .cards { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .card dd:not(.sub) { font-size: 1.8rem; }
  .filter-hint { margin-left: 0; flex-basis: 100%; }
  .team-name { display: none; }
}
</style>
