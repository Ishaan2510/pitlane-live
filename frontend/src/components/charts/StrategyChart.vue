<template>
  <ChartFrame
    title="Strategy overview"
    caption="Each driver's race as tyre stints, in finishing order. A break between two blocks is a pit stop."
    note="Stints come from the stint column of laps.json; the colour is the compound fitted. Tyre age at a stop is the tyre_life of the last lap of the stint, so it counts laps a used set had already done. Shaded columns are Safety Car, VSC and red-flag laps."
    :chart="chart"
    :empty="rows.length ? '' : 'No drivers selected.'"
  >
    <template #controls>
      <div class="tyre-legend" aria-label="Tyre colours">
        <span v-for="[cls, name] in TYRE_LEGEND" :key="cls"><span class="tyre-key" :class="cls"></span> {{ name }}</span>
        <span><span class="tyre-key"></span> Unknown</span>
      </div>
    </template>

    <svg :viewBox="`0 0 ${chart.width.value} ${chart.height.value}`" :height="chart.height.value" role="img" aria-label="Tyre stints per driver by lap">
      <g :transform="`translate(${M.left},${M.top})`">
        <rect v-for="(s, i) in chart.shading.value" :key="'sh' + i" class="shade" :class="s.type" :x="s.x" y="0" :width="s.width" :height="chart.innerH.value" />

        <g v-for="(row, i) in rows" :key="row.driver" class="fade" :class="{ dim: chart.dimmed(row.driver) }">
          <text class="driver-label" x="-8" :y="i * ROW + ROW / 2" text-anchor="end" dominant-baseline="central" @click="chart.pick(row.driver)">{{ row.driver }}</text>
          <rect
            v-for="s in row.stints"
            :key="s.startLap"
            class="tyre-fill stint"
            :class="tyreClass(s.compound)"
            :x="chart.x.value(s.startLap - 1) + 1"
            :y="i * ROW + 3"
            :width="Math.max(1, chart.x.value(s.endLap) - chart.x.value(s.startLap - 1) - 2)"
            :height="ROW - 6"
            @pointermove="e => chart.showTip(e, stintTip(row, s))"
            @click="chart.pick(row.driver, s.isLast ? null : s.endLap)"
          />
        </g>

        <g :transform="`translate(0,${chart.innerH.value})`">
          <line class="axis-line" x1="0" :x2="chart.innerW.value" />
          <text v-for="n in chart.lapTicks.value" :key="n" class="axis-text" :x="chart.x.value(n)" y="14" text-anchor="middle">{{ n }}</text>
          <text class="axis-text" x="0" y="14">LAP</text>
        </g>
      </g>
    </svg>
  </ChartFrame>
</template>

<script setup>
import { computed } from 'vue'
import { useChart } from '@/composables/useChart'
import { tyreClass, tyreName, TYRE_LEGEND } from '@/lib/format'
import ChartFrame from './ChartFrame.vue'

const props = defineProps({
  drivers: { type: Array, required: true },    // driverList(), finishing order
  plan:    { type: Object, required: true },   // strategy()
  laps:    { type: Object, required: true },   // parseLaps()
})

const ROW = 18
const M = { top: 4, right: 8, bottom: 20, left: 40 }

const rows = computed(() => props.drivers.map(d => {
  const stints = props.plan[d.driver] || []
  return { driver: d.driver, stints: stints.map((s, i) => ({ ...s, isLast: i === stints.length - 1 })) }
}))
const chart = useChart({ margin: M, height: () => rows.value.length * ROW + M.top + M.bottom })

function stintTip(row, s) {
  const laps = s.endLap - s.startLap + 1
  const age = props.laps.drivers[row.driver].tyreLife[s.endLap]
  return [
    `${row.driver} · ${tyreName(s.compound)}`,
    `Laps ${s.startLap}–${s.endLap} (${laps} lap${laps > 1 ? 's' : ''})`,
    s.isLast ? `Tyre age at the end: ${age || '?'} laps` : `Pitted on lap ${s.endLap}, tyre age ${age || '?'} laps`,
  ]
}
</script>

<style scoped>
.stint { cursor: pointer; }
</style>
