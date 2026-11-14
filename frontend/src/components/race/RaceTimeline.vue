<template>
  <div class="timeline">
    <div class="tl-head">
      <span class="tl-lap">LAP {{ currentLap }} / {{ totalLaps }}</span>
      <span class="tl-tip" aria-live="off">{{ tip }}</span>
    </div>

    <div
      ref="bar"
      class="tl-bar"
      role="slider"
      tabindex="0"
      aria-label="Race timeline"
      aria-valuemin="0"
      :aria-valuemax="totalLaps"
      :aria-valuenow="Math.round(playhead * 10) / 10"
      :aria-valuetext="`Lap ${currentLap} of ${totalLaps}`"
      @pointerdown="onDown"
      @pointermove="onMove"
      @pointerup="onUp"
      @pointercancel="onUp"
      @pointerleave="tip = ''"
      @keydown="onKey"
    >
      <!-- Track status bands -->
      <span
        v-for="(b, i) in bands"
        :key="'b' + i"
        class="tl-band"
        :class="b.type"
        :style="{ left: pct(b.startLap - 1), width: pct(b.endLap - b.startLap + 1) }"
        :data-tip="bandTip(b)"
      ></span>

      <!-- Pit stops, coloured by the tyre fitted -->
      <span
        v-for="(s, i) in pitTicks"
        :key="'s' + i"
        class="tl-tick tyre-fill"
        :class="[tyreClass(s.to), { faded: selectedDriver && s.driver !== selectedDriver && s.driver !== pinnedDriver }]"
        :style="{ left: pct(s.p) }"
        :data-tip="`${s.driver} pits · lap ${s.lap} · ${tyreName(s.from)} → ${tyreName(s.to)}`"
      ></span>

      <span class="tl-played" :style="{ width: pct(playhead) }"></span>
      <span class="tl-head-mark" :style="{ left: pct(playhead) }"></span>
    </div>

    <div class="tl-axis" aria-hidden="true">
      <span v-for="n in lapMarks" :key="n" :style="{ left: pct(n) }">{{ n }}</span>
    </div>

    <div class="tl-key">
      <span v-for="t in bandTypes" :key="t"><i class="tl-swatch" :class="t"></i>{{ STATUS_LABEL[t] }}</span>
      <span v-if="pitTicks.length"><i class="tl-swatch tick"></i>Pit stop, in the new tyre's colour</span>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { STATUS_LABEL } from '@/lib/raceEvents'
import { tyreClass, tyreName } from '@/lib/format'

const props = defineProps({
  totalLaps:      { type: Number, required: true },
  playhead:       { type: Number, required: true },     // leader laps, 0..totalLaps
  bands:          { type: Array, default: () => [] },   // statusBands()
  pitTicks:       { type: Array, default: () => [] },   // [{ p, driver, lap, from, to }]
  selectedDriver: { type: String, default: null },
  pinnedDriver:   { type: String, default: null },
})
const emit = defineEmits(['seek', 'scrub-start', 'scrub-end'])

const bar = ref(null)
const tip = ref('')
let dragging = false

const currentLap = computed(() => Math.min(props.totalLaps, Math.floor(props.playhead) + 1))
const pct = laps => `${(laps / props.totalLaps) * 100}%`
const bandTypes = computed(() => [...new Set(props.bands.map(b => b.type))])

// A lap number every 5 or 10 laps, depending on the race length
const lapMarks = computed(() => {
  const step = props.totalLaps > 60 ? 10 : 5
  const marks = [1]
  for (let n = step; n <= props.totalLaps - step / 2; n += step) marks.push(n)
  marks.push(props.totalLaps)
  return marks
})

function bandTip(b) {
  const laps = b.startLap === b.endLap ? `lap ${b.startLap}` : `laps ${b.startLap}–${b.endLap}`
  return `${STATUS_LABEL[b.type]} · ${laps}`
}

function lapsAt(e) {
  const rect = bar.value.getBoundingClientRect()
  return Math.min(props.totalLaps, Math.max(0, (e.clientX - rect.left) / rect.width * props.totalLaps))
}

function onDown(e) {
  dragging = true
  bar.value.setPointerCapture(e.pointerId)
  emit('scrub-start')
  emit('seek', lapsAt(e))
}
function onMove(e) {
  if (dragging) emit('seek', lapsAt(e))
  // Hover label: the band or pit stop under the pointer, else the lap
  const el = document.elementFromPoint(e.clientX, e.clientY)
  tip.value = el?.dataset?.tip || `Lap ${Math.min(props.totalLaps, Math.floor(lapsAt(e)) + 1)}`
}
function onUp() {
  if (!dragging) return
  dragging = false
  emit('scrub-end')
}

function onKey(e) {
  const step = { ArrowLeft: -1, ArrowRight: 1, ArrowDown: -1, ArrowUp: 1, PageDown: -5, PageUp: 5 }[e.key]
  let target = null
  if (step) target = Math.round(props.playhead) + step
  else if (e.key === 'Home') target = 0
  else if (e.key === 'End') target = props.totalLaps
  if (target == null) return
  e.preventDefault()
  e.stopPropagation()   // the page-level arrow shortcuts would step a second time
  emit('seek', Math.min(props.totalLaps, Math.max(0, target)))
}
</script>

<style scoped>
.timeline { padding: 0.6rem 1rem 0.7rem; font-family: 'DM Mono', monospace; }

.tl-head { display: flex; align-items: baseline; justify-content: space-between; gap: 1rem; margin-bottom: 0.4rem; min-height: 1.3rem; }
.tl-lap  { font-family: 'Bebas Neue', sans-serif; font-size: 1.25rem; letter-spacing: 0.08em; line-height: 1; color: var(--text-primary); white-space: nowrap; }
.tl-tip  { font-size: 0.62rem; letter-spacing: 0.1em; text-transform: uppercase; color: var(--text-secondary); text-align: right; }

.tl-bar {
  position: relative;
  height: 34px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  cursor: pointer;
  touch-action: none;      /* dragging scrubs, it does not scroll the page */
  overflow: hidden;
}

.tl-band { position: absolute; top: 0; bottom: 0; }
.tl-band.sc     { background: color-mix(in srgb, var(--status-sc) 38%, transparent); }
.tl-band.vsc    { background: color-mix(in srgb, var(--status-vsc) 26%, transparent); }
.tl-band.red    { background: color-mix(in srgb, var(--status-red) 50%, transparent); }
.tl-band.yellow { bottom: auto; height: 5px; background: var(--status-vsc); }

.tl-tick { position: absolute; top: 9px; bottom: 0; width: 3px; margin-left: -1px; transition: opacity var(--dur-base) var(--ease); }
.tl-tick.faded { opacity: 0.18; }

.tl-played { position: absolute; left: 0; top: 0; bottom: 0; background: var(--text-primary); opacity: 0.07; pointer-events: none; }
.tl-head-mark { position: absolute; top: 0; bottom: 0; width: 2px; margin-left: -1px; background: var(--accent); pointer-events: none; }

.tl-axis { position: relative; height: 1.1rem; margin-top: 0.2rem; font-size: 0.58rem; color: var(--text-secondary); }
.tl-axis span { position: absolute; transform: translateX(-50%); }
.tl-axis span:first-child { transform: none; }
.tl-axis span:last-child  { transform: translateX(-100%); }

.tl-key { display: flex; flex-wrap: wrap; gap: 0.25rem 1rem; font-size: 0.58rem; letter-spacing: 0.08em; text-transform: uppercase; color: var(--text-secondary); }
.tl-key span { display: inline-flex; align-items: center; gap: 0.35rem; }
.tl-swatch { display: inline-block; width: 12px; height: 8px; }
.tl-swatch.sc     { background: color-mix(in srgb, var(--status-sc) 38%, transparent); border: 1px solid var(--status-sc); }
.tl-swatch.vsc    { background: color-mix(in srgb, var(--status-vsc) 26%, transparent); border: 1px solid var(--status-vsc); }
.tl-swatch.red    { background: color-mix(in srgb, var(--status-red) 50%, transparent); border: 1px solid var(--status-red); }
.tl-swatch.yellow { height: 3px; background: var(--status-vsc); }
.tl-swatch.tick   { width: 3px; height: 10px; background: var(--text-secondary); }

@media (max-width: 720px) {
  .timeline { padding: 0.6rem 0.75rem; }
  .tl-bar { height: 40px; }
}
</style>
