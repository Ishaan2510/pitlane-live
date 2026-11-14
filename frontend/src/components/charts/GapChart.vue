<template>
  <LapLineChart
    title="Gap chart"
    :caption="caption"
    note="Each driver's race time at the end of a lap minus the reference's time at the end of the same lap, from raceClock (lap times placed by the gaps in replay.json). The axis stops one typical lap behind, so cars that have been lapped, and everyone during a red flag, run off the bottom edge instead of squashing the rest."
    :aria-label="`Gap to ${reference || 'the leader'} by lap`"
    :drivers="drivers"
    :series="series"
    :y-domain="domain"
    :y-ticks="ticks"
    :format="v => (Math.abs(v) < 0.0005 ? 'Level' : fmtGap(v) + ' s')"
    :height="380"
    :start-labels="false"
  >
    <template #controls>
      <label class="ref-pick">
        <span>GAP TO</span>
        <select :value="reference || ''" @change="$emit('update:reference', $event.target.value || null)">
          <option value="">The leader</option>
          <option v-for="d in allDrivers" :key="d.driver" :value="d.driver">{{ d.driver }}</option>
        </select>
      </label>
    </template>
  </LapLineChart>
</template>

<script setup>
import { computed } from 'vue'
import { ticks as niceTicks } from 'd3-array'
import { gapSeries } from '@/lib/debrief'
import { fmtGap } from '@/lib/format'
import LapLineChart from './LapLineChart.vue'

const props = defineProps({
  drivers:    { type: Array, required: true },    // the drivers to draw
  allDrivers: { type: Array, required: true },    // choices for the reference
  clock:      { type: Object, required: true },   // buildRaceClock()
  reference:  { type: String, default: null },    // null = the leader
})
defineEmits(['update:reference'])

const series = computed(() => gapSeries(props.clock, props.reference))

// A typical lap: the median of the leader's lap durations
const typicalLap = computed(() => {
  const s = props.clock.spine, laps = []
  for (let n = 1; n < s.length; n++) laps.push(s[n] - s[n - 1])
  laps.sort((a, b) => a - b)
  return laps[laps.length >> 1] || 90
})

// Top: the car furthest ahead of the reference (0 for the leader). Bottom: the furthest
// behind, but never more than one typical lap.
const domain = computed(() => {
  let min = 0, max = 1
  for (const d of props.drivers) {
    for (const v of series.value[d.driver] || []) {
      if (v < min) min = v
      if (v > max) max = v
    }
  }
  const cap = typicalLap.value
  return [Math.max(min, -cap), Math.min(max, cap)]
})
const ticks = computed(() => niceTicks(domain.value[0], domain.value[1], 6).map(v => ({ value: v, label: v === 0 ? '0' : (v > 0 ? '+' : '−') + Math.abs(v) })))

const caption = computed(() => `Seconds behind ${props.reference || 'the leader'} at the end of each lap. Lines falling away are losing time; a sudden drop is a pit stop. Lapped cars leave the bottom of the chart.`)
</script>

<style scoped>
.ref-pick { display: inline-flex; align-items: center; gap: 0.5rem; font-family: 'DM Mono', monospace; font-size: 0.6rem; letter-spacing: 0.14em; color: var(--text-secondary); }
.ref-pick select {
  padding: 0.3rem 0.5rem;
  background: var(--bg-input);
  border: 1px solid var(--border-secondary);
  border-radius: 0;
  color: var(--text-primary);
  font: inherit;
  letter-spacing: 0.06em;
  cursor: pointer;
}
</style>
