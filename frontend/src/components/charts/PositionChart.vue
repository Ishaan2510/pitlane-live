<template>
  <LapLineChart
    title="Position chart"
    caption="Race position at the end of every lap, from the grid on the left to the flag on the right. Teammates share a colour: the lower finisher is dashed."
    note="Positions are the position column of laps.json; the starting point is grid_position from results.json (a pit-lane start has none). A line ends where the car retired. Shaded columns are Safety Car, VSC and red-flag laps."
    aria-label="Race position by lap for every driver"
    :drivers="drivers"
    :series="series"
    :y-domain="[0.5, count + 0.5]"
    :y-ticks="ticks"
    :format="p => 'P' + p"
    :height="Math.max(260, count * 19 + 28)"
  />
</template>

<script setup>
import { computed } from 'vue'
import LapLineChart from './LapLineChart.vue'

const props = defineProps({
  drivers: { type: Array, required: true },    // the drivers to draw
  series:  { type: Object, required: true },   // positionSeries()
  count:   { type: Number, required: true },   // cars in the race: the bottom of the axis
})

const ticks = computed(() => {
  const out = []
  for (let p = 1; p <= props.count; p++) out.push({ value: p, label: '' })
  return out
})
</script>
