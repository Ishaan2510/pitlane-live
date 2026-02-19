<template>
  <div class="race-replay">
    <ToastNotification :toasts="toasts" @remove="removeToast" />

    <!-- Race Selector -->
    <div v-if="!selectedRace" class="race-selector">
      <h2>🏁 Race Replay — 2024 Season</h2>
      <p class="subtitle">Experience real F1 races lap-by-lap with authentic telemetry data</p>

      <div v-if="loadingRaces" class="loading">
        <div class="spinner"></div>
        <p>Loading available races...</p>
      </div>

      <div v-else class="races-grid">
        <div
          v-for="race in availableRaces"
          :key="race.round"
          class="race-card-selector"
          @click="selectRace(race)"
        >
          <div class="round-badge">R{{ race.round }}</div>
          <h3>{{ race.name }}</h3>
          <p class="location">{{ race.location }}, {{ race.country }}</p>
          <p class="date">{{ formatDate(race.date) }}</p>
          <button class="replay-btn">▶ Replay Race</button>
        </div>
      </div>
    </div>

    <!-- Race Replay Interface -->
    <div v-else class="replay-interface">
      <!-- Header -->
      <div class="replay-header">
        <button class="back-btn" @click="backToSelector">← Back to Races</button>
        <div class="race-info">
          <h2>{{ raceData.name }}</h2>
          <p class="badge real-data">🎯 REAL F1 DATA</p>
        </div>
        <div class="lap-counter">
          <span class="current-lap">{{ currentLap }}</span>
          <span class="lap-sep">/</span>
          <span class="total-laps">{{ raceData.total_laps }}</span>
        </div>
      </div>

      <!-- Controls -->
      <div class="replay-controls">
        <button @click="replayRunning ? pause() : play()" class="control-btn play">
          {{ replayRunning ? '⏸ Pause' : '▶ Play' }}
        </button>
        <button @click="previousLap" :disabled="currentLap <= 1" class="control-btn">⏮ Prev Lap</button>
        <button @click="nextLap" :disabled="currentLap >= raceData.total_laps" class="control-btn">Next Lap ⏭</button>
        
        <div class="speed-control">
          <label>Speed:</label>
          <select v-model="playbackSpeed" class="speed-select">
            <option :value="500">0.5x</option>
            <option :value="1000">1x</option>
            <option :value="2000">2x</option>
            <option :value="4000">4x</option>
          </select>
        </div>
      </div>

      <!-- Current Lap Data -->
      <div v-if="currentLapData" class="standings-section">
        <h3>🏁 Lap {{ currentLap }} Standings</h3>
        <DriverCard
          v-for="driver in currentLapData.drivers"
          :key="driver.driver"
          :driver="transformDriver(driver)"
        />
      </div>

      <!-- Pit Stop Events -->
      <div v-if="pitStopEvents.length > 0" class="pit-events">
        <h4>🔧 Pit Stops This Lap:</h4>
        <div v-for="(event, i) in pitStopEvents" :key="i" class="pit-event">
          {{ event }}
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import api from '../services/api.js'
import { useToast } from '../composables/useToast.js'
import ToastNotification from '../components/ToastNotification.vue'
import DriverCard from '../components/DriverCard.vue'

export default {
  name: 'RaceReplay',
  components: { ToastNotification, DriverCard },

  setup() {
    const { toasts, remove: removeToast, success, error, info, pit } = useToast()
    return { toasts, removeToast, toastSuccess: success, toastError: error, toastInfo: info, toastPit: pit }
  },

  data() {
    return {
      loadingRaces: true,
      availableRaces: [],
      selectedRace: null,
      raceData: null,
      currentLap: 1,
      currentLapData: null,
      replayRunning: false,
      replayInterval: null,
      playbackSpeed: 1000,
      pitStopEvents: []
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
        this.toastSuccess('Races Loaded', `${this.availableRaces.length} real F1 races available`)
      } catch (e) {
        this.toastError('Load Failed', 'Could not fetch race data')
      } finally {
        this.loadingRaces = false
      }
    },

    async selectRace(race) {
      this.selectedRace = race
      this.toastInfo('Loading Race Data', `Fetching ${race.name} telemetry...`)
      
      try {
        this.raceData = await api.getReplayRaceData(race.year || 2024, race.round)
        this.currentLap = 1
        this.updateCurrentLap()
        this.toastSuccess('Race Loaded!', `${this.raceData.total_laps} laps ready to replay`)
      } catch (e) {
        this.toastError('Load Failed', 'Could not load race data')
        this.selectedRace = null
      }
    },

    backToSelector() {
      this.pause()
      this.selectedRace = null
      this.raceData = null
      this.currentLap = 1
    },

    updateCurrentLap() {
      if (!this.raceData || this.currentLap > this.raceData.laps.length) return
      
      this.currentLapData = this.raceData.laps[this.currentLap - 1]
      
      // Check for pit stops
      this.pitStopEvents = []
      this.currentLapData.drivers.forEach(driver => {
        if (driver.pit_in || driver.pit_out) {
          const event = `${driver.driver} → ${driver.compound} tires (${driver.tire_life} laps old)`
          this.pitStopEvents.push(event)
          this.toastPit(`🔧 ${driver.driver} Pits!`, `Fresh ${driver.compound} tires`)
        }
      })
    },

    play() {
      this.replayRunning = true
      this.toastInfo('Replay Started', 'Race is now playing')
      this.replayInterval = setInterval(() => {
        if (this.currentLap >= this.raceData.total_laps) {
          this.pause()
          this.toastSuccess('Race Finished!', `${this.currentLapData.drivers[0].driver} wins!`)
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

    transformDriver(driver) {
      // Transform FastF1 data to DriverCard format
      return {
        position: driver.position,
        driver: driver.driver,
        team: driver.team,
        gap: driver.gap,
        tireCompound: driver.compound,
        tireAge: driver.tire_life,
        lastPitLap: this.currentLap - driver.tire_life
      }
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
.race-replay { max-width: 1400px; margin: 0 auto; }

/* Race Selector */
.race-selector { padding: 2rem; }
.race-selector h2 { font-size: 2.5rem; color: #fff; text-align: center; margin-bottom: 0.5rem; }
.subtitle { text-align: center; color: #888; font-size: 1.1rem; margin-bottom: 3rem; }

.loading { text-align: center; padding: 4rem; }
.spinner {
  width: 50px; height: 50px; border: 4px solid rgba(225,6,0,0.1);
  border-top-color: #e10600; border-radius: 50%;
  animation: spin 1s linear infinite; margin: 0 auto 1rem;
}
@keyframes spin { to { transform: rotate(360deg); } }

.races-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1.5rem; }

.race-card-selector {
  background: rgba(30,30,30,0.9); border-radius: 12px; padding: 1.5rem;
  cursor: pointer; transition: all 0.3s ease; border: 2px solid rgba(255,255,255,0.1);
  position: relative;
}
.race-card-selector:hover { transform: translateY(-5px); border-color: #e10600; box-shadow: 0 8px 25px rgba(225,6,0,0.3); }

.round-badge {
  position: absolute; top: 1rem; right: 1rem;
  background: #e10600; color: #fff; padding: 0.3rem 0.6rem;
  border-radius: 20px; font-size: 0.8rem; font-weight: bold;
}

.race-card-selector h3 { font-size: 1.2rem; color: #fff; margin-bottom: 0.5rem; }
.location { color: #888; font-size: 0.9rem; margin-bottom: 0.3rem; }
.date { color: #666; font-size: 0.85rem; margin-bottom: 1rem; }

.replay-btn {
  width: 100%; background: linear-gradient(135deg, #e10600, #ff3322);
  color: #fff; border: none; padding: 0.6rem; border-radius: 8px;
  font-size: 0.95rem; font-weight: 600; cursor: pointer; transition: all 0.3s;
}
.replay-btn:hover { transform: scale(1.05); }

/* Replay Interface */
.replay-interface { padding: 1rem; }

.replay-header {
  display: flex; justify-content: space-between; align-items: center;
  background: rgba(20,20,20,0.9); padding: 1.5rem; border-radius: 12px;
  margin-bottom: 1.5rem; border: 2px solid #e10600;
}

.back-btn {
  background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2);
  color: #fff; padding: 0.5rem 1rem; border-radius: 8px;
  font-size: 0.9rem; cursor: pointer; transition: all 0.2s;
}
.back-btn:hover { background: rgba(255,255,255,0.2); }

.race-info h2 { font-size: 1.5rem; color: #fff; margin-bottom: 0.3rem; }
.badge.real-data {
  background: rgba(0,255,0,0.2); color: #00ff00;
  padding: 0.2rem 0.6rem; border-radius: 20px;
  font-size: 0.75rem; font-weight: bold;
}

.lap-counter { text-align: center; }
.current-lap { font-size: 2.5rem; color: #00ff00; font-weight: 900; font-family: monospace; }
.lap-sep { font-size: 1.5rem; color: #444; margin: 0 0.2rem; }
.total-laps { font-size: 1.5rem; color: #666; font-family: monospace; }

/* Controls */
.replay-controls {
  display: flex; align-items: center; gap: 1rem; padding: 1rem;
  background: rgba(20,20,20,0.8); border-radius: 10px; margin-bottom: 1.5rem;
}

.control-btn {
  background: rgba(225,6,0,0.2); border: 2px solid #e10600; color: #fff;
  padding: 0.6rem 1.2rem; border-radius: 8px; font-size: 0.9rem;
  font-weight: 600; cursor: pointer; transition: all 0.2s;
}
.control-btn:hover:not(:disabled) { background: #e10600; transform: scale(1.05); }
.control-btn:disabled { opacity: 0.3; cursor: not-allowed; }
.control-btn.play { background: #00cc00; border-color: #00cc00; }
.control-btn.play:hover { background: #00ff00; }

.speed-control { display: flex; align-items: center; gap: 0.5rem; margin-left: auto; }
.speed-control label { color: #888; font-size: 0.9rem; }
.speed-select {
  background: rgba(0,0,0,0.5); border: 2px solid rgba(255,255,255,0.2);
  color: #fff; padding: 0.5rem; border-radius: 6px; cursor: pointer;
}

.standings-section { margin-bottom: 2rem; }
.standings-section h3 { font-size: 1.3rem; color: #fff; margin-bottom: 1rem; }

.pit-events {
  background: rgba(60,0,120,0.2); border: 2px solid #9900ff;
  border-radius: 10px; padding: 1rem; margin-top: 1.5rem;
}
.pit-events h4 { color: #9900ff; margin-bottom: 0.5rem; }
.pit-event { color: #fff; padding: 0.3rem 0; font-size: 0.9rem; }
</style>
