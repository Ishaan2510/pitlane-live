<template>
  <div class="race-replay">
    <ToastNotification :toasts="toasts" @remove="removeToast" />

    <!-- ══ Race Selector ════════════════════════════════════════════════════ -->
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
              <div class="race-name-text">{{ race.name }}</div>
              <div class="race-location">{{ race.location }}</div>
            </div>
            <div class="race-date">{{ formatDate(race.date) }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- ══ Replay Interface ══════════════════════════════════════════════════ -->
    <div v-else class="replay-interface">

      <!-- Top Bar -->
      <div class="top-bar">
        <button @click="backToSelector" class="back-btn">← Back</button>
        <div class="race-title">
          <span class="race-name-label">{{ raceData.name }}</span>
          <span class="race-circuit">{{ raceData.circuit }}</span>
        </div>
        <div class="lap-counter">
          Lap: <strong>{{ currentLap }}/{{ raceData.total_laps }}</strong>
        </div>
      </div>

      <!-- 3-Column Main Layout -->
      <div class="main-layout">

        <!-- Left: Weather + Leaderboard -->
        <div class="left-sidebar">
          <WeatherPanel :weather="weatherData" />

          <div class="leaderboard">
            <h4 class="section-title">LEADERBOARD</h4>
            <div
              v-for="driver in currentDrivers"
              :key="driver.driver"
              class="driver-item"
              :class="{ selected: selectedDriver === driver.driver }"
              @click="selectDriver(driver.driver)"
            >
              <div class="driver-pos">{{ driver.position }}</div>
              <div class="driver-code">{{ driver.driver }}</div>
              <div class="driver-tire">{{ getTireEmoji(driver.compound) }}</div>
            </div>
          </div>
        </div>

        <!-- Centre: Track + Controls -->
        <div class="track-area">
          <TrackCanvas
            :drivers="currentDrivers"
            :circuitData="circuitData"
            :selectedDriver="selectedDriver"
            @select-driver="selectDriver"
          />

          <!-- Playback Controls -->
          <div class="controls">
            <button @click="togglePlay" class="control-btn primary">
              {{ replayRunning ? '⏸' : '▶' }}
            </button>
            <button @click="previousLap" :disabled="currentLap <= 1" class="control-btn">⏮</button>
            <button @click="nextLap" :disabled="currentLap >= raceData.total_laps" class="control-btn">⏭</button>

            <!--
              Speed selector — note the label↔value mapping:
              0.5× = 2000ms per lap (slow), 1× = 1000ms, 2× = 500ms (fast) …
              Higher ms value = slower playback.
            -->
            <select v-model.number="playbackSpeed" class="speed-select">
              <option :value="2000">0.5×</option>
              <option :value="1000">1×</option>
              <option :value="500">2×</option>
              <option :value="250">4×</option>
              <option :value="125">8×</option>
            </select>

            <button @click="restart" class="control-btn">↻ Restart</button>
          </div>
        </div>

        <!-- Right: Telemetry -->
        <div class="right-sidebar">
          <TelemetryPanel :driver="selectedDriverData" />
        </div>

      </div><!-- /.main-layout -->

      <!-- Bottom Progress -->
      <ProgressBar :currentLap="currentLap" :totalLaps="raceData.total_laps" />

    </div><!-- /.replay-interface -->
  </div>
</template>

<script>
import api from '../services/api.js'
import { useToast } from '../composables/useToast.js'
import ToastNotification from '../components/ToastNotification.vue'
import TrackCanvas        from '../components/TrackCanvas.vue'
import WeatherPanel       from '../components/WeatherPanel.vue'
import TelemetryPanel     from '../components/TelemetryPanel.vue'
import ProgressBar        from '../components/ProgressBar.vue'

export default {
  name: 'RaceReplay',
  components: { ToastNotification, TrackCanvas, WeatherPanel, TelemetryPanel, ProgressBar },

  setup() {
    const { toasts, remove: removeToast, show, pit } = useToast()
    return { toasts, removeToast, showToast: show, pitToast: pit }
  },

  data() {
    return {
      loadingRaces:   true,
      availableRaces: [],
      selectedRace:   null,
      raceData:       null,
      circuitData:    null,
      weatherData:    null,
      currentLap:     1,
      currentLapData: null,
      replayRunning:  false,
      replayInterval: null,
      // 1000ms = 1 lap per second = 1× speed
      playbackSpeed:  1000,
      lastPitLap:     {},
      selectedDriver: null
    }
  },

  computed: {
    currentDrivers() {
      if (!this.currentLapData?.drivers) return []
      return [...this.currentLapData.drivers]
        .filter(d => d.position != null)
        .sort((a, b) => a.position - b.position)
    },
    selectedDriverData() {
      if (!this.selectedDriver) return null
      return this.currentDrivers.find(d => d.driver === this.selectedDriver) || null
    }
  },

  watch: {
    // Restart the interval with the new speed while playback is running
    playbackSpeed(newMs) {
      if (this.replayRunning) {
        clearInterval(this.replayInterval)
        this.replayInterval = null
        this._startInterval(newMs)
      }
    }
  },

  async mounted() {
    await this.loadAvailableRaces()
  },

  beforeUnmount() {
    this.pause()
  },

  methods: {
    // ── Data loading ───────────────────────────────────────────────────────
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
      this.showToast('Loading race data…')

      try {
        this.raceData    = await api.getReplayRaceData(race.year || 2024, race.round)
        this.circuitData = await api.getCircuitData(race.year || 2024, race.round)
        this.weatherData = await api.getWeatherData(race.year || 2024, race.round)

        this.currentLap    = 1
        this.lastPitLap    = {}
        this.selectedDriver = null
        this.updateCurrentLap()

        // Auto-select P1 so right sidebar is never blank on first load
        if (this.currentDrivers.length) {
          this.selectedDriver = this.currentDrivers[0].driver
        }

        this.showToast('Race loaded ✓')
      } catch (e) {
        console.error(e)
        this.showToast('Failed to load race data')
        this.selectedRace = null
      }
    },

    backToSelector() {
      this.pause()
      Object.assign(this.$data, {
        selectedRace:   null,
        raceData:       null,
        circuitData:    null,
        weatherData:    null,
        currentLap:     1,
        currentLapData: null,
        replayRunning:  false,
        replayInterval: null,
        lastPitLap:     {},
        selectedDriver: null
      })
    },

    // ── Lap update ─────────────────────────────────────────────────────────
    updateCurrentLap() {
      if (!this.raceData || this.currentLap > this.raceData.laps.length) return
      this.currentLapData = this.raceData.laps[this.currentLap - 1]

      // Batch all pit-outs in this lap into a SINGLE toast
      const pitting = []
      this.currentDrivers.forEach(driver => {
        const key = driver.driver
        if (driver.pit_out && this.lastPitLap[key] !== this.currentLap) {
          pitting.push(`${driver.driver} → ${driver.compound}`)
          this.lastPitLap[key] = this.currentLap
        }
      })

      if (pitting.length === 1) {
        this.pitToast(`🔧 ${pitting[0]}`)
      } else if (pitting.length > 1) {
        this.pitToast(`🔧 Pits: ${pitting.join(' | ')}`)
      }
    },

    // ── Playback controls ──────────────────────────────────────────────────
    togglePlay() {
      this.replayRunning ? this.pause() : this.play()
    },

    play() {
      this.replayRunning = true
      this._startInterval(this.playbackSpeed)
    },

    _startInterval(ms) {
      this.replayInterval = setInterval(() => {
        if (this.currentLap >= this.raceData.total_laps) {
          this.pause()
          this.showToast('Race finished! 🏁')
        } else {
          this.nextLap()
        }
      }, ms)
    },

    pause() {
      this.replayRunning = false
      clearInterval(this.replayInterval)
      this.replayInterval = null
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
      this.showToast('Restarted ↺')
    },

    // ── Driver selection ───────────────────────────────────────────────────
    selectDriver(code) {
      this.selectedDriver = (this.selectedDriver === code && code !== null) ? null : code
    },

    // ── Helpers ────────────────────────────────────────────────────────────
    getTireEmoji(compound) {
      return { SOFT:'🔴', MEDIUM:'🟡', HARD:'⚪' }[compound] || '⚫'
    },

    formatDate(dateStr) {
      if (!dateStr) return 'TBD'
      return new Date(dateStr).toLocaleDateString('en-US', { month:'short', day:'numeric' })
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

/* ══ Selector ══════════════════════════════════════════════════════════════ */
.selector { padding: 4rem 0; }
.page-title {
  font-family: var(--font-display);
  font-size: 3rem;
  letter-spacing: -0.02em;
  margin-bottom: 0.5rem;
}
.page-subtitle { color: var(--color-muted); margin-bottom: 3rem; }
.loading { text-align:center; padding:4rem; color:var(--color-muted); }

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
  transition: background 0.2s;
}
.race-item:hover { background: rgba(255,255,255,0.02); }
.race-round { font-family:var(--font-display); font-size:1.5rem; color:var(--color-muted); }
.race-name-text  { font-weight:500; margin-bottom:0.25rem; }
.race-location { font-size:0.85rem; color:var(--color-muted); }
.race-date { text-align:right; color:var(--color-muted); font-size:0.9rem; }

.replay-interface {
  height: calc(100vh - 65px);
  display: flex;
  flex-direction: column;
  background: #0a0a0a;
  overflow: hidden;
}

/* Top bar */
.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 2rem;
  border-bottom: 1px solid var(--color-border);
  background: rgba(10,10,10,0.98);
  flex-shrink: 0;
}
.back-btn {
  padding: 0.4rem 0.9rem;
  background: transparent;
  border: 1px solid var(--color-border);
  color: var(--color-fg);
  font-size: 0.85rem;
  cursor: pointer;
  border-radius: 4px;
  transition: border-color 0.2s;
}
.back-btn:hover { border-color: var(--color-fg); }
.race-title { flex:1; text-align:center; }
.race-name-label { font-family:var(--font-display); font-size:1.2rem; margin-right:0.75rem; }
.race-circuit    { font-size:0.8rem; color:var(--color-muted); }
.lap-counter     { font-size:0.9rem; color:var(--color-muted); }
.lap-counter strong { color:var(--color-fg); }

/* Main 3-column */
.main-layout {
  flex: 1;
  display: grid;
  grid-template-columns: 220px 1fr 280px;
  overflow: hidden;
  min-height: 0;
}

/* ── Left Sidebar ── */
.left-sidebar {
  background: rgba(8,8,8,0.98);
  border-right: 1px solid var(--color-border);
  padding: 1rem;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0;
}
.leaderboard   { margin-top:0.75rem; }
.section-title {
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--color-muted);
  margin-bottom: 0.5rem;
  padding-bottom: 0.35rem;
  border-bottom: 1px solid var(--color-border);
}
.driver-item {
  display: grid;
  grid-template-columns: 26px 1fr 22px;
  align-items: center;
  gap: 0.45rem;
  padding: 0.5rem 0.65rem;
  margin-bottom: 2px;
  border: 1px solid transparent;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s;
}
.driver-item:hover    { background:rgba(255,255,255,0.04); border-color:rgba(255,255,255,0.08); }
.driver-item.selected { background:rgba(255,255,255,0.08); border-color:rgba(255,255,255,0.2); }
.driver-pos  { font-size:0.82rem; font-weight:700; color:#777; text-align:center; }
.driver-code { font-family:monospace; font-weight:700; font-size:0.88rem; color:#fff; }
.driver-tire { font-size:0.95rem; text-align:center; }

/* ── Track Area ── */
.track-area {
  display: flex;
  flex-direction: column;
  padding: 0.75rem;
  min-height: 0;
  overflow: hidden;
}

.controls {
  display: flex;
  gap: 0.4rem;
  margin-top: 0.55rem;
  flex-shrink: 0;
  align-items: center;
}
.control-btn {
  padding: 0.5rem 1rem;
  background: transparent;
  border: 1px solid var(--color-border);
  color: var(--color-fg);
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  border-radius: 4px;
  transition: border-color 0.15s;
  white-space: nowrap;
}
.control-btn.primary {
  background: var(--color-fg);
  color: var(--color-bg);
  border-color: var(--color-fg);
  min-width: 44px;
  text-align: center;
}
.control-btn:hover:not(:disabled) { border-color: var(--color-fg); }
.control-btn:disabled { opacity:0.3; cursor:not-allowed; }

.speed-select {
  padding: 0.5rem 0.65rem;
  background: #1a1a1a;
  border: 1px solid var(--color-border);
  color: #fff;
  font-size: 0.85rem;
  cursor: pointer;
  border-radius: 4px;
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;
  /* small chevron via background image */
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%23888'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 0.55rem center;
  padding-right: 1.8rem;
  transition: border-color 0.15s;
}
.speed-select:hover  { border-color: rgba(255,255,255,0.3); }
.speed-select:focus  { outline: none; border-color: rgba(255,255,255,0.4); }
/* Dropdown options — dark background */
.speed-select option {
  background: #1a1a1a;
  color: #fff;
}

/* ── Right Sidebar ── */
.right-sidebar {
  background: rgba(8,8,8,0.98);
  border-left: 1px solid var(--color-border);
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}
</style>
