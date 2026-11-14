<template>
  <!-- The frame every Debrief chart sits in: title, one-line caption, an "i" note on
       how it was computed, the hover tooltip and the "Open in replay" action. -->
  <section class="chart-frame">
    <header class="cf-head">
      <h3 class="cf-title">{{ title }}</h3>
      <details class="cf-note">
        <summary aria-label="How this was computed" title="How this was computed">i</summary>
        <p>{{ note }}</p>
      </details>
      <p class="cf-caption">{{ caption }}</p>
      <div v-if="$slots.controls" class="cf-controls"><slot name="controls" /></div>
    </header>

    <p v-if="empty" class="cf-empty">{{ empty }}</p>
    <div v-else :ref="chart ? chart.el : undefined" class="cf-body" @pointerleave="chart?.hideTip()">
      <slot />
      <div v-if="chart?.tip.value" class="cf-tip" :style="{ left: chart.tip.value.left + 'px', top: chart.tip.value.top + 'px' }" role="status">
        <div v-for="(line, i) in chart.tip.value.lines" :key="i" :class="{ first: i === 0 }">{{ line }}</div>
      </div>
    </div>

    <div v-if="chart?.picked.value" class="cf-action">
      <span>{{ chart.picked.value.driver }} · LAP {{ chart.picked.value.lap }}</span>
      <router-link :to="chart.debrief.replayLink(chart.picked.value.lap, chart.picked.value.driver)" class="cf-link">
        OPEN IN REPLAY AT LAP {{ chart.picked.value.lap }} →
      </router-link>
    </div>
  </section>
</template>

<script setup>
defineProps({
  title:   { type: String, required: true },
  caption: { type: String, required: true },
  note:    { type: String, required: true },
  chart:   { type: Object, default: null },   // useChart() result
  empty:   { type: String, default: '' },     // shown instead of the chart when there is nothing to draw
})
</script>

<style scoped>
.chart-frame { border: 1px solid var(--border-primary); background: var(--bg-primary); padding: 1rem 1rem 0.85rem; min-width: 0; }

.cf-head { display: grid; grid-template-columns: 1fr auto; column-gap: 0.75rem; align-items: start; margin-bottom: 0.75rem; }
.cf-title { font-family: 'Bebas Neue', sans-serif; font-weight: 400; font-size: 1.35rem; letter-spacing: 0.05em; line-height: 1; color: var(--text-primary); }
.cf-caption { grid-column: 1 / -1; margin-top: 0.35rem; font-family: 'Work Sans', sans-serif; font-size: 0.8rem; line-height: 1.45; color: var(--text-secondary); }
.cf-controls { grid-column: 1 / -1; margin-top: 0.6rem; }

.cf-note { grid-column: 2; grid-row: 1; position: relative; }
.cf-note summary {
  list-style: none;
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border-secondary);
  color: var(--text-secondary);
  font-family: 'DM Mono', monospace;
  font-size: 0.7rem;
  cursor: pointer;
  user-select: none;
}
.cf-note summary::-webkit-details-marker { display: none; }
.cf-note[open] summary, .cf-note summary:hover { border-color: var(--accent); color: var(--accent); }
.cf-note p {
  position: absolute;
  right: 0;
  top: 28px;
  z-index: 5;
  width: min(300px, 78vw);
  padding: 0.7rem 0.8rem;
  background: var(--bg-card);
  border: 1px solid var(--border-secondary);
  font-family: 'Work Sans', sans-serif;
  font-size: 0.76rem;
  line-height: 1.5;
  color: var(--text-primary);
}

.cf-body { position: relative; min-width: 0; }
.cf-body > :deep(svg) { display: block; width: 100%; overflow: visible; }
.cf-empty { padding: 1.25rem 0; font-family: 'Work Sans', sans-serif; font-size: 0.85rem; color: var(--text-secondary); }

.cf-tip {
  position: absolute;
  z-index: 4;
  min-width: 120px;
  max-width: 220px;
  padding: 0.4rem 0.55rem;
  background: var(--bg-card);
  border: 1px solid var(--border-secondary);
  font-family: 'DM Mono', monospace;
  font-size: 0.66rem;
  line-height: 1.5;
  color: var(--text-secondary);
  pointer-events: none;
  white-space: nowrap;
}
.cf-tip .first { color: var(--text-primary); letter-spacing: 0.06em; }

.cf-action {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-top: 0.7rem;
  padding: 0.45rem 0.6rem;
  border: 1px solid var(--border-secondary);
  font-family: 'DM Mono', monospace;
  font-size: 0.64rem;
  letter-spacing: 0.12em;
  color: var(--text-secondary);
}
.cf-link { color: var(--accent); text-decoration: none; }
.cf-link:hover { text-decoration: underline; }

/* Shared SVG pieces (the charts' own elements are styled here so they all match) */
.cf-body :deep(.axis-text)  { font-family: 'DM Mono', monospace; font-size: 10px; fill: var(--text-secondary); }
.cf-body :deep(.axis-line)  { stroke: var(--border-primary); stroke-width: 1; }
.cf-body :deep(.grid-line)  { stroke: var(--border-primary); stroke-width: 1; }
.cf-body :deep(.shade.sc)   { fill: color-mix(in srgb, var(--status-sc) 22%, transparent); }
.cf-body :deep(.shade.vsc)  { fill: color-mix(in srgb, var(--status-vsc) 16%, transparent); }
.cf-body :deep(.shade.red)  { fill: color-mix(in srgb, var(--status-red) 30%, transparent); }
.cf-body :deep(.driver-label) { font-family: 'DM Mono', monospace; font-size: 10px; fill: var(--text-primary); cursor: pointer; }
.cf-body :deep(.dim) { opacity: 0.16; }
.cf-body :deep(.fade) { transition: opacity var(--dur-base) var(--ease); }
</style>
