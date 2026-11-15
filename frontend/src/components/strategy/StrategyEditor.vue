<template>
  <!-- Two stint bars on one lap axis: ACTUAL (read-only) and YOUR CALL (editable).
       A pit marker is a slider: drag it, or focus it and use the arrow keys (shift = 5 laps),
       Delete removes it. A stint is a button: press it to change the compound. -->
  <section class="editor" aria-label="Strategy editor">
    <div class="ed-row">
      <div class="ed-label">ACTUAL</div>
      <div class="ed-track">
        <div class="ed-bar">
          <span v-for="(b, i) in shading" :key="'a' + i" class="ed-shade" :class="b.type" :style="b.style"></span>
          <span
            v-for="s in actual"
            :key="s.start"
            class="ed-stint tyre-fill"
            :class="tyreClass(s.compound)"
            :style="span(s.start, s.end)"
            :title="`${tyreName(s.compound)}: laps ${s.start} to ${s.end}`"
          ><span class="ed-stint-name">{{ letter(s.compound) }}</span></span>
        </div>
      </div>
    </div>

    <div class="ed-row">
      <div class="ed-label call">YOUR CALL</div>
      <div class="ed-track">
        <div ref="bar" class="ed-bar editable">
          <span v-for="(b, i) in shading" :key="'c' + i" class="ed-shade" :class="b.type" :style="b.style"></span>
          <button
            v-for="(s, i) in stints"
            :key="'s' + i"
            type="button"
            class="ed-stint tyre-fill"
            :class="tyreClass(s.compound)"
            :style="span(s.start, s.end)"
            :aria-label="`Stint ${i + 1}: ${tyreName(s.compound)}, laps ${s.start} to ${s.end}. Press to change the compound.`"
            :title="`${tyreName(s.compound)}: laps ${s.start} to ${s.end}. Click to change the compound.`"
            @click="cycle(i)"
          ><span class="ed-stint-name">{{ letter(s.compound) }}</span></button>

          <button
            v-for="(lap, i) in modelValue.stops"
            :key="'m' + i"
            type="button"
            class="ed-marker"
            :class="{ dragging: drag?.index === i, removing: drag?.index === i && drag.off }"
            role="slider"
            aria-orientation="horizontal"
            :aria-label="`Pit stop ${i + 1}`"
            :aria-valuemin="minLap(i)"
            :aria-valuemax="maxLap(i)"
            :aria-valuenow="lap"
            :aria-valuetext="`Pit at the end of lap ${lap}`"
            :style="{ left: pct(lap) + '%' }"
            @pointerdown="startDrag($event, i)"
            @pointermove="onDrag"
            @pointerup="endDrag"
            @pointercancel="drag = null"
            @keydown="onKey($event, i)"
          >
            <span class="ed-flag">{{ drag?.index === i && drag.off ? 'REMOVE' : 'LAP ' + lap }}</span>
          </button>
        </div>

        <div class="ed-axis" aria-hidden="true">
          <span v-for="n in ticks" :key="n" :style="{ left: pct(n) + '%' }">{{ n }}</span>
        </div>
      </div>
    </div>

    <div class="ed-foot">
      <button type="button" class="ed-btn" :disabled="!canAdd" title="Add a pit stop in the middle of the longest stint" @click="addStop">
        <svg viewBox="0 0 10 10" aria-hidden="true"><path d="M5 1v8M1 5h8" /></svg> ADD STOP
      </button>
      <span class="ed-hint">Drag a marker to move a stop, or focus it and use the arrow keys (shift for 5 laps). Click a stint to change its tyre. Drag a marker off the bar, or press Delete, to remove the stop.</span>
      <span class="ed-key">
        <span v-if="has('sc')"><i class="ed-swatch sc"></i> Safety Car</span>
        <span v-if="has('vsc')"><i class="ed-swatch vsc"></i> VSC</span>
        <span v-if="has('red')"><i class="ed-swatch red"></i> Red flag</span>
      </span>
    </div>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import { tyreClass, tyreName } from '@/lib/format'

const props = defineProps({
  modelValue: { type: Object, required: true },   // { compounds: ['MEDIUM', 'HARD'], stops: [18] }
  actual:     { type: Array, required: true },    // the real stints [{ compound, start, end }]
  laps:       { type: Number, required: true },   // laps the driver completed
  compounds:  { type: Array, required: true },    // compounds that can be chosen
  bands:      { type: Array, default: () => [] }, // statusBands(): Safety Car, VSC and red-flag laps
})
const emit = defineEmits(['update:modelValue'])

const OFF_BAR_PX = 44        // drag a marker this far above or below the bar to remove it

const pct = lap => (lap / props.laps) * 100
const span = (start, end) => ({ left: pct(start - 1) + '%', width: pct(end - start + 1) + '%' })
const letter = c => (c ? c[0] : '?')

const stints = computed(() => props.modelValue.compounds.map((compound, i) => ({
  compound,
  start: i === 0 ? 1 : props.modelValue.stops[i - 1] + 1,
  end: i < props.modelValue.stops.length ? props.modelValue.stops[i] : props.laps,
})))

const shading = computed(() => props.bands.filter(b => b.type !== 'yellow' && b.startLap <= props.laps).map(b => ({
  type: b.type,
  style: span(b.startLap, Math.min(b.endLap, props.laps)),
})))
const has = type => shading.value.some(b => b.type === type)

const ticks = computed(() => {
  const step = props.laps > 40 ? 10 : 5
  const out = []
  for (let n = step; n < props.laps; n += step) out.push(n)
  return out
})

// A stop sits strictly between its neighbours, and never on the last lap
const minLap = i => (i === 0 ? 1 : props.modelValue.stops[i - 1] + 1)
const maxLap = i => (i === props.modelValue.stops.length - 1 ? props.laps - 1 : props.modelValue.stops[i + 1] - 1)
const clamp = (lap, i) => Math.min(maxLap(i), Math.max(minLap(i), lap))

function update(compounds, stops) {
  emit('update:modelValue', { compounds, stops })
}
function moveStop(i, lap) {
  lap = clamp(lap, i)
  if (lap === props.modelValue.stops[i]) return
  const stops = props.modelValue.stops.slice()
  stops[i] = lap
  update(props.modelValue.compounds, stops)
}
function removeStop(i) {
  const compounds = props.modelValue.compounds.slice(), stops = props.modelValue.stops.slice()
  stops.splice(i, 1)
  compounds.splice(i + 1, 1)          // the stint that began at this stop goes with it
  update(compounds, stops)
}
function cycle(i) {
  const options = props.compounds
  if (options.length < 2) return
  const compounds = props.modelValue.compounds.slice()
  compounds[i] = options[(options.indexOf(compounds[i]) + 1) % options.length]
  update(compounds, props.modelValue.stops)
}

// A new stop goes in the middle of the longest stint, onto a different compound
const longest = computed(() => stints.value.reduce((a, b, i) => (b.end - b.start > a.len ? { i, len: b.end - b.start } : a), { i: 0, len: -1 }))
const canAdd = computed(() => longest.value.len >= 2 && props.modelValue.stops.length < 6)
function addStop() {
  if (!canAdd.value) return
  const i = longest.value.i, s = stints.value[i]
  const lap = Math.floor((s.start + s.end) / 2)
  const compounds = props.modelValue.compounds.slice(), stops = props.modelValue.stops.slice()
  const other = props.compounds.find(c => c !== s.compound) || s.compound
  stops.splice(i, 0, lap)
  compounds.splice(i + 1, 0, other)
  update(compounds, stops)
}

// ── Dragging (mouse, pen and touch through pointer events) ──
const bar = ref(null)
const drag = ref(null)       // { index, off }
function startDrag(e, i) {
  try { e.currentTarget.setPointerCapture(e.pointerId) } catch { /* a pointer the browser no longer tracks: the drag still works over the marker */ }
  drag.value = { index: i, off: false }
}
function onDrag(e) {
  if (!drag.value) return
  const rect = bar.value.getBoundingClientRect()
  drag.value.off = e.clientY < rect.top - OFF_BAR_PX || e.clientY > rect.bottom + OFF_BAR_PX
  if (!drag.value.off) moveStop(drag.value.index, Math.round(((e.clientX - rect.left) / rect.width) * props.laps))
}
function endDrag() {
  if (drag.value?.off) removeStop(drag.value.index)
  drag.value = null
}

function onKey(e, i) {
  const step = e.shiftKey ? 5 : 1
  const lap = props.modelValue.stops[i]
  if (e.key === 'ArrowLeft' || e.key === 'ArrowDown') moveStop(i, lap - step)
  else if (e.key === 'ArrowRight' || e.key === 'ArrowUp') moveStop(i, lap + step)
  else if (e.key === 'Home') moveStop(i, minLap(i))
  else if (e.key === 'End') moveStop(i, maxLap(i))
  else if (e.key === 'Delete' || e.key === 'Backspace') removeStop(i)
  else return
  e.preventDefault()
}
</script>

<style scoped>
.editor { border: 1px solid var(--border-primary); padding: 1rem 1rem 0.8rem; font-family: 'DM Mono', monospace; }
.ed-row { display: grid; grid-template-columns: 5.2rem minmax(0, 1fr); align-items: start; gap: 0.75rem; }
.ed-row + .ed-row { margin-top: 1.6rem; }          /* room for the lap flag above a marker */
.ed-label { height: 30px; display: flex; align-items: center; font-size: 0.6rem; letter-spacing: 0.16em; color: var(--text-secondary); }
.ed-label.call { color: var(--text-primary); }

.ed-track { min-width: 0; padding: 0 9px; }         /* a marker at either end stays inside */
.ed-bar { position: relative; height: 30px; background: var(--bg-secondary); border: 1px solid var(--border-secondary); }
.ed-shade { position: absolute; top: -5px; bottom: -5px; pointer-events: none; }
.ed-shade.sc  { background: color-mix(in srgb, var(--status-sc) 34%, transparent); }
.ed-shade.vsc { background: color-mix(in srgb, var(--status-vsc) 26%, transparent); }
.ed-shade.red { background: color-mix(in srgb, var(--status-red) 40%, transparent); }

.ed-stint {
  position: absolute;
  top: 3px;
  bottom: 3px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  border: 0;
  border-left: 2px solid var(--bg-primary);
  overflow: hidden;
  font: inherit;
  opacity: 0.92;
}
button.ed-stint { cursor: pointer; transition: opacity var(--dur-fast) var(--ease); }
button.ed-stint:hover { opacity: 1; }
.ed-stint-name { font-size: 0.68rem; color: var(--tyre-ink); letter-spacing: 0.08em; }
.ed-stint.soft .ed-stint-name { color: var(--tyre-ink-on-soft); }

.ed-marker {
  position: absolute;
  top: -7px;
  bottom: -7px;
  width: 18px;
  margin-left: -9px;
  padding: 0;
  background: none;
  border: 0;
  cursor: ew-resize;
  touch-action: none;                 /* the drag is ours, not a page scroll */
  z-index: 2;
}
.ed-marker::before {                  /* the bar of the marker */
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  left: 6px;
  width: 6px;
  background: var(--text-primary);
  border: 1px solid var(--bg-primary);
  transition: background var(--dur-fast) var(--ease);
}
.ed-marker:hover::before, .ed-marker:focus-visible::before, .ed-marker.dragging::before { background: var(--accent); }
.ed-marker.removing::before { background: none; border: 1px dashed var(--status-red); }
.ed-flag {
  position: absolute;
  bottom: calc(100% + 2px);
  left: 50%;
  translate: -50% 0;
  padding: 0.05rem 0.3rem;
  background: var(--bg-primary);
  border: 1px solid var(--border-secondary);
  font-size: 0.56rem;
  letter-spacing: 0.1em;
  color: var(--text-primary);
  white-space: nowrap;
  pointer-events: none;
}
.ed-marker:focus-visible .ed-flag, .ed-marker.dragging .ed-flag { border-color: var(--accent); color: var(--accent); }
.ed-marker.removing .ed-flag { border-color: var(--status-red); color: var(--status-red); }

.ed-axis { position: relative; height: 16px; margin-top: 6px; font-size: 0.56rem; color: var(--text-secondary); }
.ed-axis span { position: absolute; translate: -50% 0; }

.ed-foot { display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem 1rem; margin-top: 0.6rem; }
.ed-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.35rem 0.7rem;
  background: none;
  border: 1px solid var(--border-secondary);
  color: var(--text-primary);
  font: inherit;
  font-size: 0.58rem;
  letter-spacing: 0.14em;
  cursor: pointer;
  transition: border-color var(--dur-fast) var(--ease), color var(--dur-fast) var(--ease), scale var(--dur-fast) var(--ease);
}
.ed-btn:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
.ed-btn:disabled { opacity: 0.35; cursor: default; }
.ed-btn svg { width: 10px; height: 10px; fill: none; stroke: currentColor; stroke-width: 1.4; }
.ed-hint { flex: 1 1 18rem; font-family: 'Work Sans', sans-serif; font-size: 0.72rem; line-height: 1.4; color: var(--text-secondary); }
.ed-key { display: inline-flex; gap: 0.8rem; font-size: 0.56rem; letter-spacing: 0.1em; text-transform: uppercase; color: var(--text-secondary); }
.ed-swatch { display: inline-block; width: 0.8em; height: 0.8em; vertical-align: -0.05em; }
.ed-swatch.sc  { background: color-mix(in srgb, var(--status-sc) 60%, transparent); }
.ed-swatch.vsc { background: color-mix(in srgb, var(--status-vsc) 55%, transparent); }
.ed-swatch.red { background: color-mix(in srgb, var(--status-red) 60%, transparent); }

@media (max-width: 720px) {
  .editor { padding: 0.8rem 0.6rem; }
  .ed-row { grid-template-columns: minmax(0, 1fr); gap: 0.2rem; }
  .ed-label { height: auto; }
  .ed-row + .ed-row { margin-top: 0.9rem; }
  .ed-row:nth-child(2) .ed-track { padding-top: 1.1rem; }   /* the lap flag sits above the bar */
  .ed-marker { width: 28px; margin-left: -14px; }           /* a finger-sized target */
  .ed-marker::before { left: 11px; }
}
</style>
