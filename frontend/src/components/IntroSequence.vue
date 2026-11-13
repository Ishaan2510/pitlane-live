<template>
  <!-- Decorative: hidden from assistive tech, focus is never moved here. -->
  <div v-if="visible" class="intro" :class="'is-' + phase" aria-hidden="true">

    <svg class="gantry" viewBox="0 0 232 56">
      <rect class="g-frame" x="0.5" y="0.5" width="231" height="55" />
      <g v-for="i in 5" :key="i">
        <circle class="g-lamp" :cx="i * 40 - 4" cy="28" r="14" />
        <circle class="g-lit" :cx="i * 40 - 4" cy="28" r="14" :style="{ '--i': i - 1 }" />
      </g>
    </svg>

    <div class="stage">
      <template v-if="outline">
        <svg class="outline" viewBox="0 0 400 240">
          <path :d="outline" pathLength="1" />
        </svg>
        <div class="intro-name">{{ raceName }}</div>
      </template>
      <div v-else class="intro-name wordmark">PITLANE<span class="dot">.</span></div>
    </div>

    <button class="intro-skip" type="button" tabindex="-1">SKIP</button>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { introPlays, introFinished } from '@/services/intro'
import { getSchedule } from '@/services/schedule'
import { getManifest, getCircuit } from '@/services/data'

// Timeline in ms. Lights come on one by one, go out together, the outline draws, the
// overlay fades. Keep in step with the CSS below.
const LIGHTS_OUT = 1500
const FADE_AT    = 2400
const END        = 2600
const FETCH_BUDGET = 600   // per request; anything slower and we show the wordmark instead

const W = 400, H = 240, PAD = 16   // outline viewBox

const visible  = ref(introPlays)
const phase    = ref('lights')   // lights -> go -> out
const outline  = ref('')
const raceName = ref('')

let loaded = null   // { d, name } once the circuit is in hand
let timers = []

const within = (promise, ms) => Promise.race([
  promise,
  new Promise((_, reject) => setTimeout(() => reject(new Error('slow')), ms)),
])

function toPath({ points, rotation }) {
  const a = (rotation || 0) * Math.PI / 180
  const cos = Math.cos(a), sin = Math.sin(a)
  // FastF1 rotation convention; y is flipped because SVG y points down.
  const pts = points.map(p => [p.x * cos - p.y * sin, -(p.x * sin + p.y * cos)])
  const xs = pts.map(p => p[0]), ys = pts.map(p => p[1])
  const minX = Math.min(...xs), minY = Math.min(...ys)
  const spanX = (Math.max(...xs) - minX) || 1, spanY = (Math.max(...ys) - minY) || 1
  const scale = Math.min((W - 2 * PAD) / spanX, (H - 2 * PAD) / spanY)
  const ox = (W - spanX * scale) / 2, oy = (H - spanY * scale) / 2
  return 'M' + pts
    .map(([x, y]) => `${(ox + (x - minX) * scale).toFixed(1)} ${(oy + (y - minY) * scale).toFixed(1)}`)
    .join('L') + 'Z'
}

// Most recent event at the next race's venue. Two rounds of requests at 600 ms each
// finish before lights out, so the intro never waits on them.
async function loadOutline() {
  const [races, manifest] = await Promise.all([
    within(getSchedule(new Date().getFullYear()), FETCH_BUDGET),
    within(getManifest(), FETCH_BUDGET),
  ])
  const next  = races.find(r => r.is_next)
  const event = next && manifest.events.find(e => e.location === next.location)
  if (!event) return
  const circuit = await within(getCircuit(event.year, event.round), FETCH_BUDGET)
  if (circuit?.points?.length > 1) loaded = { d: toPath(circuit), name: next.name }
}

function lightsOut() {
  if (loaded) {
    outline.value  = loaded.d
    raceName.value = loaded.name
  }
  phase.value = 'go'
}

function fadeOut() {
  phase.value = 'out'
  introFinished(false)   // hero entrance starts as the overlay lifts
}

function end(skipped) {
  if (!visible.value) return
  timers.forEach(clearTimeout)
  window.removeEventListener('keydown', skip)
  window.removeEventListener('pointerdown', skip)
  visible.value = false
  if (skipped) introFinished(true)
}

function skip() {
  if (phase.value !== 'out') end(true)
}

onMounted(() => {
  if (!visible.value) return
  loadOutline().catch(() => {})   // no outline: the wordmark shows
  timers = [
    setTimeout(lightsOut, LIGHTS_OUT),
    setTimeout(fadeOut, FADE_AT),
    setTimeout(() => end(false), END),
  ]
  window.addEventListener('keydown', skip)
  window.addEventListener('pointerdown', skip)
})

onBeforeUnmount(() => end(false))
</script>

<style scoped>
.intro {
  position: fixed;
  inset: 0;
  z-index: 10000;   /* above the cold-start overlay, which may be waiting underneath */
  background: var(--bg-primary);
  display: grid;
  place-items: center;
  transition: opacity 200ms var(--ease);
}
.intro.is-out { opacity: 0; pointer-events: none; }

.gantry, .stage { grid-area: 1 / 1; }

/* ── Start lights ── */
.gantry {
  width: min(232px, 64vw);
  overflow: visible;
  transition: opacity 200ms var(--ease);
}
.g-frame, .g-lamp {
  fill: none;
  stroke: var(--border-secondary);
  stroke-width: 1;
  vector-effect: non-scaling-stroke;
}
.g-lit { fill: var(--accent); opacity: 0; }
.is-lights .g-lit {
  animation: lamp-on 60ms linear both;
  animation-delay: calc(200ms + var(--i) * 280ms);
}
@keyframes lamp-on { to { opacity: 1; } }
.is-go .gantry, .is-out .gantry { opacity: 0; }

/* ── Circuit outline and name ── */
.stage {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1.25rem;
  padding: 0 1.5rem;
  opacity: 0;
}
.is-go .stage, .is-out .stage { opacity: 1; }

.outline { width: min(480px, 78vw); }
.outline path {
  fill: none;
  stroke: var(--accent);
  stroke-width: 2;
  stroke-linejoin: round;
  vector-effect: non-scaling-stroke;
  stroke-dasharray: 1;
  stroke-dashoffset: 1;
}
.is-go .outline path, .is-out .outline path { animation: draw 900ms var(--ease) forwards; }
@keyframes draw { to { stroke-dashoffset: 0; } }

.intro-name {
  font-family: 'Bebas Neue', sans-serif;
  font-size: clamp(2rem, 5vw, 3.5rem);
  line-height: 0.95;
  color: var(--text-primary);
  text-align: center;
  opacity: 0;
}
.is-go .intro-name, .is-out .intro-name { animation: name-in 320ms var(--ease) 200ms forwards; }
@keyframes name-in { to { opacity: 1; } }

.wordmark { font-size: clamp(2.8rem, 9vw, 5rem); letter-spacing: 4px; }
.dot { color: var(--accent); }

.intro-skip {
  position: absolute;
  right: 1.5rem;
  bottom: 1.5rem;
  background: none;
  border: none;
  padding: 0.5rem;
  font-family: 'DM Mono', monospace;
  font-size: 11px;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--text-secondary);
  cursor: pointer;
}
.intro-skip:hover { color: var(--text-primary); }
</style>
