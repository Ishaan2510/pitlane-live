<template>
  <div class="race-replay">
    <ToastNotification :toasts="toasts" @remove="removeToast" />

    <!-- ══════════════════════════════════════════════
         RACE SELECTOR
    ══════════════════════════════════════════════ -->
    <div v-if="!selectedRace" class="selector">
      <div class="container">
        <h1 class="page-title">Race Replay</h1>
        <p class="page-subtitle">Select a race to replay with real F1 telemetry data</p>

        <!-- Year toggle -->
        <div class="year-selector">
          <button
            v-for="y in [2024, 2025, 2026]"
            :key="y"
            class="year-btn"
            :class="{ active: selectedYear === y }"
            @click="switchYear(y)"
          >{{ y }}</button>
        </div>

        <div v-if="loadingRaces" class="loading">Loading races…</div>

        <div v-else class="race-list">
          <div
            v-for="race in availableRaces"
            :key="race.round"
            class="race-item"
            :class="{ 'not-ready': !race.ready }"
            @click="race.ready ? selectRace(race) : null"
          >
            <div class="race-round">R{{ race.round }}</div>
            <div class="race-details">
              <div class="race-name-text">{{ race.name }}</div>
              <div class="race-location">{{ race.location }}, {{ race.country }}</div>
            </div>
            <div class="race-date">
              {{ formatDate(race.date) }}
              <span v-if="race.ready" class="ready-badge">REPLAY →</span>
              <span v-else class="pending-badge">PROCESSING</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ══════════════════════════════════════════════
         REPLAY INTERFACE
    ══════════════════════════════════════════════ -->
    <div v-else class="replay-interface">

      <!-- Top bar -->
      <div class="top-bar">
        <button @click="backToSelector" class="back-btn">← Back</button>
        <div class="race-title-block">
          <span class="race-name-display">{{ raceData.name }}</span>
          <span class="race-circuit-display">{{ raceData.circuit }}</span>
        </div>
        <div class="lap-counter">
          Lap <strong>{{ currentLap }} / {{ raceData.total_laps }}</strong>
        </div>
      </div>

      <!-- Three-column body -->
      <div class="main-layout">

        <!-- ── LEFT sidebar: Weather + Leaderboard ── -->
        <div class="left-sidebar">
          <WeatherPanel :weather="weatherData" />

          <div class="lb-section">
            <div class="sidebar-heading">LEADERBOARD</div>
            <div
              v-for="driver in currentLapDrivers"
              :key="driver.driver"
              class="lb-row"
              :class="{ selected: selectedDriver === driver.driver }"
              @click="onSelectDriver(driver.driver)"
            >
              <div class="lb-pos">{{ driver.position }}</div>
              <div class="lb-code">{{ driver.driver }}</div>
              <div class="lb-tire">{{ getTireEmoji(driver.compound) }}</div>
            </div>
          </div>
        </div>

        <!-- ── CENTER: Track canvas + controls ── -->
        <div class="track-area">
          <!-- Track fills all available vertical space -->
          <div class="canvas-wrapper">
            <TrackCanvas
              :drivers="currentLapDrivers"
              :circuitData="circuitData"
              :selectedDriver="selectedDriver"
              :lapDuration="playbackSpeed"
              @select-driver="onSelectDriver"
            />
          </div>

          <!-- Playback controls bar -->
          <div class="controls">
            <button
              class="control-btn primary"
              @click="replayRunning ? pause() : play()"
            >{{ replayRunning ? '⏸' : '▶' }}</button>

            <button class="control-btn" @click="previousLap" :disabled="currentLap <= 1">⏮</button>
            <button class="control-btn" @click="nextLap"     :disabled="currentLap >= raceData.total_laps">⏭</button>

            <select v-model.number="playbackSpeed" @change="onSpeedChange" class="speed-select">
              <option :value="2000">0.5×</option>
              <option :value="1000">1×</option>
              <option :value="500">2×</option>
              <option :value="250">4×</option>
              <option :value="125">8×</option>
            </select>

            <button class="control-btn restart" @click="restart">↻ Restart</button>
          </div>
        </div>

        <!-- ── RIGHT sidebar: Pit stops + Telemetry ── -->
        <div class="right-sidebar">

          <!-- TOP: Recent pit stops -->
          <div class="pit-section">
            <div class="sidebar-heading">RECENT PIT STOPS</div>

            <div v-if="pitStopLog.length === 0" class="pits-empty">
              No pit stops yet
            </div>

            <div class="pit-scroll">
              <div
                v-for="(pit, i) in pitStopLog"
                :key="i"
                class="pit-entry"
              >
                <div class="pit-meta">
                  <span class="pit-lap">Lap {{ pit.lap }}</span>
                </div>
                <div class="pit-driver-name">{{ pit.driver }}</div>
                <span class="tyre-pill" :class="pit.compound.toLowerCase()">
                  {{ getTireEmoji(pit.compound) }} {{ pit.compound }}
                </span>
              </div>
            </div>
          </div>

          <!-- Sidebar divider -->
          <div class="sidebar-divider" />

          <!-- BOTTOM: Telemetry -->
          <div class="telemetry-section">
            <TelemetryPanel
              :driver="selectedDriverData"
              :enriched="telemetryEnriched"
              :loading="telemetryLoading"
            />
          </div>

        </div>

      </div><!-- /.main-layout -->

      <!-- Bottom progress bar -->
      <ProgressBar :currentLap="currentLap" :totalLaps="raceData.total_laps" />

    </div>
  </div>
</template>

<script>
import api              from '../services/api.js'
import { useToast }     from '../composables/useToast.js'
import ToastNotification from '../components/ToastNotification.vue'
import TrackCanvas      from '../components/TrackCanvas.vue'
import WeatherPanel     from '../components/WeatherPanel.vue'
import TelemetryPanel   from '../components/TelemetryPanel.vue'
import ProgressBar      from '../components/ProgressBar.vue'

export default {
  name: 'RaceReplay',
  components: { ToastNotification, TrackCanvas, WeatherPanel, TelemetryPanel, ProgressBar },

  setup() {
    const { toasts, remove: removeToast, show } = useToast()
    return { toasts, removeToast, showToast: show }
  },

  data() {
    return {
      // selector
      selectedYear:   2025,
      availableYears: [2024, 2025, 2026],
      loadingRaces:   true,
      availableRaces: [],

      // replay
      selectedRace:   null,
      raceData:       null,
      circuitData:    null,
      weatherData:    null,
      currentLap:     1,
      currentLapData: null,

      // playback
      replayRunning:  false,
      replayInterval: null,
      playbackSpeed:  1000,

      // driver selection
      selectedDriver:    null,
      telemetryEnriched: {},
      telemetryLoading:  false,

      // pit stop log
      pitStopLog:   [],   // { lap, driver, compound }
      seenPitLaps:  {}    // driverCode → lap number last logged
    }
  },

  computed: {
    currentLapDrivers() {
      return this.currentLapData?.drivers ?? []
    },
    selectedDriverData() {
      if (!this.selectedDriver || !this.currentLapData) return null
      return this.currentLapData.drivers.find(d => d.driver === this.selectedDriver) ?? null
    }
  },

  async mounted() {
    await this.loadAvailableRaces()
  },

  beforeUnmount() {
    this.pause()
  },

  methods: {
    // ── Year selector ─────────────────────────────────────────────────────────
    async switchYear(year) {
      if (year === this.selectedYear) return
      this.selectedYear   = year
      this.loadingRaces   = true
      this.availableRaces = []
      await this.loadAvailableRaces()
    },

    async loadAvailableRaces() {
      try {
        // Use schedule API — shows all completed races, not just cached ones
        const [scheduleRes, cachedRes] = await Promise.all([
          fetch(`/api/schedule?year=${this.selectedYear}`),
          fetch(`/api/replay/available?year=${this.selectedYear}`)
        ])
        const schedule = await scheduleRes.json()
        const cached = await cachedRes.json()
        const cachedRounds = new Set(cached.map(r => r.round))
        this.availableRaces = schedule
          .filter(r => r.status === 'completed')
          .map(r => ({
            round:    r.round,
            name:     r.name,
            location: r.location,
            country:  r.country,
            date:     r.date,
            year:     r.year || this.selectedYear,
            ready:    cachedRounds.has(r.round)
          }))
      } catch (e) {
        console.error(e)
      } finally {
        this.loadingRaces = false
      }
    },

    // ── Race selection ────────────────────────────────────────────────────────
    async selectRace(race) {
      this.selectedRace = race
      this.showToast('Loading race data…')

      try {
        const year  = race.year || this.selectedYear
        const round = race.round

        const [raceData, circuitData, weatherData] = await Promise.all([
          api.getReplayRaceData(year, round),
          api.getCircuitData(year, round),
          api.getWeatherData(year, round)
        ])

        this.raceData    = raceData
        this.circuitData = circuitData
        this.weatherData = weatherData

        this.currentLap        = 1
        this.pitStopLog        = []
        this.seenPitLaps       = {}
        this.selectedDriver    = null
        this.telemetryEnriched = {}

        this.updateCurrentLap()
        this.showToast('Race loaded ✓')
      } catch (e) {
        console.error(e)
        this.showToast('Failed to load race data')
        this.selectedRace = null
      }
    },

    backToSelector() {
      this.pause()
      this.selectedRace      = null
      this.raceData          = null
      this.circuitData       = null
      this.weatherData       = null
      this.currentLap        = 1
      this.pitStopLog        = []
      this.seenPitLaps       = {}
      this.selectedDriver    = null
      this.telemetryEnriched = {}
    },

    // ── Lap management ────────────────────────────────────────────────────────
    updateCurrentLap() {
      if (!this.raceData || this.currentLap > this.raceData.laps.length) return
      this.currentLapData = this.raceData.laps[this.currentLap - 1]
      this.detectPitStops()

      // Refresh telemetry if a driver is selected
      if (this.selectedDriver) {
        this.fetchTelemetry(this.selectedDriver, this.currentLap)
      }
    },

    detectPitStops() {
      if (!this.currentLapData) return
      this.currentLapData.drivers.forEach(driver => {
        const key = driver.driver
        if (driver.pit_out && this.seenPitLaps[key] !== this.currentLap) {
          this.seenPitLaps[key] = this.currentLap
          // prepend so newest is on top
          this.pitStopLog.unshift({
            lap:      this.currentLap,
            driver:   driver.driver,
            compound: driver.compound || 'UNKNOWN'
          })
        }
      })
    },

    play() {
      this.replayRunning  = true
      this.replayInterval = setInterval(() => {
        if (this.currentLap >= this.raceData.total_laps) {
          this.pause()
          this.showToast('Race finished!')
        } else {
          this.currentLap++
          this.updateCurrentLap()
        }
      }, this.playbackSpeed)
    },

    pause() {
      this.replayRunning = false
      clearInterval(this.replayInterval)
      this.replayInterval = null
    },

    onSpeedChange() {
      if (this.replayRunning) { this.pause(); this.play() }
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
      this.currentLap  = 1
      this.pitStopLog  = []
      this.seenPitLaps = {}
      this.updateCurrentLap()
      this.showToast('Restarted')
    },

    // ── Driver selection + telemetry ──────────────────────────────────────────
    async onSelectDriver(code) {
      if (this.selectedDriver === code) {
        this.selectedDriver    = null
        this.telemetryEnriched = {}
        return
      }
      this.selectedDriver = code
      await this.fetchTelemetry(code, this.currentLap)
    },

    async fetchTelemetry(code, lap) {
      if (!this.selectedRace) return
      this.telemetryLoading  = true
      this.telemetryEnriched = {}
      const year  = this.selectedRace.year || this.selectedYear
      const round = this.selectedRace.round
      const data  = await api.getDriverTelemetry(year, round, code, lap)
      if (data) this.telemetryEnriched = data
      this.telemetryLoading = false
    },

    // ── Helpers ───────────────────────────────────────────────────────────────
    getTireEmoji(compound) {
      return { SOFT:'🔴', MEDIUM:'🟡', HARD:'⚪', INTERMEDIATE:'🟢', WET:'🔵' }[compound] ?? '⚫'
    },

    formatDate(dateStr) {
      if (!dateStr) return 'TBD'
      return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    }
  }
}
</script>

<style scoped>
/* ════════════════════════════════════════════════════
   SELECTOR
════════════════════════════════════════════════════ */
.container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 4rem;
}

.race-item.not-ready { opacity: 0.4; cursor: not-allowed; }
.ready-badge  { color: #e10600; font-size: 0.72rem; font-weight: 700; margin-left: 0.5rem; }
.pending-badge { color: #555; font-size: 0.72rem; margin-left: 0.5rem; }

.selector { padding: 4rem 0; }

.page-title {
  font-family: var(--font-display);
  font-size: 3rem;
  letter-spacing: -0.02em;
  margin-bottom: 0.5rem;
}
.page-subtitle {
  color: var(--color-muted);
  margin-bottom: 2rem;
}

/* Year toggle */
.year-selector {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 2rem;
}
.year-btn {
  padding: 0.45rem 1.4rem;
  background: transparent;
  border: 1px solid var(--color-border);
  color: var(--color-muted);
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  border-radius: 2px;
}
.year-btn:hover       { border-color: var(--color-fg); color: var(--color-fg); }
.year-btn.active      { background: var(--color-fg); color: var(--color-bg); border-color: var(--color-fg); }

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
  padding: 1.25rem 2rem;
  background: var(--color-bg);
  cursor: pointer;
  transition: background 0.15s;
}
.race-item:hover    { background: rgba(255,255,255,0.02); }
.race-round         { font-family: var(--font-display); font-size: 1.5rem; color: var(--color-muted); }
.race-name-text     { font-weight: 500; margin-bottom: 0.2rem; }
.race-location      { font-size: 0.82rem; color: var(--color-muted); }
.race-date          { text-align: right; color: var(--color-muted); font-size: 0.9rem; }


/* ════════════════════════════════════════════════════
   REPLAY INTERFACE — full-viewport
════════════════════════════════════════════════════ */
.replay-interface {
  /* sit under the fixed 56px navbar */
  height: calc(100vh - 56px);
  display: flex;
  flex-direction: column;
  background: #0a0a0a;
  overflow: hidden;
}

/* ── Top bar ── */
.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.6rem 1.5rem;
  border-bottom: 1px solid var(--color-border);
  background: rgba(10,10,10,0.98);
  flex-shrink: 0;
  height: 48px;
}

.back-btn {
  padding: 0.35rem 0.85rem;
  background: transparent;
  border: 1px solid var(--color-border);
  color: var(--color-fg);
  font-size: 0.82rem;
  cursor: pointer;
  transition: border-color 0.15s;
  border-radius: 2px;
}
.back-btn:hover { border-color: var(--color-fg); }

.race-title-block   { flex: 1; text-align: center; }
.race-name-display  { font-family: var(--font-display); font-size: 1.15rem; margin-right: 0.6rem; }
.race-circuit-display { font-size: 0.8rem; color: var(--color-muted); }

.lap-counter        { font-size: 0.85rem; color: var(--color-muted); white-space: nowrap; }
.lap-counter strong { color: var(--color-fg); }

/* ── Three-column body ── */
.main-layout {
  flex: 1;
  display: grid;
  /* narrower sidebars → more canvas space */
  grid-template-columns: 200px 1fr 255px;
  overflow: hidden;
  min-height: 0;
}

/* ── LEFT sidebar ── */
.left-sidebar {
  border-right: 1px solid var(--color-border);
  padding: 0.65rem;
  overflow-y: auto;
  background: rgba(10,10,10,0.97);
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.lb-section { flex: 1; min-height: 0; overflow-y: auto; }

.sidebar-heading {
  font-size: 0.67rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: #555;
  margin-bottom: 0.45rem;
  padding: 0 0.15rem;
}

.lb-row {
  display: grid;
  grid-template-columns: 28px 1fr 22px;
  align-items: center;
  gap: 0.35rem;
  padding: 0.45rem 0.4rem;
  margin-bottom: 2px;
  border: 1px solid transparent;
  border-radius: 3px;
  cursor: pointer;
  transition: all 0.12s;
}
.lb-row:hover    { background: rgba(255,255,255,0.04); border-color: #2a2a2a; }
.lb-row.selected { background: rgba(255,255,255,0.07); border-color: #555; }

.lb-pos  { font-family: var(--font-display); font-size: 1rem; color: #555; text-align: center; }
.lb-code { font-family: monospace; font-weight: 700; font-size: 0.88rem; }
.lb-tire { font-size: 0.95rem; text-align: center; }

/* ── CENTER track area ── */
.track-area {
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

/* Canvas wrapper fills ALL remaining vertical space above controls */
.canvas-wrapper {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

/* Playback controls bar */
.controls {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.45rem 0.75rem;
  background: rgba(8,8,8,0.98);
  border-top: 1px solid var(--color-border);
  flex-shrink: 0;
}

.control-btn {
  padding: 0.42rem 0.9rem;
  background: transparent;
  border: 1px solid var(--color-border);
  color: var(--color-fg);
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.12s;
  border-radius: 2px;
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
.control-btn:disabled { opacity: 0.3; cursor: not-allowed; }
.control-btn.restart  { margin-left: auto; }

.speed-select {
  padding: 0.42rem 0.6rem;
  background: transparent;
  border: 1px solid var(--color-border);
  color: var(--color-fg);
  font-size: 0.82rem;
  cursor: pointer;
  border-radius: 2px;
}
.speed-select option { background: #111; }

/* ── RIGHT sidebar ── */
.right-sidebar {
  border-left: 1px solid var(--color-border);
  background: rgba(10,10,10,0.97);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Pit stops — top portion, scrollable, up to 45% of sidebar */
.pit-section {
  padding: 0.65rem;
  max-height: 42%;
  min-height: 80px;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.pit-scroll {
  overflow-y: auto;
  flex: 1;
  padding-right: 2px;
}

.pits-empty {
  color: #3a3a3a;
  font-size: 0.78rem;
  text-align: center;
  padding: 1.5rem 0;
}

.pit-entry {
  padding: 0.5rem 0.4rem;
  margin-bottom: 4px;
  border-radius: 3px;
  background: rgba(255,255,255,0.02);
  border: 1px solid #181818;
}
.pit-meta { display: flex; justify-content: space-between; margin-bottom: 0.15rem; }
.pit-lap  { font-size: 0.67rem; color: #555; text-transform: uppercase; letter-spacing: 0.05em; }
.pit-driver-name {
  font-family: monospace;
  font-weight: 700;
  font-size: 0.9rem;
  color: #ddd;
  margin-bottom: 0.25rem;
}

/* Tyre pills */
.tyre-pill {
  display: inline-block;
  padding: 0.1rem 0.4rem;
  border-radius: 3px;
  font-size: 0.72rem;
  font-weight: 700;
}
.tyre-pill.soft         { background: rgba(200,0,0,0.3);     color: #ff7777; }
.tyre-pill.medium       { background: rgba(200,200,0,0.25);  color: #ffff77; }
.tyre-pill.hard         { background: rgba(220,220,220,0.18); color: #ddd;   }
.tyre-pill.intermediate { background: rgba(0,180,0,0.25);   color: #77ff77; }
.tyre-pill.wet          { background: rgba(0,100,255,0.25); color: #77aaff; }
.tyre-pill.unknown      { background: rgba(100,100,100,0.2); color: #777;   }

/* Divider between pit stops and telemetry */
.sidebar-divider {
  height: 1px;
  background: #1a1a1a;
  flex-shrink: 0;
}

/* Telemetry — bottom portion, fills remaining space */
.telemetry-section {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}
</style>