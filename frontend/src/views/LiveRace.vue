<template>
  <div class="live-race">
    <div v-if="loading" class="loading"><div class="spinner"></div><p>Loading race data...</p></div>
    <div v-else>
      <!-- Header -->
      <div class="race-header">
        <div class="header-left">
          <h2>{{ race.name }}</h2>
          <p class="circuit">{{ race.circuit }}</p>
        </div>
        <div class="lap-counter">
          <span class="current-lap">{{ race.currentLap }}</span>
          <span class="separator">/</span>
          <span class="total-laps">{{ race.totalLaps }}</span>
          <span class="lap-label">LAPS</span>
        </div>
      </div>

      <!-- Standings -->
      <div class="standings-section">
        <h3>🏁 Current Standings</h3>
        <div class="standings-grid">
          <div v-for="leader in race.leaders" :key="leader.position" class="driver-card">
            <div class="position-badge">P{{ leader.position }}</div>
            <div class="driver-info">
              <h4>{{ leader.driver }}</h4>
              <p class="team">{{ leader.team }}</p>
            </div>
            <div class="driver-stats">
              <div class="stat"><span class="stat-label">Gap:</span><span class="stat-value">{{ leader.gap }}</span></div>
              <div class="stat">
                <span class="stat-label">Tire:</span>
                <span class="stat-value tire" :class="leader.tireCompound.toLowerCase()">
                  {{ leader.tireCompound }} ({{ leader.tireAge }} laps)
                </span>
              </div>
              <div class="stat"><span class="stat-label">Last Pit:</span><span class="stat-value">Lap {{ leader.lastPitLap }}</span></div>
            </div>
          </div>
        </div>
      </div>

      <!-- Prediction Panel -->
      <div class="prediction-panel">
        <h3>🎯 Make Your Prediction</h3>
        <p class="prediction-hint">Predict the next strategic move</p>
        <div class="prediction-form">
          <div class="form-group">
            <label>Select Driver:</label>
            <select v-model="prediction.driver" class="input-select">
              <option value="">Choose a driver...</option>
              <option v-for="l in race.leaders" :key="l.driver" :value="l.driver">{{ l.driver }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>Predicted Action:</label>
            <select v-model="prediction.action" class="input-select">
              <option value="">Choose action...</option>
              <option value="pit_soft">Pit Stop – Soft Tires</option>
              <option value="pit_medium">Pit Stop – Medium Tires</option>
              <option value="pit_hard">Pit Stop – Hard Tires</option>
              <option value="stay_out">Stay Out (No Pit)</option>
            </select>
          </div>
          <div class="form-group">
            <label>Expected Lap:</label>
            <input v-model.number="prediction.lap" type="number"
                   :min="race.currentLap + 1" :max="race.totalLaps"
                   class="input-number" placeholder="Enter lap number" />
          </div>
          <div class="form-group">
            <label>Confidence Level: {{ prediction.confidence }}%</label>
            <input v-model.number="prediction.confidence" type="range" min="1" max="100" class="input-range" />
          </div>
          <button @click="submitPrediction" :disabled="!isPredictionValid" class="submit-btn">
            Submit Prediction
          </button>
        </div>

        <div v-if="userPredictions.length > 0" class="predictions-history">
          <h4>Your Predictions This Race:</h4>
          <div class="prediction-list">
            <div v-for="(pred, i) in userPredictions" :key="i" class="prediction-item" :class="pred.status">
              <span class="pred-driver">{{ pred.driver }}</span>
              <span class="pred-action">{{ formatAction(pred.action) }}</span>
              <span class="pred-lap">Lap {{ pred.lap }}</span>
              <span class="pred-status">{{ pred.status }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import api from '../services/api.js'
export default {
  name: 'LiveRace',
  data() {
    return {
      race: null, loading: true,
      prediction: { driver: '', action: '', lap: null, confidence: 75 },
      userPredictions: []
    }
  },
  computed: {
    isPredictionValid() {
      return this.prediction.driver && this.prediction.action && this.prediction.lap > this.race?.currentLap
    }
  },
  async mounted() {
    try { this.race = await api.getLiveRace(this.$route.params.id) }
    catch(e) { console.error(e) }
    finally { this.loading = false }
  },
  methods: {
    async submitPrediction() {
      if (!this.isPredictionValid) return
      const result = await api.submitPrediction({ raceId: this.race.id, ...this.prediction })
      this.userPredictions.push({ ...this.prediction, status: 'pending' })
      this.prediction = { driver: '', action: '', lap: null, confidence: 75 }
      alert(`Prediction submitted! Potential points: ${result.points}`)
    },
    formatAction(a) {
      return { pit_soft:'Pit → Soft', pit_medium:'Pit → Medium', pit_hard:'Pit → Hard', stay_out:'Stay Out' }[a] || a
    }
  }
}
</script>

<style scoped>
.live-race { max-width: 1200px; margin: 0 auto; }
.loading { text-align: center; padding: 4rem; }
.spinner { width:50px;height:50px;border:4px solid rgba(225,6,0,.1);border-top-color:#e10600;border-radius:50%;animation:spin 1s linear infinite;margin:0 auto 1rem; }
@keyframes spin { to{transform:rotate(360deg)} }
.race-header { display:flex;justify-content:space-between;align-items:center;background:rgba(30,30,30,.8);padding:1.5rem;border-radius:12px;margin-bottom:2rem;border:2px solid #e10600; }
.header-left h2 { font-size:2rem;color:#fff;margin-bottom:.5rem; }
.circuit { color:#888; }
.lap-counter { display:flex;align-items:baseline;gap:.5rem;font-family:monospace; }
.current-lap { font-size:3rem;color:#0f0;font-weight:bold; }
.separator { font-size:2rem;color:#666; }
.total-laps { font-size:1.5rem;color:#888; }
.lap-label { font-size:.9rem;color:#666;margin-left:.5rem; }
.standings-section { margin-bottom:2rem; }
.standings-section h3 { font-size:1.5rem;margin-bottom:1rem;color:#fff; }
.standings-grid { display:grid;gap:1rem; }
.driver-card { background:rgba(30,30,30,.8);border-radius:12px;padding:1.5rem;display:flex;align-items:center;gap:1.5rem;border:2px solid rgba(255,255,255,.1);transition:all .3s ease; }
.driver-card:hover { border-color:#e10600;transform:translateX(5px); }
.position-badge { background:#e10600;width:50px;height:50px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:1.5rem;font-weight:bold;flex-shrink:0; }
.driver-info { flex:1; }
.driver-info h4 { font-size:1.3rem;color:#fff;margin-bottom:.25rem; }
.team { color:#888;font-size:.9rem; }
.driver-stats { display:flex;gap:2rem;flex-wrap:wrap; }
.stat { display:flex;flex-direction:column; }
.stat-label { color:#666;font-size:.75rem;text-transform:uppercase; }
.stat-value { color:#fff;font-weight:600;font-size:.95rem; }
.stat-value.tire { padding:.25rem .5rem;border-radius:4px; }
.tire.soft   { background:#f00;color:#fff; }
.tire.medium { background:#ff0;color:#000; }
.tire.hard   { background:#fff;color:#000; }
.prediction-panel { background:rgba(30,30,30,.8);border-radius:12px;padding:2rem;border:2px solid rgba(255,255,255,.1); }
.prediction-panel h3 { font-size:1.5rem;margin-bottom:.5rem;color:#fff; }
.prediction-hint { color:#888;margin-bottom:1.5rem;font-style:italic; }
.prediction-form { display:grid;gap:1.5rem; }
.form-group { display:flex;flex-direction:column;gap:.5rem; }
.form-group label { color:#fff;font-weight:600;font-size:.9rem; }
.input-select,.input-number { background:rgba(0,0,0,.5);border:2px solid rgba(255,255,255,.2);color:#fff;padding:.75rem;border-radius:8px;font-size:1rem;transition:border-color .3s; }
.input-select:focus,.input-number:focus { outline:none;border-color:#e10600; }
.input-range { width:100%;height:8px;background:rgba(255,255,255,.2);border-radius:10px;outline:none; }
.input-range::-webkit-slider-thumb { appearance:none;width:20px;height:20px;background:#e10600;border-radius:50%;cursor:pointer; }
.submit-btn { background:#e10600;color:#fff;border:none;padding:1rem;border-radius:8px;font-size:1.1rem;font-weight:bold;cursor:pointer;transition:all .3s; }
.submit-btn:hover:not(:disabled) { background:#ff1a1a;transform:scale(1.05); }
.submit-btn:disabled { background:#555;cursor:not-allowed;opacity:.5; }
.predictions-history { margin-top:2rem;padding-top:2rem;border-top:1px solid rgba(255,255,255,.1); }
.predictions-history h4 { color:#fff;margin-bottom:1rem; }
.prediction-list { display:flex;flex-direction:column;gap:.5rem; }
.prediction-item { display:grid;grid-template-columns:2fr 2fr 1fr 1fr;gap:1rem;padding:.75rem;background:rgba(0,0,0,.3);border-radius:6px;border-left:4px solid #888; }
.prediction-item.pending   { border-left-color:#ffa500; }
.prediction-item.correct   { border-left-color:#0f0; }
.prediction-item.incorrect { border-left-color:#f00; }
.pred-driver,.pred-action,.pred-lap,.pred-status { color:#fff;font-size:.9rem; }
.pred-status { text-transform:uppercase;font-weight:600; }
</style>
