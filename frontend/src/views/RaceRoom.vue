<template>
  <div class="race-room">
    <div v-if="loading" class="rr-wrap" aria-busy="true" aria-label="Loading race">
      <div class="skeleton rr-skel-title"></div>
      <div class="skeleton-stack"><div class="skeleton" v-for="i in 6" :key="i"></div></div>
    </div>

    <div v-else-if="!event" class="rr-wrap">
      <StatePanel
        :label="loadError ? 'Race unavailable' : 'Race not found'"
        :text="loadError ? 'The race list could not be loaded.' : `There is no built race for round ${round} of ${year}.`"
        action="Race library"
        to="/replay"
      />
    </div>

    <template v-else>
      <header class="rr-head">
        <div class="rr-id">
          <div class="rr-label">ROUND {{ event.round }} · {{ event.year }}</div>
          <h1 class="rr-name">{{ event.name }}</h1>
          <div class="rr-meta">
            <span>{{ event.location }}, {{ event.country }} · {{ formatDate(event.date) }}</span>
            <span v-for="tag in coverageTags(event)" :key="tag" class="cov-tag">{{ tag }}</span>
          </div>
        </div>

        <ol v-if="podium.length" class="rr-podium" aria-label="Podium">
          <li v-for="p in podium" :key="p.driver" :class="{ winner: p.position === 1 }">
            <span class="pod-pos">{{ p.position === 1 ? 'WINNER' : 'P' + p.position }}</span>
            <span class="pod-code" :style="{ borderColor: p.team_color }">{{ p.driver }}</span>
            <span class="pod-team">{{ p.team }}</span>
          </li>
        </ol>

        <div class="rr-actions">
          <component
            :is="older ? 'router-link' : 'span'"
            :to="older ? raceLink(older) : undefined"
            class="rr-btn icon"
            :class="{ disabled: !older }"
            :aria-label="older ? `Previous race: ${older.name} ${older.year}` : undefined"
            :aria-hidden="older ? undefined : 'true'"
            :title="older ? `${older.name} ${older.year}` : ''"
          >
            <svg viewBox="0 0 12 12" aria-hidden="true"><path d="M7.5 2 3.5 6l4 4" /></svg>
          </component>
          <component
            :is="newer ? 'router-link' : 'span'"
            :to="newer ? raceLink(newer) : undefined"
            class="rr-btn icon"
            :class="{ disabled: !newer }"
            :aria-label="newer ? `Next race: ${newer.name} ${newer.year}` : undefined"
            :aria-hidden="newer ? undefined : 'true'"
            :title="newer ? `${newer.name} ${newer.year}` : ''"
          >
            <svg viewBox="0 0 12 12" aria-hidden="true"><path d="M4.5 2l4 4-4 4" /></svg>
          </component>
          <button type="button" class="rr-btn" aria-label="Copy link to this race" @click="copyLink">
            <svg viewBox="0 0 12 12" aria-hidden="true"><path d="M5 7l2-2M4.2 5.3 2.9 6.6a1.8 1.8 0 0 0 2.5 2.5l1.3-1.3M7.8 6.7l1.3-1.3a1.8 1.8 0 0 0-2.5-2.5L5.3 4.2" /></svg>
            <span aria-live="polite">{{ copied ? 'COPIED' : 'COPY LINK' }}</span>
          </button>
        </div>
      </header>

      <nav class="rr-tabs" aria-label="Race Room sections">
        <router-link
          v-for="t in TABS"
          :key="t.id"
          :to="tabLink(t)"
          class="rr-tab"
          :class="{ active: t.id === tab.id }"
          :aria-current="t.id === tab.id ? 'page' : undefined"
        >{{ t.label }}</router-link>
      </nav>

      <component
        :is="tab.component"
        :key="`${year}-${round}-${tab.id}`"
        :year="year"
        :round="round"
        :event="event"
        :results="results"
      />
    </template>
  </div>
</template>

<script setup>
import { computed, defineAsyncComponent, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getRaces, getResults, coverageTags } from '@/services/data'
import StatePanel from '@/components/StatePanel.vue'

// One entry per tab. To add a tab (e.g. Strategy Lab), add one line: the id is the last
// URL segment (/race/:year/:round/:id) and the component gets { year, round, event, results }.
const TABS = [
  { id: 'replay',  label: 'Replay',  component: defineAsyncComponent(() => import('@/components/race/ReplayTab.vue')) },
  { id: 'debrief', label: 'Debrief', component: defineAsyncComponent(() => import('@/components/race/DebriefTab.vue')) },
  { id: 'strategy', label: 'Strategy', component: defineAsyncComponent(() => import('@/components/race/StrategyTab.vue')) },
]

const route = useRoute()
const year  = computed(() => parseInt(route.params.year, 10))
const round = computed(() => parseInt(route.params.round, 10))
const tab   = computed(() => TABS.find(t => t.id === route.params.tab) || TABS[0])

const races     = ref([])     // newest first
const results   = ref(null)   // race classification, null when it could not be loaded
const loading   = ref(true)
const loadError = ref(false)

const index  = computed(() => races.value.findIndex(r => r.year === year.value && r.round === round.value))
const event  = computed(() => races.value[index.value] || null)
const newer  = computed(() => (index.value > 0 ? races.value[index.value - 1] : null))
const older  = computed(() => (index.value >= 0 ? races.value[index.value + 1] || null : null))
const podium = computed(() => (results.value || []).filter(r => r.position <= 3).slice(0, 3))

const raceLink = r => `/race/${r.year}/${r.round}`
const tabLink  = t => `/race/${year.value}/${round.value}${t === TABS[0] ? '' : '/' + t.id}`

watch([year, round], async () => {
  loading.value = true
  loadError.value = false
  results.value = null
  const wanted = `${year.value}/${round.value}`
  try {
    const [list, res] = await Promise.all([
      getRaces(),
      getResults(year.value, round.value).catch(() => null),
    ])
    if (wanted !== `${year.value}/${round.value}`) return   // navigated on while loading
    races.value   = list
    results.value = res
  } catch (e) {
    console.error(e)
    loadError.value = true
  } finally {
    loading.value = false
  }
}, { immediate: true })

const copied = ref(false)
async function copyLink() {
  try {
    await navigator.clipboard.writeText(window.location.href)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  } catch { /* clipboard blocked: the URL is still in the address bar */ }
}

function formatDate(d) {
  return new Date(d + 'T00:00:00Z').toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' }).toUpperCase()
}
</script>

<style scoped>
.race-room { min-height: calc(100vh - 56px); background: var(--bg-primary); color: var(--text-primary); }
.rr-wrap { max-width: 900px; margin: 0 auto; padding: 3rem 1.5rem; }
.rr-skel-title { height: 3rem; width: min(26rem, 80%); margin-bottom: 1.5rem; }

.rr-head {
  display: grid;
  grid-template-columns: 1fr auto auto;
  align-items: end;
  gap: 1rem 2rem;
  padding: 0.9rem 1.5rem 0.8rem;
  border-bottom: 1px solid var(--border-primary);
}
.rr-label, .rr-meta, .pod-pos, .pod-team, .rr-btn, .rr-tab {
  font-family: 'DM Mono', monospace;
  text-transform: uppercase;
}
.rr-label { font-size: 0.62rem; letter-spacing: 0.2em; color: var(--accent-hover); }   /* the brighter red: small text needs the contrast */
.rr-name {
  font-family: 'Bebas Neue', sans-serif;
  font-weight: 400;
  font-size: clamp(1.8rem, 3.2vw, 2.5rem);
  letter-spacing: 0.03em;
  line-height: 1;
  margin: 0.2rem 0 0.35rem;
}
.rr-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem 0.5rem;
  font-size: 0.66rem;
  letter-spacing: 0.1em;
  color: var(--text-secondary);
}

.rr-podium { display: flex; gap: 1.25rem; list-style: none; }
.rr-podium li { display: grid; gap: 0.15rem; }
.pod-pos  { font-size: 0.55rem; letter-spacing: 0.18em; color: var(--text-secondary); }
.winner .pod-pos { color: var(--accent-hover); }
.pod-code {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 1.5rem;
  line-height: 1;
  letter-spacing: 0.05em;
  padding-left: 0.4rem;
  border-left: 3px solid var(--border-secondary);   /* team colour set inline */
}
.pod-team { font-size: 0.55rem; letter-spacing: 0.08em; color: var(--text-secondary); white-space: nowrap; }

.rr-actions { display: flex; gap: 0.35rem; }
.rr-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  height: 32px;
  padding: 0 0.75rem;
  background: none;
  border: 1px solid var(--border-secondary);
  color: var(--text-primary);
  font-size: 0.6rem;
  letter-spacing: 0.14em;
  text-decoration: none;
  cursor: pointer;
  transition: border-color var(--dur-base) var(--ease), color var(--dur-base) var(--ease), scale var(--dur-fast) var(--ease);
}
.rr-btn.icon { width: 32px; padding: 0; justify-content: center; }
.rr-btn:hover { border-color: var(--accent); color: var(--accent); }
.rr-btn.disabled { opacity: 0.3; pointer-events: none; }
.rr-btn svg { width: 12px; height: 12px; fill: none; stroke: currentColor; stroke-width: 1.3; stroke-linecap: round; stroke-linejoin: round; }

.rr-tabs {
  display: flex;
  gap: 1.75rem;
  padding: 0 1.5rem;
  border-bottom: 1px solid var(--border-primary);
}
.rr-tab {
  padding: 0.65rem 0 0.55rem;
  font-size: 0.68rem;
  letter-spacing: 0.18em;
  color: var(--text-secondary);
  text-decoration: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  transition: color var(--dur-base) var(--ease), border-color var(--dur-base) var(--ease);
}
.rr-tab:hover  { color: var(--text-primary); }
.rr-tab.active { color: var(--text-primary); border-bottom-color: var(--accent); }

@media (max-width: 900px) {
  .rr-head { grid-template-columns: 1fr auto; padding: 1rem; }
  .rr-podium { grid-column: 1 / -1; grid-row: 2; }
  .rr-actions { grid-column: 2; grid-row: 1; align-self: start; }
  .rr-tabs { padding: 0 1rem; }
}
@media (max-width: 480px) {
  .rr-btn:not(.icon) span { display: none; }
  .rr-btn:not(.icon) { width: 32px; padding: 0; justify-content: center; }
  .pod-team { display: none; }
}
</style>
