<template>
  <div class="live-race">

    <!-- ═══════════════════════════════════════════════
         NO LIVE SESSION
    ═══════════════════════════════════════════════ -->
    <div v-if="!liveState && !loading" class="no-session">
      <div class="no-session-inner">
        <div class="no-session-icon">🏁</div>
        <h2>No Live Session</h2>
        <p>There's no F1 race happening right now.</p>
        <p class="hint">The live feed activates automatically during race weekends.<br>Check back on race day — usually Sundays from ~13:00 local circuit time.</p>
        <div class="next-race-links">
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
         LIVE INTERFACE
    ═══════════════════════════════════════════════ -->
    <div v-else class="live-interface">

      <!-- ── Top bar ── -->
      <div class="top-bar">
        <div class="top-left">
          <span class="live-pill">
            <span class="live-dot"></span> LIVE
          </span>
          <span class="session-name">{{ sessionName }}</span>
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

        <!-- CENTER: Track canvas -->
        <div class="track-area">
          <TrackCanvas
            :drivers="canvasDrivers"
            :circuitData="null"
            :selectedDriver="selectedDriver"
            :lapDuration="3000"
            @select-driver="selectDriver"
          />

          <!-- Race control history overlay (bottom of canvas) -->
          <div class="rc-log" v-if="rcHistory.length">
            <div
              v-for="(msg, i) in rcHistory.slice(0, 3)"
              :key="i"
              class="rc-log-item"
              :class="rcClass(msg)"
            >
              <span class="rc-log-time">{{ msg.time }}</span>
              <span class="rc-log-text">{{ msg.text }}</span>
            </div>
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
      liveState:      null,        // latest state from SSE / polling
      selectedDriver: null,
      rcHistory:      [],          // race control message history
      lastUpdated:    '—',
      eventSource:    null,        // SSE connection
      pollInterval:   null,        // fallback polling
      sessionName:    'Live Race',

      prediction: { action: '', confidence: 75 },
      submitting:     false,
      lastPrediction: null,

      actions: [
        { value: 'pit_soft',   label: 'Pit → Soft',   emoji: '🔴', cls: 'soft'   },
        { value: 'pit_medium', label: 'Pit → Medium', emoji: '🟡', cls: 'medium' },
        { value: 'pit_hard',   label: 'Pit → Hard',   emoji: '⚪', cls: 'hard'   },
        { value: 'stay_out',   label: 'Stay Out',     emoji: '⏩', cls: 'stay'   },
      ]
    }
  },

  computed: {
    selectedDriverData() {
      if (!this.selectedDriver || !this.liveState) return null
      return this.liveState.drivers.find(d => d.driver === this.selectedDriver) ?? null
    },

    // Convert live drivers to the shape TrackCanvas expects
    canvasDrivers() {
      if (!this.liveState) return []
      return this.liveState.drivers.map(d => ({
        driver:   d.driver,
        team:     d.team,
        position: d.position,
        gap:      d.gap,
        compound: d.compound,
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
      return 'rc-neutral'
    },

    rcFlag() {
      const flag = this.liveState?.race_control?.flag || ''
      if (flag.includes('RED'))         return '🚩'
      if (flag.includes('YELLOW'))      return '🟡'
      if (flag.includes('SAFETY'))      return '🚗'
      if (flag.includes('VSC'))         return '🟡'
      if (flag.includes('GREEN'))       return '🟢'
      if (flag.includes('CHEQUERED'))   return '🏁'
      return '📢'
    }
  },

  async mounted() {
    await this.connect()
  },

  beforeUnmount() {
    this.disconnect()
  },

  methods: {
    // ── Connection ────────────────────────────────────────────────────────────
    async connect() {
      this.loading = true

      // First fetch to check if there's a live session at all
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

      // Try SSE first for push updates
      this.connectSSE()
    },

    connectSSE() {
      try {
        this.eventSource = new EventSource(`/api/replay/live/stream`)

        this.eventSource.onmessage = (e) => {
          try {
            const state = JSON.parse(e.data)
            if (!state.error) this.applyState(state)
          } catch { /* ignore parse errors */ }
        }

        this.eventSource.onerror = () => {
          // SSE failed — fall back to polling
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

      // Update session name from first driver's team if possible
      if (state.drivers?.length) {
        this.sessionName = `Formula 1 – Session ${state.session_key}`
      }

      // Track race control history
      if (state.race_control) {
        const rc = state.race_control
        const text = rc.message || rc.flag || ''
        if (text && (this.rcHistory.length === 0 || this.rcHistory[0].text !== text)) {
          this.rcHistory.unshift({
            text,
            flag: rc.flag || '',
            time: new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
          })
          // Keep only last 10
          if (this.rcHistory.length > 10) this.rcHistory.pop()
        }
      }

      // Last updated timestamp
      this.lastUpdated = new Date().toLocaleTimeString('en-GB', {
        hour: '2-digit', minute: '2-digit', second: '2-digit'
      })
    },

    async retryConnection() {
      this.disconnect()
      await this.connect()
    },

    // ── Driver selection ──────────────────────────────────────────────────────
    selectDriver(code) {
      if (this.selectedDriver === code) {
        this.selectedDriver   = null
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
        // Use the existing predictions endpoint
        // We use race_id = 0 as a placeholder for live races (scoring comes in a later feature)
        await api.submitPrediction({
          raceId:     0,
          driver:     this.selectedDriver,
          action:     this.prediction.action,
          lap:        0,   // live — lap TBD
          confidence: this.prediction.confidence
        })
        this.lastPrediction = {
          driver: this.selectedDriver,
          action: this.prediction.action
        }
        this.prediction.action = ''
      } catch (e) {
        console.error('Prediction failed:', e)
      } finally {
        this.submitting = false
      }
    },

    // ── Helpers ───────────────────────────────────────────────────────────────
    teamColor(team)  { return TEAM_COLORS[team] || '#888' },
    shortTeam(team)  { return SHORT_TEAM[team]  || team?.slice(0, 3).toUpperCase() || '???' },

    tyreEmoji(compound) {
      return { SOFT:'🔴', MEDIUM:'🟡', HARD:'⚪', INTERMEDIATE:'🟢', WET:'🔵' }[compound] || '⚫'
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
  max-width: 480px;
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
.next-race-links {
  display: flex;
  gap: 1rem;
  justify-content: center;
  margin-top: 2rem;
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
}
.live-dot {
  width: 6px; height: 6px;
  background: #e10600;
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
}

/* Race control banner (center) */
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
  gap: 0;
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
  gap: 0;
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

.tr-pos {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 1.05rem;
  color: #444;
  text-align: center;
}
.tr-pos.p1 { color: #ffd700; }
.tr-pos.p2 { color: #c0c0c0; }
.tr-pos.p3 { color: #cd7f32; }

.tr-driver {
  display: flex;
  flex-direction: column;
  gap: 0.05rem;
  padding-left: 0.3rem;
}
.tr-code {
  font-family: monospace;
  font-size: 0.85rem;
  font-weight: 800;
  color: #ddd;
  letter-spacing: 0.03em;
}
.tr-team {
  font-size: 0.6rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  opacity: 0.8;
}

.tr-gap {
  font-family: monospace;
  font-size: 0.75rem;
  color: #666;
  text-align: right;
  padding-right: 0.25rem;
}
.tr-gap.leader { color: #ffd700; font-weight: 800; font-size: 0.65rem; }

.tr-interval {
  font-family: monospace;
  font-size: 0.72rem;
  color: #444;
  text-align: right;
  padding-right: 0.25rem;
}

.tr-tyre {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  justify-content: center;
}
.tyre-dot {
  width: 10px; height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}
.tyre-dot.soft         { background: #cc2222; }
.tyre-dot.medium       { background: #cccc00; }
.tyre-dot.hard         { background: #cccccc; }
.tyre-dot.intermediate { background: #00aa44; }
.tyre-dot.wet          { background: #2255cc; }
.tyre-dot.unknown      { background: #444; }
.tyre-age {
  font-family: monospace;
  font-size: 0.68rem;
  color: #444;
}

/* ════════════════════════════════════════════════════
   TRACK AREA (center)
════════════════════════════════════════════════════ */
.track-area {
  position: relative;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

/* Race control history — floats over bottom of canvas */
.rc-log {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 0.5rem 0.75rem;
  background: linear-gradient(transparent, rgba(8,8,8,0.9));
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  pointer-events: none;
}
.rc-log-item {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  font-size: 0.72rem;
  padding: 0.25rem 0.5rem;
  border-radius: 2px;
  backdrop-filter: blur(4px);
}
.rc-log-time { color: #444; font-family: monospace; flex-shrink: 0; }
.rc-log-text { color: #666; }
.rc-log-red    .rc-log-text { color: #ff7777; }
.rc-log-yellow .rc-log-text { color: #ffee77; }
.rc-log-safety .rc-log-text { color: #ffaa44; }
.rc-log-green  .rc-log-text { color: #77ff99; }

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

/* Selected driver card */
.selected-card {
  padding: 1rem 0.9rem;
  border-bottom: 1px solid #111;
}
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

.sc-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.2rem;
}
.sc-code {
  font-family: monospace;
  font-size: 1.3rem;
  font-weight: 900;
  color: #fff;
  letter-spacing: 0.05em;
}
.sc-pos {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 1.2rem;
  color: #555;
  letter-spacing: 0.05em;
}
.sc-pos.p1 { color: #ffd700; }
.sc-pos.p2 { color: #c0c0c0; }
.sc-pos.p3 { color: #cd7f32; }
.sc-team {
  font-size: 0.72rem;
  font-weight: 600;
  margin-bottom: 0.9rem;
  letter-spacing: 0.04em;
}

.sc-stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.65rem 0.5rem;
}
.sc-stat {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}
.sc-label {
  font-size: 0.6rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #3a3a3a;
}
.sc-value {
  font-family: monospace;
  font-size: 0.82rem;
  font-weight: 600;
  color: #bbb;
}
.sc-value.leader { color: #ffd700; font-weight: 800; }

.sc-tyre-pill {
  display: inline-block;
  padding: 0.15rem 0.4rem;
  border-radius: 2px;
  font-size: 0.72rem;
  font-weight: 700;
}
.sc-tyre-pill.soft         { background: rgba(200,0,0,0.25);   color: #ff9999; }
.sc-tyre-pill.medium       { background: rgba(200,200,0,0.2);  color: #ffff99; }
.sc-tyre-pill.hard         { background: rgba(200,200,200,0.15); color: #ccc;  }
.sc-tyre-pill.intermediate { background: rgba(0,180,0,0.2);   color: #99ff99;  }
.sc-tyre-pill.wet          { background: rgba(0,80,220,0.2);  color: #99aaff;  }
.sc-tyre-pill.unknown      { background: rgba(80,80,80,0.2);  color: #666;     }

.panel-divider {
  height: 1px;
  background: #111;
  flex-shrink: 0;
}

/* ── Prediction panel ── */
.prediction-panel {
  padding: 0.9rem;
  flex: 1;
}
.panel-heading {
  font-size: 0.62rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: #333;
  margin-bottom: 0.9rem;
}
.pred-hint {
  font-size: 0.78rem;
  color: #2d2d2d;
  text-align: center;
  padding: 1rem 0;
}
.pred-form { display: flex; flex-direction: column; gap: 0.8rem; }

.pred-driver-chip {
  font-size: 0.72rem;
  color: #555;
  background: #0f0f0f;
  border: 1px solid #1a1a1a;
  padding: 0.35rem 0.6rem;
  border-radius: 2px;
}
.pred-driver-chip strong { color: #fff; font-family: monospace; }

.pred-field {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}
.pred-field label {
  font-size: 0.65rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #3a3a3a;
}
.pred-field label strong { color: #888; }

.action-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px;
}
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

.conf-slider {
  width: 100%;
  height: 3px;
  background: #1a1a1a;
  border-radius: 2px;
  outline: none;
  cursor: pointer;
  appearance: none;
}
.conf-slider::-webkit-slider-thumb {
  appearance: none;
  width: 14px; height: 14px;
  background: #e10600;
  border-radius: 50%;
  cursor: pointer;
}

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
.pred-submit:hover:not(:disabled) {
  background: rgba(225, 6, 0, 0.3);
  border-color: #e10600;
}
.pred-submit:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.last-prediction {
  font-size: 0.7rem;
  color: #2a6;
  text-align: center;
  padding: 0.3rem;
}
</style>