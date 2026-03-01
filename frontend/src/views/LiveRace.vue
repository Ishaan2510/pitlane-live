<template>
  <div class="live-race">

    <!-- ═══════════════════════════════════════════════
         NO LIVE SESSION
    ═══════════════════════════════════════════════ -->
    <div v-if="(!liveState || !liveState.drivers?.length) && !loading" class="no-session">
      <div class="no-session-inner">
        <div class="no-session-icon">🏁</div>
        <h2>No Live Session</h2>
        <p>There's no F1 race happening right now.</p>
        <p class="hint">The live feed activates automatically during race weekends.<br>Check back on race day — usually Sundays from ~13:00 local circuit time.</p>

        <!-- ── Simulation picker ── -->
        <div class="sim-box" v-if="simulatableRaces.length">
          <div class="sim-heading">TEST WITH SIMULATION</div>
          <p class="sim-sub">Replay a cached race through the live UI to test predictions, timing tower and track canvas.</p>

          <div class="sim-controls">
            <select v-model="simSelection" class="sim-select">
              <option :value="null" disabled>Select a race…</option>
              <option
                v-for="r in simulatableRaces"
                :key="`${r.year}_${r.round}`"
                :value="r"
              >{{ r.year }} — {{ r.name }}</option>
            </select>

            <button
              class="sim-btn"
              :disabled="!simSelection"
              @click="startSimulation"
            >▶ START SIMULATION</button>
          </div>
        </div>
        <div class="sim-box sim-loading" v-else-if="loadingSimRaces">
          <div class="sim-heading">TEST WITH SIMULATION</div>
          <p class="sim-sub">Loading available races…</p>
        </div>

        <div class="next-race-links" style="margin-top: 1rem">
          <router-link to="/replay" class="btn-outline">← Browse Replays</router-link>
          <button @click="retryConnection" class="btn-outline">↻ Check Again</button>
        </div>
      </div>
    </div>

    <!-- Loading -->
    <div v-else-if="loading" class="loading-screen">
      <div class="loading-pip"></div>
      <p>Connecting to live timing…</p>
    </div>

    <!-- ═══════════════════════════════════════════════
         LIVE / SIMULATED INTERFACE
    ═══════════════════════════════════════════════ -->
    <div v-else class="live-interface">

      <!-- ── Top bar ── -->
      <div class="top-bar">
        <div class="top-left">
          <span class="live-pill" :class="{ 'sim-pill': isSimulated }">
            <span class="live-dot"></span>
            {{ isSimulated ? 'SIMULATED' : 'LIVE' }}
          </span>
          <span class="session-name">{{ sessionName }}</span>
          <!-- Simulation lap counter + controls -->
          <span v-if="isSimulated" class="sim-lap-display">
            Lap {{ simLap }} / {{ simTotalLaps }}
            <button class="sim-nav-btn" @click="simStepLap(-5)"  title="−5 laps">«</button>
            <button class="sim-nav-btn" @click="simStepLap(-1)"  title="−1 lap">‹</button>
            <button class="sim-nav-btn" @click="simTogglePlay()" title="Play/Pause">
              {{ simPlaying ? '⏸' : '▶' }}
            </button>
            <button class="sim-nav-btn" @click="simStepLap(1)"   title="+1 lap">›</button>
            <button class="sim-nav-btn" @click="simStepLap(5)"   title="+5 laps">»</button>
            <button class="sim-nav-btn stop" @click="stopSimulation" title="Stop simulation">✕</button>
          </span>
        </div>

        <!-- Race control message banner (center) -->
        <div class="rc-banner" :class="rcBannerClass" v-if="liveState.race_control">
          <span class="rc-flag">{{ rcFlag }}</span>
          <span class="rc-text">{{ liveState.race_control.message || liveState.race_control.flag }}</span>
        </div>
        <div class="rc-banner-empty" v-else></div>

        <div class="top-right">
          <span class="update-time">↻ {{ lastUpdated }}</span>
          <span class="driver-count">{{ liveState.drivers.length }} drivers</span>
        </div>
      </div>

      <!-- ── Main 3-column body ── -->
      <div class="main-layout">

        <!-- LEFT: Timing tower -->
        <div class="timing-tower">
          <div class="tower-header">
            <span class="th-pos">P</span>
            <span class="th-driver">DRIVER</span>
            <span class="th-gap">GAP</span>
            <span class="th-interval">INT</span>
            <span class="th-tyre">TYRE</span>
          </div>

          <div
            v-for="driver in liveState.drivers"
            :key="driver.driver"
            class="tower-row"
            :class="{
              selected:  selectedDriver === driver.driver,
              'pos-1':   driver.position === 1,
              'pos-2':   driver.position === 2,
              'pos-3':   driver.position === 3,
              'in-zone': driver.position <= 10
            }"
            @click="selectDriver(driver.driver)"
          >
            <span class="tr-pos" :class="posClass(driver.position)">
              {{ driver.position }}
            </span>
            <div class="tr-driver">
              <span class="tr-code">{{ driver.driver }}</span>
              <span class="tr-team" :style="{ color: teamColor(driver.team) }">{{ shortTeam(driver.team) }}</span>
            </div>
            <span class="tr-gap" :class="{ leader: driver.gap === 'LEADER' }">
              {{ driver.gap === 'LEADER' ? '—' : driver.gap }}
            </span>
            <span class="tr-interval">
              {{ formatInterval(driver.interval) }}
            </span>
            <div class="tr-tyre">
              <span class="tyre-dot" :class="(driver.compound || 'unknown').toLowerCase()"></span>
              <span class="tyre-age">{{ driver.tire_age ?? '?' }}</span>
            </div>
          </div>
        </div>

        <!-- CENTER: Track canvas + pit log strip -->
        <div class="track-area">
          <TrackCanvas
            :drivers="canvasDrivers"
            :circuitData="circuitData"
            :selectedDriver="selectedDriver"
            :lapDuration="3000"
            @select-driver="selectDriver"
          />

          <!-- Pit stop log — compact strip below canvas, no overlap -->
          <div class="rc-log" v-if="rcHistory.length">
            <span
              v-for="(msg, i) in rcHistory.slice(0, 3)"
              :key="i"
              class="rc-log-item"
              :class="rcClass(msg)"
            >
              <span class="rc-log-time">{{ msg.time }}</span>
              <span class="rc-log-text">{{ msg.text }}</span>
            </span>
          </div>
        </div>

        <!-- RIGHT: Selected driver + prediction -->
        <div class="right-panel">

          <!-- Selected driver card -->
          <div class="selected-card" v-if="selectedDriverData">
            <div class="sc-header">
              <div class="sc-code">{{ selectedDriverData.driver }}</div>
              <div class="sc-pos" :class="posClass(selectedDriverData.position)">
                P{{ selectedDriverData.position }}
              </div>
            </div>
            <div class="sc-team" :style="{ color: teamColor(selectedDriverData.team) }">
              {{ selectedDriverData.team }}
            </div>

            <div class="sc-stats">
              <div class="sc-stat">
                <span class="sc-label">Gap to Leader</span>
                <span class="sc-value" :class="{ leader: selectedDriverData.gap === 'LEADER' }">
                  {{ selectedDriverData.gap === 'LEADER' ? 'LEADER' : selectedDriverData.gap }}
                </span>
              </div>
              <div class="sc-stat">
                <span class="sc-label">Interval</span>
                <span class="sc-value">{{ formatInterval(selectedDriverData.interval) }}</span>
              </div>
              <div class="sc-stat">
                <span class="sc-label">Tyre</span>
                <span class="sc-tyre-pill" :class="(selectedDriverData.compound || 'unknown').toLowerCase()">
                  {{ tyreEmoji(selectedDriverData.compound) }} {{ selectedDriverData.compound || '?' }}
                </span>
              </div>
              <div class="sc-stat">
                <span class="sc-label">Tyre Age</span>
                <span class="sc-value">{{ selectedDriverData.tire_age ?? '—' }} laps</span>
              </div>
            </div>
          </div>
          <div class="selected-card-empty" v-else>
            <span>🏎</span>
            <p>Click a driver on the track or timing tower to inspect</p>
          </div>

          <div class="panel-divider" />

          <!-- Prediction panel -->
          <div class="prediction-panel">
            <div class="panel-heading">MAKE PREDICTION</div>

            <div v-if="!selectedDriver" class="pred-hint">
              Select a driver first
            </div>
            <div v-else class="pred-form">
              <div class="pred-driver-chip">
                Predicting: <strong>{{ selectedDriver }}</strong>
              </div>

              <div class="pred-field">
                <label>Action</label>
                <div class="action-grid">
                  <button
                    v-for="action in actions"
                    :key="action.value"
                    class="action-btn"
                    :class="[action.cls, { active: prediction.action === action.value }]"
                    @click="prediction.action = action.value"
                  >
                    {{ action.emoji }} {{ action.label }}
                  </button>
                </div>
              </div>

              <!-- Predicted lap with ±2 window explanation -->
              <div class="pred-field" v-if="isSimulated">
                <label>On lap: <strong>{{ prediction.targetLap }}</strong>
                  <span class="window-hint">(scores if ±2 laps correct)</span>
                </label>
                <input
                  v-model.number="prediction.targetLap"
                  type="range"
                  :min="simLap"
                  :max="simTotalLaps"
                  step="1"
                  class="conf-slider"
                />
                <div class="lap-range-hint">
                  Window: laps {{ Math.max(1, prediction.targetLap - 2) }}–{{ Math.min(simTotalLaps, prediction.targetLap + 2) }}
                </div>
              </div>

              <div class="pred-field">
                <label>Confidence: <strong>{{ prediction.confidence }}%</strong></label>
                <input v-model.number="prediction.confidence" type="range" min="10" max="100" step="5" class="conf-slider" />
              </div>

              <button
                @click="submitPrediction"
                :disabled="!prediction.action || submitting"
                class="pred-submit"
              >
                {{ submitting ? 'Submitting…' : '🔒 Lock In Prediction' }}
              </button>

              <div v-if="lastPrediction" class="last-prediction">
                ✓ Locked: {{ lastPrediction.driver }} · {{ formatAction(lastPrediction.action) }}
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  </div>
</template>

<script>
import TrackCanvas from '../components/TrackCanvas.vue'
import api from '../services/api.js'

const TEAM_COLORS = {
  'Red Bull Racing': '#3671C6', 'Ferrari': '#E8002D', 'Mercedes': '#27F4D2',
  'McLaren': '#FF8000', 'Aston Martin': '#229971', 'Alpine': '#FF87BC',
  'Williams': '#64C4FF', 'RB': '#6692FF', 'Kick Sauber': '#52E252',
  'Haas F1 Team': '#B6BABD'
}

const SHORT_TEAM = {
  'Red Bull Racing': 'RBR', 'Ferrari': 'FER', 'Mercedes': 'MER',
  'McLaren': 'MCL', 'Aston Martin': 'AMR', 'Alpine': 'ALP',
  'Williams': 'WIL', 'RB': 'RB', 'Kick Sauber': 'SAU', 'Haas F1 Team': 'HAA'
}

export default {
  name: 'LiveRace',
  components: { TrackCanvas },

  data() {
    return {
      loading:        true,
      liveState:      null,
      selectedDriver: null,
      rcHistory:      [],
      lastUpdated:    '—',
      eventSource:    null,
      pollInterval:   null,
      sessionName:    'Live Race',
      circuitData:    null,   // ← real circuit SVG coords for TrackCanvas

      prediction:     { action: '', confidence: 75, targetLap: 1 },
      submitting:     false,
      lastPrediction: null,

      actions: [
        { value: 'pit_soft',   label: 'Pit → Soft',   emoji: '🔴', cls: 'soft'   },
        { value: 'pit_medium', label: 'Pit → Medium', emoji: '🟡', cls: 'medium' },
        { value: 'pit_hard',   label: 'Pit → Hard',   emoji: '⚪', cls: 'hard'   },
        { value: 'stay_out',   label: 'Stay Out',     emoji: '⏩', cls: 'stay'   },
      ],

      // ── Simulation state ──
      simulatableRaces:  [],
      loadingSimRaces:   true,
      simSelection:      null,   // selected race object from picker
      isSimulated:       false,
      simLap:            1,
      simTotalLaps:      0,
      simPlaying:        false,
      simPlayInterval:   null,
      simYear:           null,
      simRound:          null,
    }
  },

  computed: {
    selectedDriverData() {
      if (!this.selectedDriver || !this.liveState) return null
      return this.liveState.drivers.find(d => d.driver === this.selectedDriver) ?? null
    },
    canvasDrivers() {
      if (!this.liveState) return []
      return this.liveState.drivers.map(d => ({
        driver:    d.driver,
        team:      d.team,
        position:  d.position,
        gap:       d.gap,
        compound:  d.compound,
        tire_life: d.tire_age
      }))
    },
    rcBannerClass() {
      if (!this.liveState?.race_control) return ''
      const flag = this.liveState.race_control.flag || ''
      if (flag.includes('RED'))    return 'rc-red'
      if (flag.includes('YELLOW') || flag.includes('VSC')) return 'rc-yellow'
      if (flag.includes('SAFETY')) return 'rc-safety'
      if (flag.includes('GREEN'))  return 'rc-green'
      if (flag === 'PIT')          return 'rc-neutral'
      return 'rc-neutral'
    },
    rcFlag() {
      const flag = this.liveState?.race_control?.flag || ''
      if (flag.includes('RED'))       return '🚩'
      if (flag.includes('YELLOW'))    return '🟡'
      if (flag.includes('SAFETY'))    return '🚗'
      if (flag.includes('VSC'))       return '🟡'
      if (flag.includes('GREEN'))     return '🟢'
      if (flag.includes('CHEQUERED')) return '🏁'
      if (flag === 'PIT')             return '🔧'
      return '📢'
    }
  },

  async mounted() {
    await this.connect()
    this.loadSimulatableRaces()
  },

  beforeUnmount() {
    this.disconnect()
    this.stopSimulation()
  },

  methods: {
    // ── Connection (real live) ────────────────────────────────────────────────
    async connect() {
      this.loading = true
      try {
        const state = await this.fetchState()
        if (!state || state.error) {
          this.liveState = null
          this.loading   = false
          return
        }
        this.applyState(state)
      } catch {
        this.liveState = null
        this.loading   = false
        return
      }
      this.loading = false
      this.connectSSE()
    },

    connectSSE() {
      try {
        this.eventSource = new EventSource(`/api/replay/live/stream`)
        this.eventSource.onmessage = (e) => {
          try {
            const state = JSON.parse(e.data)
            if (!state.error) this.applyState(state)
          } catch { /* ignore */ }
        }
        this.eventSource.onerror = () => {
          this.eventSource?.close()
          this.eventSource = null
          this.startPolling()
        }
      } catch {
        this.startPolling()
      }
    },

    startPolling() {
      this.pollInterval = setInterval(async () => {
        try {
          const state = await this.fetchState()
          if (state && !state.error) this.applyState(state)
        } catch { /* ignore */ }
      }, 4000)
    },

    disconnect() {
      this.eventSource?.close()
      this.eventSource = null
      clearInterval(this.pollInterval)
      this.pollInterval = null
    },

    async fetchState() {
      const res = await fetch(`/api/replay/live/state`)
      return await res.json()
    },

    applyState(state) {
      this.liveState = state
      if (state.drivers?.length) {
        this.sessionName = this.isSimulated
          ? `SIMULATION — ${state.sim_race_name || ''}`
          : `Formula 1 – Session ${state.session_key}`
      }
      if (state.race_control) {
        const text = state.race_control.message || state.race_control.flag || ''
        if (text && (this.rcHistory.length === 0 || this.rcHistory[0].text !== text)) {
          this.rcHistory.unshift({
            text,
            flag: state.race_control.flag || '',
            time: new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
          })
          if (this.rcHistory.length > 10) this.rcHistory.pop()
        }
      }
      this.lastUpdated = new Date().toLocaleTimeString('en-GB', {
        hour: '2-digit', minute: '2-digit', second: '2-digit'
      })
    },

    async retryConnection() {
      this.disconnect()
      await this.connect()
    },

    // ── Simulation ────────────────────────────────────────────────────────────
    async loadSimulatableRaces() {
      this.loadingSimRaces = true
      try {
        const res = await fetch('/api/replay/simulate/races')
        this.simulatableRaces = await res.json()
      } catch {
        this.simulatableRaces = []
      } finally {
        this.loadingSimRaces = false
      }
    },

    async startSimulation() {
      if (!this.simSelection) return
      this.disconnect()   // stop polling real live endpoint

      this.isSimulated  = true
      this.simYear      = this.simSelection.year
      this.simRound     = this.simSelection.round
      this.simTotalLaps = this.simSelection.total_laps
      this.simLap       = 1
      this.rcHistory    = []
      this.circuitData  = null

      // Load real circuit layout for TrackCanvas
      try {
        const res = await fetch(`/api/replay/circuit/${this.simYear}/${this.simRound}`)
        if (res.ok) this.circuitData = await res.json()
      } catch { /* TrackCanvas falls back to oval if null */ }

      await this.fetchSimState()
      this.prediction.targetLap = Math.min(this.simTotalLaps, this.simLap + 3)
      this.simPlaying = true
      this.simPlayInterval = setInterval(async () => {
        if (this.simLap >= this.simTotalLaps) {
          this.simTogglePlay()   // auto-pause at end
          return
        }
        this.simLap++
        await this.fetchSimState()
      }, 3000)
    },

    stopSimulation() {
      this.isSimulated = false
      this.simPlaying  = false
      clearInterval(this.simPlayInterval)
      this.simPlayInterval = null
      this.liveState   = null
      this.circuitData = null
      this.sessionName = 'Live Race'
      this.rcHistory   = []
    },

    simTogglePlay() {
      if (this.simPlaying) {
        this.simPlaying = false
        clearInterval(this.simPlayInterval)
        this.simPlayInterval = null
      } else {
        this.simPlaying = true
        this.simPlayInterval = setInterval(async () => {
          if (this.simLap >= this.simTotalLaps) {
            this.simTogglePlay()
            return
          }
          this.simLap++
          await this.fetchSimState()
        }, 3000)
      }
    },

    async simStepLap(delta) {
      this.simLap = Math.max(1, Math.min(this.simTotalLaps, this.simLap + delta))
      await this.fetchSimState()
    },

    async fetchSimState() {
      try {
        const res = await fetch(
          `/api/replay/simulate/state?year=${this.simYear}&round=${this.simRound}&lap=${this.simLap}`
        )
        const state = await res.json()
        if (!state.error) {
          this.simTotalLaps = state.sim_total_laps || this.simTotalLaps
          this.applyState(state)
        }
      } catch { /* ignore */ }
    },

    // ── Driver selection ──────────────────────────────────────────────────────
    selectDriver(code) {
      if (this.selectedDriver === code) {
        this.selectedDriver    = null
        this.prediction.action = ''
        return
      }
      this.selectedDriver = code
    },

    // ── Prediction ────────────────────────────────────────────────────────────
    async submitPrediction() {
      if (!this.prediction.action || !this.selectedDriver) return
      this.submitting = true
      try {
        await api.submitPrediction({
          raceId:     0,
          driver:     this.selectedDriver,
          action:     this.prediction.action,
          lap:        this.isSimulated ? this.prediction.targetLap : 0,
          confidence: this.prediction.confidence
        })
        this.lastPrediction = {
          driver: this.selectedDriver,
          action: this.prediction.action,
          lap:    this.isSimulated ? this.prediction.targetLap : null
        }
        this.prediction.action    = ''
        // Advance targetLap default forward for next prediction
        if (this.isSimulated) {
          this.prediction.targetLap = Math.min(this.simTotalLaps, this.simLap + 3)
        }
      } catch (e) {
        console.error('Prediction failed:', e)
      } finally {
        this.submitting = false
      }
    },

    // ── Helpers ───────────────────────────────────────────────────────────────
    teamColor(team)  { return TEAM_COLORS[team] || '#888' },
    shortTeam(team)  { return SHORT_TEAM[team]  || team?.slice(0, 3).toUpperCase() || '???' },
    tyreEmoji(c) {
      return { SOFT:'🔴', MEDIUM:'🟡', HARD:'⚪', INTERMEDIATE:'🟢', WET:'🔵' }[c] || '⚫'
    },
    posClass(pos) {
      if (pos === 1) return 'p1'
      if (pos === 2) return 'p2'
      if (pos === 3) return 'p3'
      return ''
    },
    formatInterval(interval) {
      if (!interval) return '—'
      if (typeof interval === 'number') return `+${interval.toFixed(3)}`
      return interval
    },
    rcClass(msg) {
      const f = msg.flag || ''
      if (f.includes('RED'))    return 'rc-log-red'
      if (f.includes('SAFETY')) return 'rc-log-safety'
      if (f.includes('YELLOW') || f.includes('VSC')) return 'rc-log-yellow'
      if (f.includes('GREEN'))  return 'rc-log-green'
      return 'rc-log-neutral'
    },
    formatAction(a) {
      return { pit_soft:'Pit → Soft', pit_medium:'Pit → Medium',
               pit_hard:'Pit → Hard', stay_out:'Stay Out' }[a] || a
    }
  }
}
</script>

<style scoped>
/* ════════════════════════════════════════════════════
   BASE
════════════════════════════════════════════════════ */
.live-race {
  height: calc(100vh - 65px);
  background: #080808;
  display: flex;
  flex-direction: column;
  font-family: 'Work Sans', sans-serif;
}

/* ════════════════════════════════════════════════════
   NO SESSION / LOADING
════════════════════════════════════════════════════ */
.no-session {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}
.no-session-inner {
  text-align: center;
  max-width: 520px;
  padding: 3rem;
}
.no-session-icon { font-size: 4rem; margin-bottom: 1.5rem; }
.no-session-inner h2 {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 2.5rem;
  color: #fff;
  letter-spacing: 0.05em;
  margin-bottom: 0.75rem;
}
.no-session-inner p { color: #555; line-height: 1.7; margin-bottom: 0.5rem; }
.hint { font-size: 0.85rem; color: #444; }

/* ── Simulation box ── */
.sim-box {
  margin-top: 2rem;
  border: 1px solid #1e1e1e;
  padding: 1.5rem;
  text-align: left;
  background: #0d0d0d;
}
.sim-heading {
  font-size: 0.62rem;
  letter-spacing: 0.18em;
  color: #e10600;
  font-weight: 700;
  margin-bottom: 0.5rem;
}
.sim-sub {
  font-size: 0.8rem;
  color: #444;
  margin-bottom: 1.25rem;
  line-height: 1.6;
}
.sim-controls {
  display: flex;
  gap: 0.75rem;
  align-items: center;
}
.sim-select {
  flex: 1;
  background: #111;
  border: 1px solid #2a2a2a;
  color: #ccc;
  padding: 0.5rem 0.75rem;
  font-size: 0.82rem;
  cursor: pointer;
  border-radius: 2px;
}
.sim-select option { background: #111; }
.sim-btn {
  padding: 0.5rem 1.1rem;
  background: rgba(225,6,0,0.15);
  border: 1px solid rgba(225,6,0,0.35);
  color: #e10600;
  font-size: 0.82rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  cursor: pointer;
  border-radius: 2px;
  white-space: nowrap;
  transition: all 0.15s;
}
.sim-btn:hover:not(:disabled) {
  background: rgba(225,6,0,0.3);
  border-color: #e10600;
}
.sim-btn:disabled { opacity: 0.35; cursor: not-allowed; }
.sim-loading .sim-sub { color: #333; font-style: italic; }

.next-race-links {
  display: flex;
  gap: 1rem;
  justify-content: center;
}
.btn-outline {
  padding: 0.55rem 1.4rem;
  border: 1px solid #2a2a2a;
  background: transparent;
  color: #999;
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  border-radius: 2px;
  text-decoration: none;
  display: inline-block;
  transition: all 0.15s;
}
.btn-outline:hover { border-color: #888; color: #fff; }

.loading-screen {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1.25rem;
  color: #444;
}
.loading-pip {
  width: 12px; height: 12px;
  background: #e10600;
  border-radius: 50%;
  animation: pip-pulse 1s ease-in-out infinite;
}
@keyframes pip-pulse {
  0%, 100% { transform: scale(1);   opacity: 1; }
  50%       { transform: scale(2.4); opacity: 0.4; }
}

/* ════════════════════════════════════════════════════
   LIVE INTERFACE
════════════════════════════════════════════════════ */
.live-interface {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* ── Top bar ── */
.top-bar {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  padding: 0 1.25rem;
  height: 46px;
  border-bottom: 1px solid #141414;
  background: #080808;
  flex-shrink: 0;
  gap: 1rem;
}

.top-left {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  overflow: hidden;
}

.live-pill {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  background: rgba(225, 6, 0, 0.15);
  border: 1px solid rgba(225, 6, 0, 0.35);
  color: #e10600;
  font-size: 0.68rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  padding: 0.25rem 0.65rem;
  border-radius: 2px;
  flex-shrink: 0;
}
.live-pill.sim-pill {
  background: rgba(100, 100, 255, 0.1);
  border-color: rgba(100, 100, 255, 0.3);
  color: #8888ff;
}
.live-dot {
  width: 6px; height: 6px;
  background: currentColor;
  border-radius: 50%;
  animation: live-blink 1.2s ease-in-out infinite;
}
@keyframes live-blink {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.2; }
}
.session-name {
  font-size: 0.8rem;
  color: #666;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Simulation lap display */
.sim-lap-display {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.75rem;
  color: #8888ff;
  font-family: monospace;
  flex-shrink: 0;
}
.sim-nav-btn {
  background: transparent;
  border: 1px solid #2a2a2a;
  color: #666;
  width: 22px; height: 22px;
  font-size: 0.72rem;
  cursor: pointer;
  border-radius: 2px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  transition: all 0.12s;
}
.sim-nav-btn:hover  { border-color: #8888ff; color: #8888ff; }
.sim-nav-btn.stop:hover { border-color: #e10600; color: #e10600; }

/* Race control banner */
.rc-banner {
  padding: 0.3rem 1rem;
  border-radius: 2px;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  border: 1px solid transparent;
  transition: all 0.3s;
}
.rc-banner-empty { height: 28px; }
.rc-red     { background: rgba(200,0,0,0.25);   border-color: rgba(200,0,0,0.5);    color: #ff7777; }
.rc-yellow  { background: rgba(200,170,0,0.25); border-color: rgba(200,170,0,0.4);  color: #ffee77; }
.rc-safety  { background: rgba(200,130,0,0.25); border-color: rgba(200,130,0,0.4);  color: #ffaa44; }
.rc-green   { background: rgba(0,180,60,0.2);   border-color: rgba(0,180,60,0.35);  color: #77ff99; }
.rc-neutral { background: rgba(80,80,80,0.2);   border-color: rgba(80,80,80,0.35);  color: #999; }

.top-right {
  display: flex;
  align-items: center;
  gap: 1rem;
  justify-content: flex-end;
}
.update-time, .driver-count {
  font-size: 0.72rem;
  color: #3a3a3a;
  font-family: monospace;
}

/* ── Main 3-column layout ── */
.main-layout {
  flex: 1;
  display: grid;
  grid-template-columns: 260px 1fr 240px;
  overflow: hidden;
  min-height: 0;
}

/* ════════════════════════════════════════════════════
   TIMING TOWER (left)
════════════════════════════════════════════════════ */
.timing-tower {
  border-right: 1px solid #111;
  overflow-y: auto;
  background: #080808;
  display: flex;
  flex-direction: column;
}
.tower-header {
  display: grid;
  grid-template-columns: 32px 1fr 56px 56px 52px;
  padding: 0.4rem 0.75rem;
  border-bottom: 1px solid #141414;
  position: sticky;
  top: 0;
  background: #0a0a0a;
  z-index: 2;
}
.tower-header span {
  font-size: 0.6rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: #333;
  font-weight: 700;
}
.tower-row {
  display: grid;
  grid-template-columns: 32px 1fr 56px 56px 52px;
  align-items: center;
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid rgba(255,255,255,0.025);
  cursor: pointer;
  transition: background 0.1s;
  position: relative;
}
.tower-row::before {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 2px;
  background: transparent;
  transition: background 0.15s;
}
.tower-row.pos-1::before { background: #ffd700; }
.tower-row.pos-2::before { background: #c0c0c0; }
.tower-row.pos-3::before { background: #cd7f32; }
.tower-row:hover    { background: rgba(255,255,255,0.03); }
.tower-row.selected { background: rgba(255,255,255,0.06); }
.tower-row.selected::before { background: #e10600; }

.tr-pos { font-family: 'Bebas Neue', sans-serif; font-size: 1.05rem; color: #444; text-align: center; }
.tr-pos.p1 { color: #ffd700; }
.tr-pos.p2 { color: #c0c0c0; }
.tr-pos.p3 { color: #cd7f32; }
.tr-driver { display: flex; flex-direction: column; gap: 0.05rem; padding-left: 0.3rem; }
.tr-code { font-family: monospace; font-size: 0.85rem; font-weight: 800; color: #ddd; letter-spacing: 0.03em; }
.tr-team { font-size: 0.6rem; font-weight: 600; letter-spacing: 0.05em; opacity: 0.8; }
.tr-gap { font-family: monospace; font-size: 0.75rem; color: #666; text-align: right; padding-right: 0.25rem; }
.tr-gap.leader { color: #ffd700; font-weight: 800; font-size: 0.65rem; }
.tr-interval { font-family: monospace; font-size: 0.72rem; color: #444; text-align: right; padding-right: 0.25rem; }
.tr-tyre { display: flex; align-items: center; gap: 0.3rem; justify-content: center; }
.tyre-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.tyre-dot.soft         { background: #cc2222; }
.tyre-dot.medium       { background: #cccc00; }
.tyre-dot.hard         { background: #cccccc; }
.tyre-dot.intermediate { background: #00aa44; }
.tyre-dot.wet          { background: #2255cc; }
.tyre-dot.unknown      { background: #444; }
.tyre-age { font-family: monospace; font-size: 0.68rem; color: #444; }

/* ════════════════════════════════════════════════════
   TRACK AREA (center)
════════════════════════════════════════════════════ */
.track-area {
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}
/* TrackCanvas itself gets all the remaining space */
.track-area > :first-child {
  flex: 1;
  min-height: 0;
}
/* Compact pit-stop strip — sits BELOW the canvas, never overlaps */
.rc-log {
  flex-shrink: 0;
  display: flex;
  flex-direction: row;
  flex-wrap: wrap;
  gap: 0.25rem 0.75rem;
  padding: 0.3rem 0.75rem;
  background: #0a0a0a;
  border-top: 1px solid #141414;
  overflow: hidden;
  max-height: 28px;   /* single-line strip */
  pointer-events: none;
}
.rc-log-item {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.65rem;
  white-space: nowrap;
}
.rc-log-time { color: #333; font-family: monospace; }
.rc-log-text { color: #555; }
.rc-log-red    .rc-log-text { color: #ff6666; }
.rc-log-yellow .rc-log-text { color: #ddcc55; }
.rc-log-safety .rc-log-text { color: #ff9944; }
.rc-log-green  .rc-log-text { color: #66dd88; }

/* ════════════════════════════════════════════════════
   RIGHT PANEL
════════════════════════════════════════════════════ */
.right-panel {
  border-left: 1px solid #111;
  background: #080808;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}
.selected-card { padding: 1rem 0.9rem; border-bottom: 1px solid #111; }
.selected-card-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.6rem;
  padding: 2rem 1rem;
  color: #2a2a2a;
  font-size: 0.8rem;
  text-align: center;
  border-bottom: 1px solid #111;
}
.selected-card-empty span { font-size: 1.6rem; }
.sc-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.2rem; }
.sc-code { font-family: monospace; font-size: 1.3rem; font-weight: 900; color: #fff; letter-spacing: 0.05em; }
.sc-pos { font-family: 'Bebas Neue', sans-serif; font-size: 1.2rem; color: #555; letter-spacing: 0.05em; }
.sc-pos.p1 { color: #ffd700; }
.sc-pos.p2 { color: #c0c0c0; }
.sc-pos.p3 { color: #cd7f32; }
.sc-team { font-size: 0.72rem; font-weight: 600; margin-bottom: 0.9rem; letter-spacing: 0.04em; }
.sc-stats { display: grid; grid-template-columns: 1fr 1fr; gap: 0.65rem 0.5rem; }
.sc-stat { display: flex; flex-direction: column; gap: 0.15rem; }
.sc-label { font-size: 0.6rem; text-transform: uppercase; letter-spacing: 0.08em; color: #3a3a3a; }
.sc-value { font-family: monospace; font-size: 0.82rem; font-weight: 600; color: #bbb; }
.sc-value.leader { color: #ffd700; font-weight: 800; }
.sc-tyre-pill { display: inline-block; padding: 0.15rem 0.4rem; border-radius: 2px; font-size: 0.72rem; font-weight: 700; }
.sc-tyre-pill.soft         { background: rgba(200,0,0,0.25);    color: #ff9999; }
.sc-tyre-pill.medium       { background: rgba(200,200,0,0.2);   color: #ffff99; }
.sc-tyre-pill.hard         { background: rgba(200,200,200,0.15); color: #ccc; }
.sc-tyre-pill.intermediate { background: rgba(0,180,0,0.2);    color: #99ff99; }
.sc-tyre-pill.wet          { background: rgba(0,80,220,0.2);   color: #99aaff; }
.sc-tyre-pill.unknown      { background: rgba(80,80,80,0.2);   color: #666; }
.panel-divider { height: 1px; background: #111; flex-shrink: 0; }

/* ── Prediction panel ── */
.prediction-panel { padding: 0.9rem; flex: 1; }
.panel-heading { font-size: 0.62rem; text-transform: uppercase; letter-spacing: 0.12em; color: #333; margin-bottom: 0.9rem; }
.pred-hint { font-size: 0.78rem; color: #2d2d2d; text-align: center; padding: 1rem 0; }
.pred-form { display: flex; flex-direction: column; gap: 0.8rem; }
.pred-driver-chip { font-size: 0.72rem; color: #555; background: #0f0f0f; border: 1px solid #1a1a1a; padding: 0.35rem 0.6rem; border-radius: 2px; }
.pred-driver-chip strong { color: #fff; font-family: monospace; }
.pred-field { display: flex; flex-direction: column; gap: 0.4rem; }
.pred-field label { font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.08em; color: #3a3a3a; }
.pred-field label strong { color: #888; }
.action-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 4px; }
.action-btn {
  padding: 0.4rem 0.3rem;
  border: 1px solid #1a1a1a;
  background: transparent;
  color: #555;
  font-size: 0.7rem;
  font-weight: 600;
  cursor: pointer;
  border-radius: 2px;
  transition: all 0.12s;
  white-space: nowrap;
}
.action-btn.soft.active   { background: rgba(200,0,0,0.25);    border-color: #aa0000; color: #ff9999; }
.action-btn.medium.active { background: rgba(180,180,0,0.2);   border-color: #aaaa00; color: #ffff88; }
.action-btn.hard.active   { background: rgba(180,180,180,0.15); border-color: #aaa;   color: #ddd; }
.action-btn.stay.active   { background: rgba(0,100,220,0.2);   border-color: #0055aa; color: #88aaff; }
.action-btn:hover:not(.active) { border-color: #333; color: #888; }
.conf-slider { width: 100%; height: 3px; background: #1a1a1a; border-radius: 2px; outline: none; cursor: pointer; appearance: none; }
.conf-slider::-webkit-slider-thumb { appearance: none; width: 14px; height: 14px; background: #e10600; border-radius: 50%; cursor: pointer; }
.pred-submit {
  background: rgba(225, 6, 0, 0.15);
  border: 1px solid rgba(225, 6, 0, 0.3);
  color: #e10600;
  padding: 0.55rem;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  cursor: pointer;
  border-radius: 2px;
  transition: all 0.15s;
}
.pred-submit:hover:not(:disabled) { background: rgba(225, 6, 0, 0.3); border-color: #e10600; }
.pred-submit:disabled { opacity: 0.3; cursor: not-allowed; }
.last-prediction { font-size: 0.7rem; color: #2a6; text-align: center; padding: 0.3rem; }
.window-hint { font-size: 0.58rem; color: #2a2a2a; margin-left: 0.4rem; font-weight: 400; letter-spacing: 0; text-transform: none; }
.lap-range-hint { font-size: 0.62rem; color: #2a2a2a; margin-top: 0.2rem; font-family: monospace; }
</style>