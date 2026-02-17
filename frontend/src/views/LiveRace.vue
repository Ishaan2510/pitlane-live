<template>
  <div class="live-race">
    <ToastNotification :toasts="toasts" @remove="removeToast" />

    <div v-if="loading" class="loading">
      <div class="spinner"></div><p>Loading race data...</p>
    </div>

    <div v-else>
      <!-- Race Header -->
      <div class="race-header">
        <div class="header-left">
          <h2>{{ race.name }}</h2>
          <p class="circuit">{{ race.circuit }}</p>
        </div>
        <div class="lap-counter">
          <div class="lap-label-top">LAP</div>
          <div class="lap-numbers">
            <span class="current-lap">{{ race.currentLap }}</span>
            <span class="lap-sep">/</span>
            <span class="total-laps">{{ race.totalLaps }}</span>
          </div>
          <div class="lap-progress-bar">
            <div class="lap-progress-fill" :style="{ width: lapProgressPct + '%' }"></div>
          </div>
          <div class="sim-status" :class="{ running: simRunning }">
            {{ simRunning ? '🔴 LIVE' : '⏸ PAUSED' }}
          </div>
        </div>
        <button class="sim-btn" @click="toggleSim">
          {{ simRunning ? '⏸ Pause Sim' : '▶ Start Sim' }}
        </button>
      </div>

      <!-- Standings -->
      <div class="standings-section">
        <h3>🏁 Live Standings</h3>
        <DriverCard
          v-for="driver in race.leaders"
          :key="driver.driver"
          :driver="driver"
          :selected="prediction.driver === driver.driver"
          @select="selectDriver"
        />
      </div>

      <!-- Prediction Panel -->
      <div class="prediction-panel">
        <h3>🎯 Make Your Prediction</h3>
        <p class="prediction-hint">Predict the next strategic move based on tire wear above</p>

        <div class="prediction-form">
          <div class="form-group">
            <label>Selected Driver:</label>
            <div class="selected-driver-display">
              <span v-if="prediction.driver" class="driver-chip">
                {{ prediction.driver }} ✓
              </span>
              <span v-else class="driver-hint">👆 Click a driver card above to select</span>
            </div>
          </div>

          <div class="form-group">
            <label>Predicted Action:</label>
            <div class="action-buttons">
              <button
                v-for="action in actions"
                :key="action.value"
                class="action-btn-choice"
                :class="{ active: prediction.action === action.value, [action.color]: true }"
                @click="prediction.action = action.value"
              >
                {{ action.emoji }} {{ action.label }}
              </button>
            </div>
          </div>

          <div class="form-group">
            <label>Expected on Lap: <strong style="color:#e10600">{{ prediction.lap }}</strong></label>
            <input
              v-model.number="prediction.lap"
              type="range"
              :min="race.currentLap + 1"
              :max="race.totalLaps"
              class="input-range lap-range"
            />
            <div class="range-labels">
              <span>Lap {{ race.currentLap + 1 }}</span>
              <span>Lap {{ race.totalLaps }}</span>
            </div>
          </div>

          <div class="form-group">
            <label>Confidence: <strong style="color:#e10600">{{ prediction.confidence }}%</strong></label>
            <input
              v-model.number="prediction.confidence"
              type="range" min="1" max="100"
              class="input-range"
            />
          </div>

          <button
            @click="submitPrediction"
            :disabled="!isPredictionValid"
            class="submit-btn"
          >
            🚀 Submit Prediction
          </button>
        </div>

        <!-- Predictions History -->
        <div v-if="userPredictions.length > 0" class="predictions-history">
          <h4>Your Predictions This Race:</h4>
          <div class="prediction-list">
            <div
              v-for="(pred, i) in userPredictions"
              :key="i"
              class="prediction-item"
              :class="pred.status"
            >
              <span class="pred-driver">{{ pred.driver }}</span>
              <span class="pred-action">{{ formatAction(pred.action) }}</span>
              <span class="pred-lap">Lap {{ pred.lap }}</span>
              <span class="pred-confidence">{{ pred.confidence }}% conf.</span>
              <span class="pred-status-badge" :class="pred.status">{{ pred.status }}</span>
            </div>
          </div>
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

const PIT_WINDOW = { SOFT: 20, MEDIUM: 30, HARD: 40 }

export default {
  name: 'LiveRace',
  components: { ToastNotification, DriverCard },

  setup() {
    const { toasts, remove: removeToast, success, error, info, warning, pit } = useToast()
    return { toasts, removeToast, toastSuccess: success, toastError: error, toastInfo: info, toastWarning: warning, toastPit: pit }
  },

  data() {
    return {
      race: null,
      loading: true,
      simRunning: false,
      simInterval: null,
      prediction: { driver: '', action: '', lap: null, confidence: 75 },
      userPredictions: [],
      actions: [
        { value: 'pit_soft',   label: 'Soft Tires',   emoji: '🔴', color: 'soft' },
        { value: 'pit_medium', label: 'Medium Tires', emoji: '🟡', color: 'medium' },
        { value: 'pit_hard',   label: 'Hard Tires',   emoji: '⚪', color: 'hard' },
        { value: 'stay_out',   label: 'Stay Out',     emoji: '⏩', color: 'stay' },
      ]
    }
  },

  computed: {
    isPredictionValid() {
      return (
        this.prediction.driver &&
        this.prediction.action &&
        this.prediction.lap > this.race?.currentLap
      )
    },
    lapProgressPct() {
      if (!this.race) return 0
      return (this.race.currentLap / this.race.totalLaps) * 100
    }
  },

  async mounted() {
    try {
      this.race = await api.getLiveRace(this.$route.params.id)
      // Set default prediction lap
      this.prediction.lap = this.race.currentLap + 3
    } catch(e) {
      console.error(e)
    } finally {
      this.loading = false
    }
  },

  beforeUnmount() {
    this.stopSim()
  },

  methods: {
    // ── Lap Simulator ─────────────────────────────────────────────────────────
    toggleSim() {
      this.simRunning ? this.stopSim() : this.startSim()
    },

    startSim() {
      this.simRunning = true
      this.toastInfo('Simulation Started', 'Race is now progressing in real-time')
      this.simInterval = setInterval(() => this.tickLap(), 5000)
    },

    stopSim() {
      this.simRunning = false
      clearInterval(this.simInterval)
      this.simInterval = null
    },

    tickLap() {
      if (!this.race || this.race.currentLap >= this.race.totalLaps) {
        this.stopSim()
        this.toastSuccess('Race Finished!', `${this.race.leaders[0].driver} wins the ${this.race.name}!`)
        return
      }

      this.race.currentLap++

      // Age everyone's tires
      this.race.leaders.forEach(driver => {
        driver.tireAge++

        const maxAge = PIT_WINDOW[driver.tireCompound] || 30

        // Auto pit stop when tires are critically worn (adds drama!)
        if (driver.tireAge >= maxAge) {
          const newCompound = this.pickNextCompound(driver.tireCompound)
          const oldAge = driver.tireAge
          driver.tireAge = 0
          driver.lastPitLap = this.race.currentLap
          driver.tireCompound = newCompound

          this.toastPit(
            `🔧 ${driver.driver} PITS!`,
            `Lap ${this.race.currentLap} — ${oldAge}-lap ${driver.tireCompound} → Fresh ${newCompound}s`
          )

          // Check if any user prediction was correct
          this.checkPredictions(driver)
        }
      })

      // Occasionally adjust gaps for realism
      this.shuffleGaps()

      // Move prediction lap slider forward if it's now in the past
      if (this.prediction.lap <= this.race.currentLap) {
        this.prediction.lap = this.race.currentLap + 2
      }
    },

    pickNextCompound(current) {
      const strategy = { SOFT: 'MEDIUM', MEDIUM: 'HARD', HARD: 'MEDIUM' }
      return strategy[current] || 'MEDIUM'
    },

    shuffleGaps() {
      this.race.leaders.forEach((d, i) => {
        if (i === 0) { d.gap = 'LEADER'; return }
        const base = parseFloat(this.race.leaders[i-1].gap) || 0
        const delta = (Math.random() - 0.48) * 0.4
        const newGap = Math.max(0.1, base + delta).toFixed(1)
        d.gap = `+${newGap}s`
      })
    },

    // ── Prediction Logic ──────────────────────────────────────────────────────
    selectDriver(driver) {
      this.prediction.driver = driver.driver
      this.toastInfo('Driver Selected', `${driver.driver} — choose their next strategy`)
    },

    checkPredictions(driver) {
      this.userPredictions.forEach(pred => {
        if (pred.status !== 'pending') return
        if (pred.driver !== driver.driver) return
        if (Math.abs(pred.lap - this.race.currentLap) <= 2) {
          // Check compound match
          const predCompound = pred.action.replace('pit_', '').toUpperCase()
          if (pred.action === 'stay_out') {
            pred.status = 'incorrect'
            this.toastWarning('Prediction Missed', `${driver.driver} pitted — you predicted stay out`)
          } else if (predCompound === driver.tireCompound) {
            pred.status = 'correct'
            this.toastSuccess('Correct Prediction! 🎉', `+150 points — you nailed ${driver.driver}'s strategy!`)
          } else {
            pred.status = 'close'
            this.toastWarning('Almost! 🤏', `Right driver, wrong compound — +50 pts`)
          }
        }
      })
    },

    async submitPrediction() {
      if (!this.isPredictionValid) return
      try {
        const result = await api.submitPrediction({
          raceId: this.race.id,
          ...this.prediction,
          timestamp: new Date().toISOString()
        })
        this.userPredictions.unshift({
          ...this.prediction,
          status: 'pending'
        })
        this.toastSuccess(
          'Prediction Locked In! 🔒',
          `${this.prediction.driver} — ${this.formatAction(this.prediction.action)} on Lap ${this.prediction.lap}`
        )
        this.prediction = { driver: '', action: '', lap: this.race.currentLap + 3, confidence: 75 }
      } catch(e) {
        this.toastError('Submission Failed', 'Could not submit prediction. Try again.')
      }
    },

    formatAction(a) {
      return { pit_soft:'Pit → Soft', pit_medium:'Pit → Medium',
               pit_hard:'Pit → Hard', stay_out:'Stay Out' }[a] || a
    }
  }
}
</script>

<style scoped>
.live-race { max-width: 1200px; margin: 0 auto; }
.loading { text-align:center; padding: 4rem; }
.spinner {
  width:50px; height:50px; border:4px solid rgba(225,6,0,.1);
  border-top-color:#e10600; border-radius:50%;
  animation:spin 1s linear infinite; margin: 0 auto 1rem;
}
@keyframes spin { to { transform:rotate(360deg); } }

/* ── Race Header ── */
.race-header {
  display: flex; align-items: center; gap: 2rem;
  background: rgba(20,20,20,0.9); padding: 1.5rem 2rem;
  border-radius: 14px; margin-bottom: 2rem;
  border: 2px solid #e10600;
  box-shadow: 0 4px 24px rgba(225,6,0,0.2);
}
.header-left { flex: 1; }
.header-left h2 { font-size: 1.8rem; color: #fff; margin-bottom: 0.3rem; }
.circuit { color: #888; font-size: 0.9rem; }

.lap-counter { text-align: center; }
.lap-label-top { color: #888; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em; }
.lap-numbers { display: flex; align-items: baseline; gap: 0.3rem; justify-content: center; }
.current-lap { font-size: 3rem; color: #00ff00; font-weight: 900; font-family: monospace; }
.lap-sep { font-size: 1.5rem; color: #444; }
.total-laps { font-size: 1.5rem; color: #666; font-family: monospace; }

.lap-progress-bar {
  width: 140px; height: 6px; background: rgba(255,255,255,0.1);
  border-radius: 3px; margin: 0.4rem auto; overflow: hidden;
}
.lap-progress-fill {
  height: 100%; background: linear-gradient(90deg, #e10600, #ff4444);
  border-radius: 3px; transition: width 0.5s ease;
}

.sim-status {
  font-size: 0.75rem; font-weight: 700; color: #666; margin-top: 0.3rem;
  letter-spacing: 0.05em;
}
.sim-status.running { color: #00ff00; animation: blink 1.5s infinite; }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.4} }

.sim-btn {
  background: rgba(225,6,0,0.15); border: 2px solid #e10600; color: #fff;
  padding: 0.6rem 1.2rem; border-radius: 8px; font-size: 0.9rem;
  font-weight: 600; cursor: pointer; transition: all 0.2s; white-space: nowrap;
}
.sim-btn:hover { background: #e10600; transform: scale(1.05); }

/* ── Standings ── */
.standings-section { margin-bottom: 2rem; }
.standings-section h3 { font-size: 1.4rem; margin-bottom: 1rem; color: #fff; }

/* ── Prediction Panel ── */
.prediction-panel {
  background: rgba(20,20,20,0.9); border-radius: 14px;
  padding: 2rem; border: 1px solid rgba(255,255,255,0.08);
}
.prediction-panel h3 { font-size: 1.4rem; margin-bottom: 0.4rem; color: #fff; }
.prediction-hint { color: #666; font-size: 0.9rem; margin-bottom: 1.5rem; font-style: italic; }

.prediction-form { display: grid; gap: 1.4rem; }
.form-group { display: flex; flex-direction: column; gap: 0.5rem; }
.form-group label { color: #aaa; font-size: 0.85rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }

/* Selected driver */
.selected-driver-display { padding: 0.75rem; background: rgba(0,0,0,0.3); border-radius: 8px; min-height: 44px; display: flex; align-items: center; }
.driver-chip { background: #e10600; color: #fff; padding: 0.3rem 0.8rem; border-radius: 20px; font-weight: 700; font-size: 0.9rem; }
.driver-hint { color: #555; font-size: 0.9rem; font-style: italic; }

/* Action buttons */
.action-buttons { display: flex; gap: 0.75rem; flex-wrap: wrap; }
.action-btn-choice {
  flex: 1; min-width: 130px; padding: 0.6rem 1rem;
  border: 2px solid rgba(255,255,255,0.15); border-radius: 8px;
  background: rgba(255,255,255,0.05); color: #fff;
  font-size: 0.85rem; font-weight: 600; cursor: pointer;
  transition: all 0.2s; text-align: center;
}
.action-btn-choice.soft.active   { background: rgba(200,0,0,0.4);   border-color: #cc0000; }
.action-btn-choice.medium.active { background: rgba(180,180,0,0.4); border-color: #cccc00; }
.action-btn-choice.hard.active   { background: rgba(200,200,200,0.2); border-color: #aaa; }
.action-btn-choice.stay.active   { background: rgba(0,150,255,0.3); border-color: #0096ff; }
.action-btn-choice:hover:not(.active) { border-color: #e10600; background: rgba(225,6,0,0.1); }

/* Range inputs */
.input-range {
  width: 100%; height: 6px; background: rgba(255,255,255,0.15);
  border-radius: 10px; outline: none; cursor: pointer;
}
.input-range::-webkit-slider-thumb {
  appearance: none; width: 20px; height: 20px;
  background: #e10600; border-radius: 50%; cursor: pointer;
  box-shadow: 0 0 6px rgba(225,6,0,0.5);
}
.range-labels { display: flex; justify-content: space-between; color: #555; font-size: 0.75rem; margin-top: 0.2rem; }

.submit-btn {
  background: linear-gradient(135deg, #e10600, #ff3322); color: #fff;
  border: none; padding: 1rem; border-radius: 10px;
  font-size: 1rem; font-weight: 700; cursor: pointer; transition: all 0.3s;
  letter-spacing: 0.03em;
}
.submit-btn:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(225,6,0,0.4); }
.submit-btn:disabled { background: #333; color: #666; cursor: not-allowed; }

/* Predictions History */
.predictions-history { margin-top: 2rem; padding-top: 1.5rem; border-top: 1px solid rgba(255,255,255,0.08); }
.predictions-history h4 { color: #aaa; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.75rem; }
.prediction-list { display: flex; flex-direction: column; gap: 0.5rem; }
.prediction-item {
  display: flex; align-items: center; gap: 1rem; padding: 0.75rem 1rem;
  background: rgba(0,0,0,0.3); border-radius: 8px;
  border-left: 4px solid #444; font-size: 0.9rem; flex-wrap: wrap;
}
.prediction-item.pending   { border-left-color: #ffa500; }
.prediction-item.correct   { border-left-color: #00cc66; background: rgba(0,200,100,0.05); }
.prediction-item.close     { border-left-color: #ffa500; }
.prediction-item.incorrect { border-left-color: #cc0000; }
.pred-driver   { color: #fff; font-weight: 700; min-width: 160px; }
.pred-action   { color: #aaa; flex: 1; }
.pred-lap      { color: #888; }
.pred-confidence { color: #666; font-size: 0.8rem; }
.pred-status-badge {
  padding: 0.2rem 0.6rem; border-radius: 20px;
  font-size: 0.75rem; font-weight: 700; text-transform: uppercase;
}
.pending   .pred-status-badge { background: rgba(255,165,0,0.2);  color: #ffa500; }
.correct   .pred-status-badge { background: rgba(0,200,100,0.2);  color: #00cc66; }
.close     .pred-status-badge { background: rgba(255,165,0,0.2);  color: #ffa500; }
.incorrect .pred-status-badge { background: rgba(200,0,0,0.2);    color: #cc0000; }
</style>
