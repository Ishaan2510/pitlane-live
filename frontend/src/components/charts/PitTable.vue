<template>
  <ChartFrame
    title="Pit stops"
    caption="Every stop of the race: what it cost against a normal stop at this track, and whether the driver came out ahead or behind."
    note="Time lost is in-lap plus out-lap minus two normal laps, from pit_loss.json; it is only measured for stops with clean laps either side. Against median compares a green-flag stop with the green-flag median and a Safety Car or VSC stop with the Safety Car median. Positions are the lap before the stop and the lap after it. Tyre changes made during a red flag are not counted as stops."
    :empty="rows.length ? '' : 'No pit stops for the selected drivers.'"
  >
    <template #controls>
      <dl class="pit-heads">
        <div>
          <dt>MEDIAN PIT LOSS</dt>
          <dd v-if="pitLoss?.median_loss_s != null">{{ pitLoss.median_loss_s.toFixed(1) }} s <small>{{ pitLoss.green_stops }} green-flag stops</small></dd>
          <dd v-else class="none">Not measured <small>{{ noMedianWhy }}</small></dd>
        </div>
        <div>
          <dt>UNDER SAFETY CAR / VSC</dt>
          <dd v-if="pitLoss?.median_loss_sc_s != null">{{ pitLoss.median_loss_sc_s.toFixed(1) }} s <small>{{ pitLoss.sc_stops }} stops</small></dd>
          <dd v-else class="none">Not measured <small>fewer than two such stops</small></dd>
        </div>
      </dl>
    </template>

    <div class="pit-scroll">
      <table class="pit-table">
        <thead>
          <tr>
            <th v-for="c in COLUMNS" :key="c.key" :class="c.cls" :aria-sort="sortKey === c.key ? (sortDir > 0 ? 'ascending' : 'descending') : 'none'">
              <button type="button" @click="sortBy(c.key)">
                {{ c.label }}
                <svg v-if="sortKey === c.key" viewBox="0 0 8 8" aria-hidden="true"><path :d="sortDir > 0 ? 'M4 1 7 6H1z' : 'M4 7 7 2H1z'" /></svg>
              </button>
            </th>
            <th class="act"><span class="sr-only">Replay</span></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in rows" :key="r.driver + r.lap" :class="{ on: debrief.highlight.value === r.driver, dim: debrief.highlight.value && debrief.highlight.value !== r.driver }" @click="debrief.toggleHighlight(r.driver)">
            <td><span class="team-bar" :style="{ background: r.color }"></span>{{ r.driver }}</td>
            <td class="num">{{ r.lap }}</td>
            <td>
              <span class="tyre-key" :class="tyreClass(r.from)"></span> {{ tyreName(r.from) }}
              <svg class="arrow" viewBox="0 0 10 8" aria-hidden="true"><path d="M1 4h7M5.5 1.5 8 4 5.5 6.5" /></svg>
              <span class="tyre-key" :class="tyreClass(r.to)"></span> {{ tyreName(r.to) }}
            </td>
            <td class="num">{{ r.loss != null ? r.loss.toFixed(1) + ' s' : '—' }}</td>
            <td class="num" :class="{ good: r.vsMedian < 0, bad: r.vsMedian > 0 }">{{ r.vsMedian != null ? fmtGap(r.vsMedian, 1) + ' s' : '—' }}</td>
            <td><span v-if="r.status" class="status" :class="r.status">{{ r.status.toUpperCase() }}</span><template v-else>Green</template></td>
            <td class="num">
              <template v-if="r.posBefore && r.posAfter">P{{ r.posBefore }} → P{{ r.posAfter }}</template>
              <template v-else>—</template>
            </td>
            <td class="act"><router-link :to="debrief.replayLink(r.lap, r.driver)" :aria-label="`Open ${r.driver} lap ${r.lap} in the replay`" @click.stop>REPLAY →</router-link></td>
          </tr>
        </tbody>
      </table>
    </div>
  </ChartFrame>
</template>

<script setup>
import { computed, inject, ref } from 'vue'
import { DEBRIEF } from '@/composables/useChart'
import { fmtGap, tyreClass, tyreName } from '@/lib/format'
import ChartFrame from './ChartFrame.vue'

const props = defineProps({
  drivers: { type: Array, required: true },    // the drivers to list (for colour and filter)
  table:   { type: Array, required: true },    // pitTable()
  pitLoss: { type: Object, default: null },    // pit_loss.json
})

const debrief = inject(DEBRIEF)

const COLUMNS = [
  { key: 'driver',    label: 'Driver' },
  { key: 'lap',       label: 'Lap', cls: 'num' },
  { key: 'to',        label: 'Tyres' },
  { key: 'loss',      label: 'Time lost', cls: 'num' },
  { key: 'vsMedian',  label: 'Vs median', cls: 'num' },
  { key: 'status',    label: 'Track' },
  { key: 'gained',    label: 'Position', cls: 'num' },
]

const sortKey = ref('lap')
const sortDir = ref(1)
function sortBy(key) {
  if (sortKey.value === key) sortDir.value = -sortDir.value
  else { sortKey.value = key; sortDir.value = 1 }
}

const rows = computed(() => {
  const meta = Object.fromEntries(props.drivers.map(d => [d.driver, d]))
  const k = sortKey.value, dir = sortDir.value
  return props.table
    .filter(r => meta[r.driver])
    .map(r => ({ ...r, color: meta[r.driver].color }))
    .sort((a, b) => {
      const x = a[k], y = b[k]
      if (x == null || y == null) return (x == null) - (y == null)     // unknowns last either way
      return (typeof x === 'number' ? x - y : String(x).localeCompare(String(y))) * dir || a.lap - b.lap
    })
})

const noMedianWhy = computed(() => (
  props.pitLoss
    ? 'no stop in this race had green-flag laps on both sides'
    : 'no pit-loss file for this race'
))
</script>

<style scoped>
.pit-heads { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 1px; background: var(--border-primary); border: 1px solid var(--border-primary); }
.pit-heads div { background: var(--bg-primary); padding: 0.6rem 0.75rem; }
.pit-heads dt { font-family: 'DM Mono', monospace; font-size: 0.56rem; letter-spacing: 0.16em; color: var(--text-secondary); }
.pit-heads dd { font-family: 'Bebas Neue', sans-serif; font-size: 1.7rem; line-height: 1.15; letter-spacing: 0.03em; color: var(--text-primary); }
.pit-heads dd.none { font-size: 1.2rem; color: var(--text-secondary); }
.pit-heads small { display: block; font-family: 'Work Sans', sans-serif; font-size: 0.72rem; letter-spacing: 0; color: var(--text-secondary); }

.pit-scroll { overflow-x: auto; max-height: 520px; overflow-y: auto; border: 1px solid var(--border-primary); }
.pit-table { width: 100%; border-collapse: collapse; font-family: 'DM Mono', monospace; font-size: 0.7rem; white-space: nowrap; }
.pit-table th { position: sticky; top: 0; z-index: 1; background: var(--bg-secondary); border-bottom: 1px solid var(--border-primary); text-align: left; padding: 0; }
.pit-table th button {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  width: 100%;
  padding: 0.5rem 0.6rem;
  background: none;
  border: none;
  color: var(--text-secondary);
  font: inherit;
  font-size: 0.56rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  cursor: pointer;
}
.pit-table th.num button { justify-content: flex-end; }
.pit-table th button:hover { color: var(--text-primary); }
.pit-table th svg { width: 7px; height: 7px; fill: currentColor; }
.pit-table td { padding: 0.4rem 0.6rem; border-bottom: 1px solid var(--border-primary); color: var(--text-primary); }
.pit-table td.num { text-align: right; font-variant-numeric: tabular-nums; }
.pit-table tbody tr { cursor: pointer; transition: opacity var(--dur-base) var(--ease); }
.pit-table tbody tr:hover, .pit-table tbody tr.on { background: var(--bg-hover); }
.pit-table tbody tr.dim { opacity: 0.35; }
.pit-table tbody tr:last-child td { border-bottom: none; }

.team-bar { display: inline-block; width: 3px; height: 0.9em; margin-right: 0.45rem; vertical-align: -0.1em; }
.arrow { width: 10px; height: 8px; margin: 0 0.2rem; fill: none; stroke: var(--text-secondary); stroke-width: 1.2; stroke-linecap: round; stroke-linejoin: round; }
.good { color: var(--status-green) !important; }
.bad  { color: var(--status-red) !important; }
.status { padding: 0.05rem 0.35rem; border: 1px solid; font-size: 0.58rem; letter-spacing: 0.1em; }
.status.sc  { color: var(--status-sc); }
.status.vsc { color: var(--status-vsc); }
.act a { color: var(--accent); text-decoration: none; font-size: 0.58rem; letter-spacing: 0.12em; }
.act a:hover { text-decoration: underline; }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); }
</style>
