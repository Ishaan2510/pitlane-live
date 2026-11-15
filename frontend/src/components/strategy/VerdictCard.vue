<template>
  <!-- The answer, always with its range. A low-confidence result is muted and says why. -->
  <section class="verdict" :class="{ muted, pending }" aria-live="polite" aria-label="Simulation result">
    <template v-if="result">
      <div class="v-head">
        <span class="v-kicker">VERDICT</span>
        <span class="conf-tag" :class="result.confidence.level">{{ result.confidence.level }} confidence</span>
      </div>

      <p class="v-line">{{ headline }}</p>
      <p class="v-range">{{ rangeLine }}</p>

      <!-- share of the simulations in each finishing position -->
      <ol v-if="bars.length > 1" class="v-bars" :aria-label="`Finishing position in ${runs} simulations`">
        <li v-for="b in bars" :key="b.pos" :class="{ real: b.pos === result.finish.real }" :title="`P${b.pos}: ${b.pct}% of simulations`">
          <span class="v-bar" :style="{ height: Math.max(2, b.share * 46) + 'px' }"></span>
          <span class="v-pos">P{{ b.pos }}</span>
          <span class="v-pct">{{ b.pct }}%</span>
        </li>
      </ol>

      <dl class="v-facts">
        <div>
          <dt>RACE TIME</dt>
          <dd>{{ timeLine }}</dd>
          <dd v-if="!result.isActual" class="sub">80% of simulations: {{ fmtGap(result.time.p10, 1) }} to {{ fmtGap(result.time.p90, 1) }} s</dd>
        </div>
        <div>
          <dt>STOPS</dt>
          <dd>{{ stopsLine }}</dd>
          <dd class="sub">really {{ realStopsLine }}</dd>
        </div>
      </dl>

      <p class="v-why"><strong>{{ muted ? 'Why this is muted:' : 'Confidence:' }}</strong> {{ result.confidence.reason }}</p>
      <ul v-if="notes.length" class="v-flags">
        <li v-for="(f, i) in notes" :key="i" :class="f.level">{{ f.text }}</li>
      </ul>
      <p v-if="result.retiredAt" class="v-flags-note">{{ driver }} retired on lap {{ result.retiredAt + 1 }}, so the simulation stops at the end of lap {{ result.retiredAt }}: positions are the place at that point, not a finish.</p>
    </template>
    <div v-else class="skeleton-stack" aria-busy="true"><div class="skeleton" v-for="i in 4" :key="i"></div></div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { fmtGap } from '@/lib/format'
import { SIM_RUNS } from '@/lib/strategySim'

const props = defineProps({
  result:  { type: Object, default: null },     // simulate() result
  driver:  { type: String, required: true },
  pending: { type: Boolean, default: false },   // a newer simulation is running
})

const runs = SIM_RUNS
const muted = computed(() => props.result?.confidence.level === 'low')
const f = computed(() => props.result.finish)
const verb = computed(() => (props.result.retiredAt ? 'is' : 'finishes'))

const headline = computed(() => {
  const r = props.result
  if (r.isActual) return `${props.driver} ${r.retiredAt ? 'was' : 'finished'} P${f.value.real}`
  if (f.value.alt === f.value.real) return `${props.driver} still ${verb.value} P${f.value.real}`
  return `${props.driver} ${verb.value} P${f.value.alt}, not P${f.value.real}`
})
const rangeLine = computed(() => {
  const r = props.result
  if (r.isActual) return 'This is the race as it happened. Move a stop or change a tyre to ask a question.'
  if (f.value.p10 === f.value.p90) return `P${f.value.p10} in at least 80% of ${runs} simulations`
  return `P${f.value.p10} to P${f.value.p90} in 80% of ${runs} simulations`
})
const bars = computed(() => Object.entries(f.value.shares)
  .map(([pos, share]) => ({ pos: +pos, share, pct: share < 0.005 ? '<1' : Math.round(share * 100) }))
  .sort((a, b) => a.pos - b.pos))

const timeLine = computed(() => {
  const d = props.result.time.p50
  if (props.result.isActual) return 'As raced'
  if (Math.abs(d) < 0.05) return 'No change'
  return `${Math.abs(d).toFixed(1)} s ${d < 0 ? 'quicker' : 'slower'} than the real race`
})
const lapsText = laps => (laps.length ? `lap ${laps.join(', ')}` : 'no stop')
const stopsLine = computed(() => lapsText(props.result.stops.alt))
const realStopsLine = computed(() => lapsText(props.result.stops.real))

// the confidence reason already carries the flag that set it: do not say it twice
const notes = computed(() => props.result.flags.filter(x => x.text !== props.result.confidence.reason))
</script>

<style scoped>
.verdict { border: 1px solid var(--border-secondary); padding: 1rem 1.1rem; min-width: 0; transition: opacity var(--dur-base) var(--ease); }
.verdict.pending { opacity: 0.6; }
.v-head { display: flex; align-items: center; justify-content: space-between; gap: 0.75rem; }
.v-kicker { font-family: 'DM Mono', monospace; font-size: 0.6rem; letter-spacing: 0.2em; color: var(--accent-hover); }
.v-line { margin-top: 0.5rem; font-family: 'Bebas Neue', sans-serif; font-size: clamp(2rem, 5vw, 3.2rem); line-height: 1; letter-spacing: 0.03em; color: var(--text-primary); text-transform: uppercase; }
.v-range { margin-top: 0.35rem; font-family: 'DM Mono', monospace; font-size: 0.74rem; letter-spacing: 0.06em; color: var(--text-primary); }
.muted .v-line { color: var(--text-secondary); }
.muted .v-range { color: var(--text-secondary); }

.v-bars { display: flex; align-items: flex-end; gap: 4px; list-style: none; margin-top: 0.9rem; min-height: 78px; overflow-x: auto; }
.v-bars li { display: grid; justify-items: center; gap: 2px; min-width: 30px; font-family: 'DM Mono', monospace; }
.v-bar { width: 22px; background: var(--text-primary); }
.muted .v-bar { background: var(--text-muted); }
.v-bars li.real .v-pos { color: var(--accent-hover); }
.v-pos { font-size: 0.6rem; color: var(--text-primary); }
.v-pct { font-size: 0.54rem; color: var(--text-secondary); }

.v-facts { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1px; margin-top: 0.9rem; background: var(--border-primary); border: 1px solid var(--border-primary); }
.v-facts div { background: var(--bg-primary); padding: 0.55rem 0.7rem; min-width: 0; }
.v-facts dt { font-family: 'DM Mono', monospace; font-size: 0.54rem; letter-spacing: 0.16em; color: var(--text-secondary); }
.v-facts dd { font-family: 'Work Sans', sans-serif; font-size: 0.88rem; color: var(--text-primary); }
.v-facts dd.sub { font-size: 0.72rem; color: var(--text-secondary); }

.v-why, .v-flags, .v-flags-note { margin-top: 0.7rem; font-family: 'Work Sans', sans-serif; font-size: 0.8rem; line-height: 1.45; color: var(--text-secondary); }
.v-why strong { font-weight: 600; color: var(--text-primary); }
.v-flags { list-style: none; display: grid; gap: 0.3rem; }
.v-flags li { padding-left: 0.6rem; border-left: 2px solid var(--status-vsc); }
.v-flags li.error { border-left-color: var(--status-red); color: var(--text-primary); }

@media (max-width: 480px) {
  .v-facts { grid-template-columns: minmax(0, 1fr); }
}
</style>
