<template>
  <div class="home">
    <!-- Hero -->
    <section class="hero">
      <div class="container">
        <h1 class="hero-title">
          Predict race<br/>strategy in<br/>real-time
        </h1>
        <p class="hero-subtitle">
          Compete against thousands using authentic F1 telemetry data
        </p>
        <div class="hero-actions">
          <button @click="scrollToRaces" class="btn-primary">Get Started</button>
          <router-link to="/replay" class="btn-secondary">View Replays</router-link>
        </div>
      </div>
    </section>

    <!-- Races -->
    <section class="races" ref="racesSection">
      <div class="container">
        <div class="section-header">
          <h2 class="section-title">Races</h2>
          <p class="section-subtitle">2025 Season</p>
        </div>

        <div v-if="loading" class="loading">Loading...</div>

        <div v-else class="race-grid">
          <div
            v-for="race in races"
            :key="race.id"
            class="race-card"
            @click="goToRace(race.id)"
          >
            <div class="race-status" :class="race.status">
              {{ race.status }}
            </div>
            <h3 class="race-name">{{ race.name }}</h3>
            <p class="race-circuit">{{ race.circuit }}</p>
            <div class="race-meta">
              <span>{{ formatDate(race.date) }}</span>
              <span>{{ race.laps }} laps</span>
            </div>
            
            <div v-if="race.currentLap" class="race-live">
              <span>Lap {{ race.currentLap }}/{{ race.laps }}</span>
              <div class="progress">
                <div 
                  class="progress-bar" 
                  :style="{ width: ((race.currentLap / race.laps) * 100) + '%' }"
                ></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script>
import api from '../services/api.js'

export default {
  name: 'Home',
  data() {
    return {
      races: [],
      loading: true
    }
  },
  async mounted() {
    await this.loadRaces()
  },
  methods: {
    async loadRaces() {
      try {
        this.races = await api.getRaces()
      } catch (error) {
        console.error(error)
      } finally {
        this.loading = false
      }
    },
    formatDate(dateStr) {
      const date = new Date(dateStr)
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    },
    goToRace(id) {
      this.$router.push(`/race/${id}`)
    },
    scrollToRaces() {
      this.$refs.racesSection.scrollIntoView({ behavior: 'smooth' })
    }
  }
}
</script>

<style scoped>
.container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 4rem;
}

/* Hero */
.hero {
  min-height: 90vh;
  display: flex;
  align-items: center;
  position: relative;
}

.hero-title {
  font-family: var(--font-display);
  font-size: clamp(4rem, 10vw, 8rem);
  line-height: 0.95;
  letter-spacing: -0.02em;
  margin-bottom: 2rem;
}

.hero-subtitle {
  font-size: 1.25rem;
  color: var(--color-muted);
  max-width: 500px;
  margin-bottom: 3rem;
  font-weight: 300;
}

.hero-actions {
  display: flex;
  gap: 1.5rem;
}

.btn-primary {
  padding: 1rem 2rem;
  background: var(--color-fg);
  color: var(--color-bg);
  border: none;
  font-family: var(--font-body);
  font-size: 0.95rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s var(--ease);
}

.btn-primary:hover {
  background: var(--color-accent);
  color: white;
}

.btn-secondary {
  padding: 1rem 2rem;
  background: transparent;
  color: var(--color-fg);
  border: 1px solid var(--color-border);
  font-size: 0.95rem;
  font-weight: 500;
  text-decoration: none;
  display: inline-block;
  transition: all 0.3s var(--ease);
}

.btn-secondary:hover {
  border-color: var(--color-fg);
}

/* Races */
.races {
  padding: 8rem 0;
}

.section-header {
  margin-bottom: 4rem;
}

.section-title {
  font-family: var(--font-display);
  font-size: 3rem;
  letter-spacing: -0.02em;
}

.section-subtitle {
  color: var(--color-muted);
  font-size: 1rem;
}

.loading {
  text-align: center;
  padding: 4rem;
  color: var(--color-muted);
}

.race-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 2rem;
}

.race-card {
  padding: 2rem;
  border: 1px solid var(--color-border);
  cursor: pointer;
  transition: all 0.3s var(--ease);
}

.race-card:hover {
  border-color: var(--color-fg);
  transform: translateY(-4px);
}

.race-status {
  display: inline-block;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  padding: 0.25rem 0.75rem;
  margin-bottom: 1rem;
  font-weight: 500;
}

.race-status.live {
  background: var(--color-accent);
  color: white;
}

.race-status.upcoming {
  background: rgba(255, 255, 255, 0.1);
  color: var(--color-muted);
}

.race-status.completed {
  background: rgba(255, 255, 255, 0.05);
  color: var(--color-muted);
}

.race-name {
  font-family: var(--font-display);
  font-size: 1.75rem;
  letter-spacing: -0.01em;
  margin-bottom: 0.5rem;
}

.race-circuit {
  color: var(--color-muted);
  font-size: 0.9rem;
  margin-bottom: 1.5rem;
}

.race-meta {
  display: flex;
  gap: 1.5rem;
  font-size: 0.85rem;
  color: var(--color-muted);
}

.race-live {
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid var(--color-border);
}

.race-live span {
  display: block;
  font-size: 0.85rem;
  margin-bottom: 0.5rem;
  color: var(--color-muted);
}

.progress {
  height: 2px;
  background: rgba(255, 255, 255, 0.1);
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: var(--color-accent);
  transition: width 0.3s var(--ease);
}
</style>
