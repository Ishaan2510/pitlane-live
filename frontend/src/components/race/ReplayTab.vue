<template>
  <div v-if="loading" class="tab-pad" aria-busy="true" aria-label="Loading replay">
    <div class="skeleton-stack"><div class="skeleton" v-for="i in 8" :key="i"></div></div>
  </div>

  <div v-else-if="error" class="tab-pad">
    <StatePanel label="Replay unavailable" text="The lap data for this race could not be loaded." action="Retry" @action="load" />
  </div>

  <div v-else class="workspace" :class="{ 'sheet-open': sheetOpen }">
    <!-- Timing tower -->
    <section class="ws-tower" aria-label="Timing tower">
      <TimingTower :cars="view.cars" :grid="grid" :selected="selected" :pinned="pinned" @select="select" @pin="pin" />
    </section>

    <!-- Track map -->
    <section class="ws-map" aria-label="Track map">
      <TrackCanvas ref="canvas" :circuitData="circuit" :selectedDriver="selected" :pinnedDriver="pinned" @select-driver="onMapSelect" />
      <p v-if="!circuit" class="map-note">No track outline for this race: cars are shown on a plain oval.</p>
    </section>

    <!-- Selected driver, weather, events -->
    <aside class="ws-side">
      <div class="ws-panel">
        <DriverPanel :clock="clock" :cars="view.cars" :driver="selected" :compare="pinned" @close="closeSheet" />
      </div>
      <EventsFeed class="ws-feed" :events="events" :playhead="view.playhead" @seek="seek" />
    </aside>

    <!-- Playback controls and timeline -->
    <section class="ws-bottom" aria-label="Playback">
      <div class="controls">
        <button type="button" class="control-btn" aria-label="Back one lap" title="Back one lap (←)" :disabled="view.playhead <= 0" @click="stepLap(-1)">
          <svg viewBox="0 0 12 12" aria-hidden="true"><path d="M2.5 2v8M10 2 4.5 6 10 10z" /></svg>
        </button>
        <button type="button" class="control-btn primary" :aria-label="playing ? 'Pause' : 'Play'" :title="playing ? 'Pause (space)' : 'Play (space)'" @click="toggle">
          <svg v-if="playing" viewBox="0 0 12 12" aria-hidden="true"><path d="M3 2h2v8H3zM7 2h2v8H7z" /></svg>
          <svg v-else viewBox="0 0 12 12" aria-hidden="true"><path d="M3 1.5 10 6 3 10.5z" /></svg>
        </button>
        <button type="button" class="control-btn" aria-label="Forward one lap" title="Forward one lap (→)" :disabled="view.playhead >= clock.totalLaps" @click="stepLap(1)">
          <svg viewBox="0 0 12 12" aria-hidden="true"><path d="M9.5 2v8M2 2l5.5 4L2 10z" /></svg>
        </button>

        <div class="speed" role="group" aria-label="Playback speed, seconds per lap">
          <span class="speed-label">SEC / LAP</span>
          <button
            v-for="(s, i) in SPEEDS"
            :key="s"
            type="button"
            class="control-btn"
            :class="{ active: speedIndex === i }"
            :aria-pressed="speedIndex === i"
            :title="`One lap every ${s} seconds ([ and ] change speed)`"
            @click="speedIndex = i"
          >{{ s }}</button>
        </div>

        <span class="keys-hint">SPACE play · ← → lap · [ ] speed</span>
      </div>

      <RaceTimeline
        :totalLaps="clock.totalLaps"
        :playhead="view.playhead"
        :bands="bands"
        :pitTicks="pitTicks"
        :selectedDriver="selected"
        :pinnedDriver="pinned"
        @seek="seek"
        @scrub-start="onScrubStart"
        @scrub-end="onScrubEnd"
      />
    </section>

    <!-- Weather at the leader's lap -->
    <section v-if="lapWeather" class="ws-weather" aria-label="Weather">
      <WeatherPanel :weather="lapWeather" />
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getReplay, getLaps, getCircuit, getWeather, getTrackStatus, getPitLoss } from '@/services/data'
import { buildRaceClock } from '@/lib/raceClock'
import { statusBands, pitStops, raceEvents } from '@/lib/raceEvents'
import StatePanel from '@/components/StatePanel.vue'
import TrackCanvas from '@/components/TrackCanvas.vue'
import WeatherPanel from '@/components/WeatherPanel.vue'
import TimingTower from './TimingTower.vue'
import DriverPanel from './DriverPanel.vue'
import EventsFeed from './EventsFeed.vue'
import RaceTimeline from './RaceTimeline.vue'

const props = defineProps({
  year:    { type: Number, required: true },
  round:   { type: Number, required: true },
  event:   { type: Object, default: null },
  results: { type: Array, default: null },
})

const SPEEDS = [15, 5, 2]      // seconds of playback per lap of the leader
const UI_INTERVAL_MS = 100     // the map redraws every frame; the tower and panels at 10 Hz

const route = useRoute()

const loading = ref(true)
const error   = ref(false)

// Big, read-only objects: kept out of Vue's deep reactivity
const clock    = shallowRef(null)
const circuit  = shallowRef(null)
const weather  = shallowRef(null)
const bands    = shallowRef([])
const events   = shallowRef([])
const pitTicks = shallowRef([])
const grid     = shallowRef({})

const canvas     = ref(null)
const playing    = ref(false)
const speedIndex = ref(1)
const selected   = ref(null)
const pinned     = ref(null)
const sheetOpen  = ref(false)   // the driver panel as a bottom sheet (small screens)

// What the tower, panels and timeline show: replaced at most every UI_INTERVAL_MS
const view = shallowRef({ playhead: 0, cars: [] })

let playhead = 0               // leader laps; the source of truth, advanced every frame
let frameId = null
let lastFrame = 0
let lastUi = 0

async function load() {
  loading.value = true
  error.value = false
  pause()
  try {
    const [replay, laps, circuitData, weatherData, trackStatus, pitLoss] = await Promise.all([
      getReplay(props.year, props.round),
      getLaps(props.year, props.round),
      getCircuit(props.year, props.round),
      getWeather(props.year, props.round),
      getTrackStatus(props.year, props.round),
      getPitLoss(props.year, props.round),
    ])
    const c = buildRaceClock({ laps, replay, results: props.results, pitLoss })
    const b = statusBands(trackStatus, c.totalLaps)
    const stops = pitStops(laps, pitLoss, b)
    const ev = raceEvents({ clock: c, laps, results: props.results, bands: b, stops })

    clock.value    = c
    circuit.value  = circuitData?.points?.length ? circuitData : null
    weather.value  = weatherData
    bands.value    = b
    events.value   = ev
    pitTicks.value = ev.filter(e => e.type === 'pit')
    grid.value     = Object.fromEntries(c.drivers.filter(d => d.grid < 99).map(d => [d.driver, d.grid]))

    // ?lap=23&driver=VER, from "Open in replay" in the debrief
    const lap = parseInt(route.query.lap, 10)
    playhead = Number.isFinite(lap) ? Math.min(c.totalLaps, Math.max(0, lap - 1)) : 0
    const wanted = String(route.query.driver || '')
    selected.value = c.byCode[wanted] ? wanted : null
    pinned.value = null
  } catch (e) {
    console.error(e)
    error.value = true
  } finally {
    loading.value = false
  }
  if (!error.value) {
    await nextTick()   // the canvas exists now
    render(true)
  }
}

// Push the current moment to the map, and (throttled) to everything reactive
function render(force = false) {
  const c = clock.value
  if (!c) return
  const cars = c.stateAt(c.timeAt(playhead))
  canvas.value?.setCars(cars)
  const now = performance.now()
  if (force || now - lastUi >= UI_INTERVAL_MS) {
    lastUi = now
    view.value = { playhead, cars }
  }
}

function frame(ts) {
  const dt = Math.min(ts - lastFrame, 250)   // a long frame must not jump the race forward
  lastFrame = ts
  playhead += dt / 1000 / SPEEDS[speedIndex.value]
  if (playhead >= clock.value.totalLaps) {
    playhead = clock.value.totalLaps
    pause()
    render(true)
    return
  }
  render()
  frameId = requestAnimationFrame(frame)
}

function play() {
  if (playing.value || !clock.value) return
  if (playhead >= clock.value.totalLaps) playhead = 0   // play again from the start
  playing.value = true
  lastFrame = performance.now()
  frameId = requestAnimationFrame(frame)
}
function pause() {
  playing.value = false
  if (frameId) cancelAnimationFrame(frameId)
  frameId = null
  render(true)
}
const toggle = () => (playing.value ? pause() : play())

function seek(p) {
  playhead = Math.min(clock.value.totalLaps, Math.max(0, p))
  render(true)
}
function stepLap(direction) {
  // to the start of the next lap, or back to the start of this one (then the one before)
  seek(direction > 0 ? Math.floor(playhead + 1e-6) + 1 : Math.ceil(playhead - 1e-6) - 1)
}
function stepSpeed(direction) {
  speedIndex.value = Math.min(SPEEDS.length - 1, Math.max(0, speedIndex.value + direction))
}

// Dragging the timeline pauses playback and resumes it on release
let resumeAfterScrub = false
function onScrubStart() { resumeAfterScrub = playing.value; pause() }
function onScrubEnd()   { if (resumeAfterScrub) play() }

// ── Driver selection ──
function select(code) {
  if (selected.value === code) { selected.value = null; sheetOpen.value = false; return }
  if (pinned.value === code) pinned.value = null
  selected.value = code
  sheetOpen.value = true
}
function pin(code) {
  if (!selected.value) return select(code)
  if (code === selected.value) return
  pinned.value = pinned.value === code ? null : code
  sheetOpen.value = true
}
function onMapSelect(code, opts) {
  if (!code) return               // a click on empty track keeps the selection
  opts?.pin ? pin(code) : select(code)
}
function closeSheet() { sheetOpen.value = false }

// ── Keyboard: space, arrows, [ and ] ──
function onKeydown(e) {
  if (!clock.value || e.ctrlKey || e.metaKey || e.altKey) return
  const tag = e.target?.tagName
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || e.target?.isContentEditable) return
  if (e.key === ' ') {
    if (tag === 'BUTTON' || tag === 'A') return   // space already activates the focused control
    e.preventDefault()
    toggle()
  } else if (e.key === 'ArrowLeft')  { e.preventDefault(); stepLap(-1) }
  else if (e.key === 'ArrowRight')   { e.preventDefault(); stepLap(1) }
  else if (e.key === '[')            stepSpeed(-1)
  else if (e.key === ']')            stepSpeed(1)
  else if (e.key === 'Escape')       closeSheet()
}
function onVisibility() {
  if (document.hidden) pause()
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
  document.addEventListener('visibilitychange', onVisibility)
  load()
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  document.removeEventListener('visibilitychange', onVisibility)
  if (frameId) cancelAnimationFrame(frameId)
})
// The results arrive with the Race Room header; rebuild if they change under us
watch(() => props.results, (now, before) => { if (now !== before && !loading.value) load() })

// ── Weather at the leader's current lap ──
const lapWeather = computed(() => {
  const w = weather.value
  if (!w) return null
  const rows = w.laps?.rows
  if (!rows?.length) return w.summary || null
  const lap = Math.min(clock.value.totalLaps, Math.floor(view.value.playhead) + 1)
  const row = rows.find(r => r[0] === lap) || rows[Math.min(rows.length, lap) - 1]
  const at = Object.fromEntries(w.laps.columns.map((name, i) => [name, row[i]]))
  return { ...w.summary, ...at }   // wind is only in the summary
})
</script>

<style scoped>
.tab-pad { max-width: 900px; margin: 0 auto; padding: 3rem 1.5rem; }

.workspace {
  display: grid;
  grid-template-columns: 290px minmax(0, 1fr) 320px;
  grid-template-rows: clamp(430px, calc(100vh - 392px), 720px) auto;
  border-bottom: 1px solid var(--border-primary);
}
.ws-tower  { grid-area: 1 / 1; min-height: 0; display: flex; flex-direction: column; border-right: 1px solid var(--border-primary); }
.ws-tower > * { flex: 1; }
.ws-map    { grid-area: 1 / 2; min-height: 0; min-width: 0; position: relative; }
.ws-side   { grid-area: 1 / 3; min-height: 0; display: flex; flex-direction: column; border-left: 1px solid var(--border-primary); overflow-y: auto; }
.ws-bottom  { grid-area: 2 / 1 / 3 / 3; min-width: 0; border-top: 1px solid var(--border-primary); }
.ws-weather { grid-area: 2 / 3; border-top: 1px solid var(--border-primary); border-left: 1px solid var(--border-primary); }
.ws-weather :deep(.weather-panel) { margin: 0; border: none; background: none; padding: 0.7rem 0.75rem; }

.ws-panel   { border-bottom: 1px solid var(--border-primary); }
.ws-feed    { flex: 1 0 170px; }

.map-note {
  position: absolute;
  left: 10px;
  bottom: 10px;
  font-family: 'DM Mono', monospace;
  font-size: 0.6rem;
  letter-spacing: 0.08em;
  color: #999;   /* on the map, which is dark in both themes */
}

/* ── Controls ── */
.controls { display: flex; align-items: center; gap: 0.35rem; padding: 0.6rem 1rem 0; flex-wrap: wrap; }
.control-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 36px;
  height: 32px;
  padding: 0 0.6rem;
  background: none;
  border: 1px solid var(--border-secondary);
  color: var(--text-primary);
  font-family: 'DM Mono', monospace;
  font-size: 0.7rem;
  cursor: pointer;
  transition: border-color var(--dur-fast) var(--ease), background var(--dur-fast) var(--ease), color var(--dur-fast) var(--ease), scale var(--dur-fast) var(--ease);
}
.control-btn svg { width: 12px; height: 12px; fill: currentColor; stroke: currentColor; stroke-width: 1.2; stroke-linejoin: round; stroke-linecap: round; }
.control-btn:hover:not(:disabled) { border-color: var(--text-primary); }
.control-btn:disabled { opacity: 0.3; cursor: not-allowed; }
.control-btn.primary,
.control-btn.active { background: var(--text-primary); color: var(--bg-primary); border-color: var(--text-primary); }
.control-btn.primary { min-width: 52px; }

.speed { display: inline-flex; align-items: center; margin-left: 0.75rem; }
.speed .control-btn + .control-btn { border-left: none; }
.speed-label, .keys-hint { font-family: 'DM Mono', monospace; font-size: 0.58rem; letter-spacing: 0.14em; color: var(--text-secondary); }
.speed-label { margin-right: 0.5rem; }
.keys-hint { margin-left: auto; text-transform: uppercase; }

/* ── Mid widths: narrower side columns ── */
@media (max-width: 1280px) {
  .workspace { grid-template-columns: 270px minmax(0, 1fr) 290px; }
}

/* ── Small screens: map, timeline, tower, then the rest; driver panel is a bottom sheet ── */
@media (max-width: 900px) {
  .workspace { display: flex; flex-direction: column; }
  .ws-map    { order: 1; height: min(56vh, 420px); }
  .ws-bottom { order: 2; border-bottom: 1px solid var(--border-primary); }
  .ws-tower  { order: 3; border-right: none; }
  .ws-side   { order: 4; border-left: none; overflow: visible; }
  .ws-weather { order: 5; border-left: none; }
  .ws-feed   { flex: none; max-height: 320px; }
  .keys-hint { display: none; }

  .ws-panel {
    position: fixed;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 10001;            /* above the soundtrack dock, so the sheet is always usable */
    max-height: 72vh;
    overflow-y: auto;
    background: var(--bg-card);
    border-top: 1px solid var(--border-secondary);
    border-bottom: none;
    transform: translateY(100%);
    visibility: hidden;
    transition: transform var(--dur-slow) var(--ease), visibility 0s var(--dur-slow);
  }
  .sheet-open .ws-panel { transform: none; visibility: visible; transition-delay: 0s; }
  .ws-panel :deep(.dp-close) { display: flex; }
}
</style>
