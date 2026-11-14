<template>
  <div class="feed">
    <div class="feed-title">RACE EVENTS</div>
    <p v-if="!shown.length" class="feed-empty">Events appear here as the race plays.</p>
    <ol v-else class="feed-list">
      <li v-for="e in shown" :key="e.key">
        <button type="button" class="feed-item" :class="[e.type, e.status]" :title="`Jump to lap ${e.lap}`" @click="$emit('seek', e.p)">
          <span class="f-lap">L{{ e.lap }}</span>
          <span class="f-text">
            <template v-if="e.type === 'pit'">
              <b>{{ e.driver }}</b> pits
              <span class="tyre-key" :class="tyreClass(e.from)"></span>
              <svg class="f-arrow" viewBox="0 0 10 8" aria-hidden="true"><path d="M1 4h7M5.5 1.5 8 4 5.5 6.5" /></svg>
              <span class="tyre-key" :class="tyreClass(e.to)"></span>
              <span class="sr-only">{{ tyreName(e.from) }} to {{ tyreName(e.to) }}</span>
              <span v-if="e.loss != null" class="f-dim">{{ e.loss.toFixed(1) }}s lost</span>
            </template>
            <template v-else-if="e.type === 'status'"><b>{{ STATUS_LABEL[e.status] }}</b></template>
            <template v-else-if="e.type === 'clear'">{{ STATUS_LABEL[e.status] }} ends</template>
            <template v-else-if="e.type === 'lead'"><b>{{ e.driver }}</b> takes the lead from {{ e.from }}</template>
            <template v-else-if="e.type === 'retired'"><b>{{ e.driver }}</b> retires</template>
            <template v-else-if="e.type === 'fastest'"><b>{{ e.driver }}</b> fastest lap <span class="f-dim">{{ fmtLapTime(e.time) }}</span></template>
          </span>
        </button>
      </li>
    </ol>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { STATUS_LABEL } from '@/lib/raceEvents'
import { fmtLapTime, tyreClass, tyreName } from '@/lib/format'

const props = defineProps({
  events:   { type: Array, default: () => [] },   // raceEvents(), sorted by playhead
  playhead: { type: Number, default: 0 },
})
defineEmits(['seek'])

const MAX_SHOWN = 80

// Newest first, only what has happened by now
const shown = computed(() => {
  const out = []
  for (let i = props.events.length - 1; i >= 0 && out.length < MAX_SHOWN; i--) {
    const e = props.events[i]
    if (e.p <= props.playhead + 1e-6) out.push({ ...e, key: i })
  }
  return out
})
</script>

<style scoped>
.feed { display: flex; flex-direction: column; min-height: 0; font-family: 'DM Mono', monospace; }
.feed-title { padding: 0.6rem 0.75rem 0.4rem; font-size: 0.62rem; letter-spacing: 0.18em; color: var(--text-secondary); }
.feed-empty { padding: 0 0.75rem 0.75rem; font-family: 'Work Sans', sans-serif; font-size: 0.8rem; color: var(--text-secondary); }
.feed-list { list-style: none; overflow-y: auto; min-height: 0; flex: 1; border-top: 1px solid var(--border-primary); }

.feed-item {
  display: grid;
  grid-template-columns: 2.4rem 1fr;
  align-items: center;
  gap: 0.4rem;
  width: 100%;
  min-height: 26px;
  padding: 0.25rem 0.75rem 0.25rem 0.6rem;
  background: none;
  border: none;
  border-bottom: 1px solid var(--border-primary);
  border-left: 2px solid transparent;
  color: var(--text-secondary);
  font: inherit;
  font-size: 0.68rem;
  text-align: left;
  cursor: pointer;
}
.feed-item:hover { background: var(--bg-hover); }
.feed-item:focus-visible { outline-offset: -1px; }
.feed-item b { color: var(--text-primary); font-weight: 500; }
.f-lap { color: var(--text-secondary); font-size: 0.6rem; letter-spacing: 0.06em; }
.f-text { display: inline-flex; flex-wrap: wrap; align-items: center; gap: 0.3rem; }
.f-dim { color: var(--text-secondary); }
.f-arrow { width: 10px; height: 8px; fill: none; stroke: currentColor; stroke-width: 1.2; stroke-linecap: round; stroke-linejoin: round; }

.feed-item.status.sc     { border-left-color: var(--status-sc); }
.feed-item.status.vsc,
.feed-item.status.yellow { border-left-color: var(--status-vsc); }
.feed-item.status.red    { border-left-color: var(--status-red); }
.feed-item.status.sc b     { color: var(--status-sc); }
.feed-item.status.vsc b,
.feed-item.status.yellow b { color: var(--status-vsc); }
.feed-item.status.red b    { color: var(--status-red); }
.feed-item.clear   { border-left-color: var(--status-green); }
.feed-item.lead    { border-left-color: var(--accent); }
.feed-item.retired { border-left-color: var(--text-secondary); }

.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); }
</style>
