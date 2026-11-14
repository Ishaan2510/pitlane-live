<template>
  <div class="selector">
    <div class="container">
      <h1 class="page-title">Race Library</h1>
      <p class="page-subtitle">Pick a race to open its Race Room: replay and debrief from real timing data</p>

      <div class="year-selector">
        <button
          v-for="y in years"
          :key="y"
          class="year-btn"
          :class="{ active: selectedYear === y }"
          @click="selectedYear = y"
        >{{ y }}</button>
      </div>

      <div v-if="loading" class="skeleton-stack" aria-busy="true" aria-label="Loading races">
        <div class="skeleton" v-for="i in 8" :key="i"></div>
      </div>

      <StatePanel
        v-else-if="loadError"
        label="Library unavailable"
        text="The race list could not be loaded."
        action="Retry"
        @action="load"
      />
      <StatePanel
        v-else-if="!yearRaces.length"
        label="No races"
        :text="`No ${selectedYear} races have been built yet.`"
      />

      <div v-else class="race-list">
        <router-link
          v-for="race in yearRaces"
          :key="race.round"
          :to="`/race/${race.year}/${race.round}`"
          class="race-item"
        >
          <div class="race-round">R{{ race.round }}</div>
          <div class="race-details">
            <div class="race-name-text">{{ race.name }}</div>
            <div class="race-location">{{ race.location }}, {{ race.country }}</div>
            <div class="race-coverage">
              <span v-for="tag in coverageTags(race)" :key="tag" class="cov-tag">{{ tag }}</span>
            </div>
          </div>
          <div class="race-date">
            {{ formatDate(race.date) }}
            <span class="ready-badge">OPEN →</span>
          </div>
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { getRaces, coverageTags } from '@/services/data'
import StatePanel from '@/components/StatePanel.vue'

const races        = ref([])
const loading      = ref(true)
const loadError    = ref(false)
const selectedYear = ref(null)

const years     = computed(() => [...new Set(races.value.map(r => r.year))].sort())
const yearRaces = computed(() => races.value
  .filter(r => r.year === selectedYear.value)
  .sort((a, b) => a.round - b.round))

async function load() {
  loading.value   = true
  loadError.value = false
  try {
    races.value = await getRaces()
    selectedYear.value ??= races.value[0]?.year ?? null   // newest season first
  } catch (e) {
    console.error(e)
    loadError.value = true
  } finally {
    loading.value = false
  }
}
onMounted(load)

function formatDate(dateStr) {
  if (!dateStr) return 'TBD'
  return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}
</script>

<style scoped>
.container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 4rem;
}
.selector { padding: 4rem 0; }

.page-title {
  font-family: var(--font-display);
  font-size: 3rem;
  letter-spacing: 0.02em;
  margin-bottom: 0.5rem;
  color: var(--text-primary);
}
.page-subtitle {
  color: var(--text-secondary);
  margin-bottom: 2rem;
}

.year-selector {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 2rem;
}
.year-btn {
  padding: 0.45rem 1.4rem;
  background: transparent;
  border: 1px solid var(--border-primary);
  color: var(--text-secondary);
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: border-color var(--dur-fast) var(--ease), color var(--dur-fast) var(--ease), scale var(--dur-fast) var(--ease);
}
.year-btn:hover  { border-color: var(--text-primary); color: var(--text-primary); }
.year-btn.active { background: var(--text-primary); color: var(--bg-primary); border-color: var(--text-primary); }

.race-list {
  display: grid;
  gap: 1px;
  background: var(--border-primary);
  border: 1px solid var(--border-primary);
}
.race-item {
  display: grid;
  grid-template-columns: 80px 1fr 150px;
  align-items: center;
  padding: 1.25rem 2rem;
  background: var(--bg-primary);
  color: inherit;
  text-decoration: none;
  transition: background var(--dur-fast) var(--ease);
}
.race-item:hover    { background: var(--bg-secondary); }
.race-round         { font-family: var(--font-display); font-size: 1.5rem; color: var(--text-secondary); }
.race-name-text     { font-weight: 500; margin-bottom: 0.2rem; color: var(--text-primary); }
.race-location      { font-size: 0.82rem; color: var(--text-secondary); }
.race-date          { text-align: right; color: var(--text-secondary); font-size: 0.9rem; }
.race-coverage      { display: flex; gap: 0.3rem; margin-top: 0.45rem; }
.ready-badge        { color: var(--accent); font-size: 0.72rem; font-weight: 700; margin-left: 0.5rem; white-space: nowrap; }

@media (max-width: 720px) {
  .container  { padding: 0 1rem; }
  .selector   { padding: 2rem 0; }
  .page-title { font-size: 2.2rem; }
  .race-item  { grid-template-columns: 44px 1fr auto; padding: 0.9rem 0.75rem; gap: 0.5rem; }
  .race-round { font-size: 1.15rem; }
  .ready-badge { display: block; margin: 0.2rem 0 0; }
}
</style>
