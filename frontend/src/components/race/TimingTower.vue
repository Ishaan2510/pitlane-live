<template>
  <div class="tower">
    <div class="tower-top">
      <span class="tower-title">TIMING</span>
      <div class="tower-mode" role="group" aria-label="Show gap to leader or interval to the car ahead">
        <button type="button" class="mode-btn" :class="{ active: mode === 'gap' }" :aria-pressed="mode === 'gap'" @click="mode = 'gap'">GAP</button>
        <button type="button" class="mode-btn" :class="{ active: mode === 'interval' }" :aria-pressed="mode === 'interval'" @click="mode = 'interval'">INT</button>
      </div>
    </div>

    <div class="tyre-legend" aria-label="Tyre colours">
      <span v-for="[cls, name] in TYRE_LEGEND" :key="cls"><span class="tyre-key" :class="cls"></span> {{ name }}</span>
    </div>

    <!-- FLIP: rows slide to their new place when the order changes -->
    <TransitionGroup name="tower" tag="ol" class="tower-rows">
      <li
        v-for="car in cars"
        :key="car.driver"
        class="tower-row"
        :class="{ selected: car.driver === selected, pinned: car.driver === pinned, out: car.retired }"
      >
        <button
          type="button"
          class="row-main"
          :aria-pressed="car.driver === selected"
          @click="e => $emit(e.shiftKey ? 'pin' : 'select', car.driver)"
        >
          <span class="t-pos">{{ car.position }}</span>
          <span class="t-code" :style="{ borderColor: car.color }">{{ car.driver }}</span>
          <span class="t-move" :class="moveClass(car)" :title="moveTitle(car)">
            <template v-if="moved(car) > 0"><svg viewBox="0 0 8 8" aria-hidden="true"><path d="M4 1 7 6H1z" /></svg>{{ moved(car) }}</template>
            <template v-else-if="moved(car) < 0"><svg viewBox="0 0 8 8" aria-hidden="true"><path d="M4 7 7 2H1z" /></svg>{{ -moved(car) }}</template>
          </span>
          <span class="t-gap" :class="{ flag: car.inPit || car.retired }">{{ gapText(car) }}</span>
          <span class="t-tyre">
            <span class="tyre-key" :class="tyreClass(car.compound)" :title="car.compound || 'Unknown compound'"></span>
            <span class="t-age">{{ car.tyreAge || '' }}</span>
          </span>
        </button>
        <button
          type="button"
          class="row-pin"
          :aria-pressed="car.driver === pinned"
          :aria-label="car.driver === pinned ? `Unpin ${car.driver}` : `Pin ${car.driver} to compare`"
          :title="car.driver === pinned ? 'Unpin' : 'Pin to compare'"
          @click="$emit('pin', car.driver)"
        >
          <svg viewBox="0 0 12 12" aria-hidden="true"><path d="M4.5 1.5h3l-.5 3.5 2 2h-6l2-2zM6 7v3.5" /></svg>
        </button>
      </li>
    </TransitionGroup>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { fmtGap, tyreClass, TYRE_LEGEND } from '@/lib/format'

const props = defineProps({
  cars:     { type: Array, default: () => [] },   // raceClock.stateAt(), sorted by position
  grid:     { type: Object, default: () => ({}) }, // driver -> grid slot (absent for a pit-lane start)
  selected: { type: String, default: null },
  pinned:   { type: String, default: null },
})
defineEmits(['select', 'pin'])

const mode = ref('gap')

// Places gained (+) or lost (-) since the start
function moved(car) {
  const g = props.grid[car.driver]
  return g && !car.retired ? g - car.position : 0
}
const moveClass = car => (moved(car) > 0 ? 'up' : moved(car) < 0 ? 'down' : '')
function moveTitle(car) {
  const m = moved(car)
  return m ? `${Math.abs(m)} place${Math.abs(m) > 1 ? 's' : ''} ${m > 0 ? 'gained' : 'lost'} since the start` : ''
}

function gapText(car) {
  if (car.retired) return 'OUT'
  if (car.inPit) return 'PIT'
  if (car.position === 1) return mode.value === 'gap' ? 'LEADER' : '—'
  if (mode.value === 'interval') return fmtGap(car.interval)
  return car.lapsDown >= 1 ? `+${car.lapsDown} LAP${car.lapsDown > 1 ? 'S' : ''}` : fmtGap(car.gap)
}
</script>

<style scoped>
.tower { display: flex; flex-direction: column; min-height: 0; font-family: 'DM Mono', monospace; }

.tower-top { display: flex; align-items: center; justify-content: space-between; padding: 0.6rem 0.75rem 0.4rem; }
.tower-title { font-size: 0.62rem; letter-spacing: 0.18em; color: var(--text-secondary); }
.tower-mode { display: flex; }
.mode-btn {
  padding: 0.2rem 0.55rem;
  background: none;
  border: 1px solid var(--border-secondary);
  color: var(--text-secondary);
  font: inherit;
  font-size: 0.58rem;
  letter-spacing: 0.12em;
  cursor: pointer;
  transition: color var(--dur-fast) var(--ease), background var(--dur-fast) var(--ease), scale var(--dur-fast) var(--ease);
}
.mode-btn + .mode-btn { border-left: none; }
.mode-btn.active { background: var(--text-primary); color: var(--bg-primary); border-color: var(--text-primary); }

.tyre-legend { padding: 0 0.75rem 0.5rem; }

.tower-rows { list-style: none; position: relative; overflow-y: auto; min-height: 0; flex: 1; border-top: 1px solid var(--border-primary); }
.tower-row {
  display: flex;
  align-items: stretch;
  border-bottom: 1px solid var(--border-primary);
  background: var(--bg-primary);
}
.tower-move { transition: transform var(--dur-base) var(--ease); }
.tower-row.selected { background: var(--bg-hover); }
.tower-row.selected .row-main { border-left-color: var(--accent); }
.tower-row.pinned .row-pin { color: var(--accent); }
/* Retired: greyed, but still readable */
.tower-row.out .row-main, .tower-row.out .t-code { color: var(--text-secondary); }
.tower-row.out .t-code { border-left-style: dashed; }
.tower-row.out .t-tyre { visibility: hidden; }

.row-main {
  flex: 1;
  min-width: 0;
  display: grid;
  grid-template-columns: 1.5rem 3rem 1.9rem 1fr 2.4rem;
  align-items: center;
  gap: 0.3rem;
  height: 26px;
  padding: 0 0.2rem 0 0.4rem;
  background: none;
  border: none;
  border-left: 2px solid transparent;
  color: var(--text-primary);
  font: inherit;
  font-size: 0.72rem;
  text-align: left;
  cursor: pointer;
}
.row-main:hover { background: var(--bg-hover); }
.row-main:focus-visible, .row-pin:focus-visible { outline-offset: -1px; }

.t-pos  { font-family: 'Bebas Neue', sans-serif; font-size: 0.95rem; color: var(--text-secondary); text-align: right; }
.t-code { font-weight: 500; letter-spacing: 0.04em; padding-left: 0.35rem; border-left: 3px solid var(--border-secondary); line-height: 1.1; }
.t-move { display: inline-flex; align-items: center; gap: 1px; font-size: 0.58rem; color: var(--text-secondary); }
.t-move svg { width: 7px; height: 7px; fill: currentColor; }
.t-move.up   { color: var(--status-green); }
.t-move.down { color: var(--status-red); }
.t-gap  { text-align: right; font-size: 0.68rem; color: var(--text-secondary); white-space: nowrap; font-variant-numeric: tabular-nums; }
.t-gap.flag { color: var(--accent-hover); letter-spacing: 0.1em; }
.t-tyre { display: inline-flex; align-items: center; gap: 0.3rem; justify-content: flex-end; }
.t-age  { min-width: 1.1rem; font-size: 0.62rem; color: var(--text-secondary); text-align: right; font-variant-numeric: tabular-nums; }

.row-pin {
  width: 26px;
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color var(--dur-fast) var(--ease);
}
.row-pin:hover { color: var(--text-primary); }
.row-pin svg { width: 12px; height: 12px; fill: none; stroke: currentColor; stroke-width: 1.2; stroke-linejoin: round; stroke-linecap: round; }
.tower-row.pinned .row-pin svg { fill: currentColor; }

@media (max-width: 720px) {
  .row-main { height: 34px; font-size: 0.78rem; }
  .row-pin  { width: 40px; }
}
</style>
