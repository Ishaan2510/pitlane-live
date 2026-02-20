<template>
  <div class="race-replay">
    <ToastNotification :toasts="toasts" @remove="removeToast" />

    <!-- Race Selector -->
    <div v-if="!selectedRace" class="selector">
      <div class="container">
        <h1 class="page-title">Race Replay</h1>
        <p class="page-subtitle">Select a race to replay with real F1 telemetry data</p>

        <div v-if="loadingRaces" class="loading">Loading races...</div>

        <div v-else class="race-list">
          <div
            v-for="race in availableRaces"
            :key="race.round"
            class="race-item"
            @click="selectRace(race)"
          >
            <div class="race-round">R{{ race.round }}</div>
            <div class="race-details">
              <div class="race-name">{{ race.name }}</div>
              <div class="race-location">{{ race.location }}</div>
            </div>
            <div class="race-date">{{ formatDate(race.date) }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Race Replay Interface -->
    <div v-else class="replay-interface">
      <!-- Top Bar -->
      <div class="top-bar">
        <button @click="backToSelector" class="back-btn">← Back</button>
        <div class="race-title">
          <span class="race-name">{{ raceData.name }}</span>
          <span class="race-circuit">{{ raceData.circuit }}</span>
        </div>
        <div class="lap-counter">
          Lap: <strong>{{ currentLap }}/{{ raceData.total_laps }}</strong>
        </div>
      </div>

      <!-- Main Layout -->
      <div class="main-layout">
        <!-- Left Sidebar: Weather + Leaderboard -->
        <div class="left-sidebar">
          <WeatherPanel :weather="weatherData" />
          
          <div class="leaderboard">
            <h4 class="section-title">Leaderboard</h4>
            <div
              v-for="driver in currentLapData ? currentLapData.drivers : []"
              :key="driver.driver"
              class="driver-item"
              :class="{ selected: selectedDriver === driver.driver }"
              @click="selectDriver(driver.driver)"
            >
              <div class="driver-pos">{{ driver.position }}</div>
              <div class="driver-code">{{ driver.driver }}</div>
              <div class="driver-tire" :class="driver.compound.toLowerCase()">
                {{ getTireEmoji(driver.compound) }}
              </div>
            </div>
          </div>
        </div>

        <!-- Center: Track Visualization -->
        <div class="track-area">
          <TrackCanvas
            :drivers="currentLapData ? currentLapData.drivers : []"
            :circuitData="circuitData"
            :selectedDriver="selectedDriver"
            @select-driver="selectDriver"
          />
          
          <!-- Controls -->
          <div class="controls">
            <button @click="replayRunning ? pause() : play()" class="control-btn primary">
              {{ replayRunning ? '⏸' : '▶' }}
            </button>
            <button @click="previousLap" :disabled="currentLap <= 1" class="control-btn">
              ⏮
            </button>
            <button @click="nextLap" :disabled="currentLap >= raceData.total_laps" class="control-btn">
              ⏭
            </button>
            <select v-model.number="playbackSpeed" class="speed-select">
              <option :value="500">0.5x</option>
              <option :value="1000">1x</option>
              <option :value="2000">2x</option>
              <option :value="4000">4x</option>
              <option :value="8000">8x</option>
            </select>
            <button @click="restart" class="control-btn">
              ↻ Restart
            </button>
          </div>
        </div>

        <!-- Right Sidebar: Telemetry -->
        <div class="right-sidebar">
          <TelemetryPanel :driver="selectedDriverData" />
        </div>
      </div>

      <!-- Bottom Progress Bar -->
      <ProgressBar
        :currentLap="currentLap"
        :totalLaps="raceData.total_laps"
      />
    </div>
  </div>
</template>

<script>
import api from '../services/api.js'
import { useToast } from '../composables/useToast.js'
import ToastNotification from '../components/ToastNotification.vue'
import TrackCanvas from '../components/TrackCanvas.vue'
import WeatherPanel from '../components/WeatherPanel.vue'
import TelemetryPanel from '../components/TelemetryPanel.vue'
import ProgressBar from '../components/ProgressBar.vue'

export default {
  name: 'RaceReplay',
  components: {
    ToastNotification,
    TrackCanvas,
    WeatherPanel,
    TelemetryPanel,
    ProgressBar
  },

  setup() {
    const { toasts, remove: removeToast, show } = useToast()
    return { toasts, removeToast, showToast: show }
  },

  data() {
    return {
      loadingRaces: true,
      availableRaces: [],
      selectedRace: null,
      raceData: null,
      circuitData: null,
      weatherData: null,
      currentLap: 1,
      currentLapData: null,
      replayRunning: false,
      replayInterval: null,
      playbackSpeed: 1000,
      lastPitLap: {},
      selectedDriver: null
    }
  },

  computed: {
    selectedDriverData() {
      if (!this.selectedDriver || !this.currentLapData) return null
      return this.currentLapData.drivers.find(d => d.driver === this.selectedDriver)
    }
  },

  async mounted() {
    await this.loadAvailableRaces()
  },

  beforeUnmount() {
    this.pause()
  },

  methods: {
    async loadAvailableRaces() {
      try {
        this.availableRaces = await api.getAvailableReplays(2024)
      } catch (e) {
        console.error(e)
      } finally {
        this.loadingRaces = false
      }
    },

    async selectRace(race) {
      this.selectedRace = race
      this.showToast('Loading race data...')
      
      try {
        // Load race data
        this.raceData = await api.getReplayRaceData(race.year || 2024, race.round)
        
        // Load circuit data
        this.circuitData = await api.getCircuitData(race.year || 2024, race.round)
        
        // Load weather data
        this.weatherData = await api.getWeatherData(race.year || 2024, race.round)
        
        this.currentLap = 1
        this.lastPitLap = {}
        this.selectedDriver = null
        this.updateCurrentLap()
        
        this.showToast('Race loaded successfully')
      } catch (e) {
        console.error(e)
        this.showToast('Failed to load race data')
        this.selectedRace = null
      }
    },

    backToSelector() {
      this.pause()
      this.selectedRace = null
      this.raceData = null
      this.circuitData = null
      this.weatherData = null
      this.currentLap = 1
      this.selectedDriver = null
    },

    updateCurrentLap() {
      if (!this.raceData || this.currentLap > this.raceData.laps.length) return
      
      this.currentLapData = this.raceData.laps[this.currentLap - 1]
      
      // Show pit stop toasts (prevent spam)
      this.currentLapData.drivers.forEach(driver => {
        const key = driver.driver
        const prevPitLap = this.lastPitLap[key] || 0
        
        if (driver.pit_out && prevPitLap !== this.currentLap) {
          this.showToast(`${driver.driver} → ${driver.compound}`)
          this.lastPitLap[key] = this.currentLap
        }
      })
    },

    play() {
      this.replayRunning = true
      this.replayInterval = setInterval(() => {
        if (this.currentLap >= this.raceData.total_laps) {
          this.pause()
          this.showToast('Race finished!')
        } else {
          this.nextLap()
        }
      }, this.playbackSpeed)
    },

    pause() {
      this.replayRunning = false
      clearInterval(this.replayInterval)
    },

    nextLap() {
      if (this.currentLap < this.raceData.total_laps) {
        this.currentLap++
        this.updateCurrentLap()
      }
    },

    previousLap() {
      if (this.currentLap > 1) {
        this.currentLap--
        this.updateCurrentLap()
      }
    },

    restart() {
      this.pause()
      this.currentLap = 1
      this.updateCurrentLap()
      this.showToast('Restarted')
    },

    selectDriver(driverCode) {
      this.selectedDriver = this.selectedDriver === driverCode ? null : driverCode
    },

    getTireEmoji(compound) {
      const emojis = {
        'SOFT': '🔴',
        'MEDIUM': '🟡',
        'HARD': '⚪'
      }
      return emojis[compound] || '⚫'
    },

    formatDate(dateStr) {
      if (!dateStr) return 'TBD'
      const date = new Date(dateStr)
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
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

/* ═══ Selector ═══ */
.selector {
  padding: 4rem 0;
}

.page-title {
  font-family: var(--font-display);
  font-size: 3rem;
  letter-spacing: -0.02em;
  margin-bottom: 0.5rem;
}

.page-subtitle {
  color: var(--color-muted);
  margin-bottom: 3rem;
}

.loading {
  text-align: center;
  padding: 4rem;
  color: var(--color-muted);
}

.race-list {
  display: grid;
  gap: 1px;
  background: var(--color-border);
  border: 1px solid var(--color-border);
}

.race-item {
  display: grid;
  grid-template-columns: 80px 1fr 150px;
  align-items: center;
  padding: 1.5rem 2rem;
  background: var(--color-bg);
  cursor: pointer;
  transition: all 0.2s var(--ease);
}

.race-item:hover {
  background: rgba(255, 255, 255, 0.02);
}

.race-round {
  font-family: var(--font-display);
  font-size: 1.5rem;
  color: var(--color-muted);
}

.race-name {
  font-weight: 500;
  margin-bottom: 0.25rem;
}

.race-location {
  font-size: 0.85rem;
  color: var(--color-muted);
}

.race-date {
  text-align: right;
  color: var(--color-muted);
  font-size: 0.9rem;
}

/* ═══ Replay Interface ═══ */
.replay-interface {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #0a0a0a;
}

.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 2rem;
  border-bottom: 1px solid var(--color-border);
  background: rgba(10, 10, 10, 0.95);
}

.back-btn {
  padding: 0.5rem 1rem;
  background: transparent;
  border: 1px solid var(--color-border);
  color: var(--color-fg);
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.2s;
}

.back-btn:hover {
  border-color: var(--color-fg);
}

.race-title {
  flex: 1;
  text-align: center;
}

.race-title .race-name {
  font-family: var(--font-display);
  font-size: 1.25rem;
  margin-right: 1rem;
}

.race-title .race-circuit {
  font-size: 0.85rem;
  color: var(--color-muted);
}

.lap-counter {
  font-size: 0.9rem;
  color: var(--color-muted);
}

.lap-counter strong {
  color: var(--color-fg);
}

/* Main Layout */
.main-layout {
  flex: 1;
  display: grid;
  grid-template-columns: 250px 1fr 300px;
  overflow: hidden;
}

/* Left Sidebar */
.left-sidebar {
  background: rgba(10, 10, 10, 0.95);
  border-right: 1px solid var(--color-border);
  padding: 1rem;
  overflow-y: auto;
}

.leaderboard {
  margin-top: 1rem;
}

.section-title {
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--color-muted);
  margin-bottom: 0.75rem;
}

.driver-item {
  display: grid;
  grid-template-columns: 40px 1fr 30px;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  margin-bottom: 0.5rem;
  border: 1px solid var(--color-border);
  cursor: pointer;
  transition: all 0.2s;
}

.driver-item:hover {
  background: rgba(255, 255, 255, 0.05);
}

.driver-item.selected {
  background: rgba(255, 255, 255, 0.1);
  border-color: var(--color-fg);
}

.driver-pos {
  font-family: var(--font-display);
  font-size: 1.25rem;
  text-align: center;
}

.driver-code {
  font-family: monospace;
  font-weight: 600;
}

.driver-tire {
  font-size: 1.25rem;
  text-align: center;
}

/* Track Area */
.track-area {
  display: flex;
  flex-direction: column;
  padding: 1rem;
}

.controls {
  display: flex;
  gap: 0.5rem;
  margin-top: 1rem;
}

.control-btn {
  padding: 0.75rem 1.5rem;
  background: transparent;
  border: 1px solid var(--color-border);
  color: var(--color-fg);
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.control-btn.primary {
  background: var(--color-fg);
  color: var(--color-bg);
  border-color: var(--color-fg);
}

.control-btn:hover:not(:disabled) {
  border-color: var(--color-fg);
}

.control-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.speed-select {
  padding: 0.75rem 1rem;
  background: transparent;
  border: 1px solid var(--color-border);
  color: var(--color-fg);
  font-size: 0.9rem;
  cursor: pointer;
}

/* Right Sidebar */
.right-sidebar {
  background: rgba(10, 10, 10, 0.95);
  border-left: 1px solid var(--color-border);
  padding: 1rem;
  overflow-y: auto;
}
</style>
