<template>
  <div class="predict-race">

    <!-- ── Header ── -->
    <div class="page-header">
      <div class="header-left">
        <div class="header-tag">POST-QUALIFYING</div>
        <h1 class="page-title">{{ windowInfo?.race_name || 'Race Predictions' }}</h1>
        <div class="header-meta" v-if="windowInfo">
          {{ year }} · Round {{ round }}
        </div>
      </div>

      <div class="header-right">
        <!-- Pre-quali: countdown to window opening -->
        <div v-if="windowState === 'pre_quali'" class="status-block pending">
          <div class="status-label">PREDICTIONS OPEN IN</div>
          <div class="status-value">{{ formatDuration(secondsUntilOpen) }}</div>
        </div>

        <!-- Window open: countdown to lockout -->
        <div v-else-if="windowState === 'window_open'" class="status-block live">
          <div class="status-label">
            <span class="live-dot"></span>
            LOCKS IN
          </div>
          <div class="status-value">{{ formatDuration(secondsUntilLock) }}</div>
        </div>

        <!-- Locked / finished -->
        <div v-else-if="windowState === 'locked'" class="status-block locked">
          <div class="status-label">STATUS</div>
          <div class="status-value">LOCKED</div>
        </div>
        <div v-else-if="windowState === 'race_finished'" class="status-block finished">
          <div class="status-label">STATUS</div>
          <div class="status-value">RACE OVER</div>
        </div>
      </div>
    </div>

    <!-- ── Loading ── -->
    <div v-if="loading" class="loading-state">
      <div class="loading-pip"></div>
      <p>Loading prediction window…</p>
    </div>

    <!-- ── Pre-quali message ── -->
    <div v-else-if="windowState === 'pre_quali'" class="info-state">
      <div class="info-icon">🏁</div>
      <h2>Predictions open after qualifying</h2>
      <p>Once qualifying ends, you'll be able to predict the top 10 finishing order and each driver's tyre strategy.</p>
      <router-link to="/" class="info-link">← Back to schedule</router-link>
    </div>

    <!-- ── Race finished — show scored breakdown if present ── -->
    <div v-else-if="windowState === 'race_finished'" class="info-state">
      <div class="info-icon">🏆</div>
      <h2>Race is complete</h2>
      <p v-if="myPrediction?.status === 'scored'">
        Your prediction scored
        <strong>{{ myPrediction.total_points }}</strong> points
        ({{ myPrediction.position_points }} position + {{ myPrediction.tyre_points }} tyres).
      </p>
      <p v-else-if="myPrediction">Your prediction is awaiting scoring.</p>
      <p v-else>You didn't submit a prediction for this race.</p>
      <router-link to="/standings" class="info-link">View standings →</router-link>
    </div>

    <!-- ── Locked but no race result yet ── -->
    <div v-else-if="windowState === 'locked'" class="info-state">
      <div class="info-icon">🔒</div>
      <h2>Predictions are locked</h2>
      <p v-if="myPrediction">Your prediction is in. Results will be available after the race.</p>
      <p v-else>The prediction window has closed and you didn't submit one.</p>
      <router-link to="/" class="info-link">← Back to schedule</router-link>
    </div>

    <!-- ── Window open — the actual prediction UI ── -->
    <div v-else-if="windowState === 'window_open'" class="prediction-layout">

      <!-- LEFT: Driver pool -->
      <div class="driver-pool">
        <div class="pool-header">
          <div class="pool-title">DRIVER POOL</div>
          <div class="pool-hint">Drag to slots or click → click slot</div>
        </div>
        <div class="pool-grid">
          <div
            v-for="driver in availableDrivers"
            :key="driver.code"
            class="driver-card"
            :class="{ selected: selectedFromPool === driver.code }"
            :style="{ '--team-color': teamColor(driver.team) }"
            draggable="true"
            @dragstart="onDragStart($event, driver.code, 'pool')"
            @click="onPoolClick(driver.code)"
            tabindex="0"
            @keydown.enter="onPoolClick(driver.code)"
            @keydown.space.prevent="onPoolClick(driver.code)"
          >
            <div class="driver-num">{{ driver.number }}</div>
            <div class="driver-body">
              <div class="driver-code">{{ driver.code }}</div>
              <div class="driver-name">{{ driver.firstName }} {{ driver.lastName }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- RIGHT: Slots + tyre picker -->
      <div class="slots-column">
        <div class="slots-header">
          <div class="slots-title">YOUR TOP 10</div>
          <div class="slots-status">{{ filledSlots }}/10 filled</div>
        </div>

        <div class="slots-list">
          <div
            v-for="(slot, i) in slots"
            :key="i"
            class="slot-row"
            :class="{
              filled: slot,
              targeting: dragOverIndex === i,
              expanded: expandedSlot === i
            }"
            @dragover.prevent="dragOverIndex = i"
            @dragleave="dragOverIndex = null"
            @drop="onDrop($event, i)"
            @click="onSlotClick(i)"
          >
            <div class="slot-pos" :class="positionClass(i)">{{ i + 1 }}</div>

            <div v-if="slot" class="slot-driver" :style="{ '--team-color': teamColor(driverByCode(slot)?.team) }">
              <div class="slot-num">{{ driverByCode(slot)?.number }}</div>
              <div class="slot-info">
                <span class="slot-code">{{ slot }}</span>
                <span class="slot-name">{{ driverByCode(slot)?.lastName }}</span>
              </div>
              <div class="slot-tyres">
                <span
                  v-for="(c, idx) in tyreStrategies[slot] || []"
                  :key="idx"
                  class="tyre-pip"
                  :class="c.toLowerCase()"
                ></span>
                <span v-if="!tyreStrategies[slot]?.length" class="tyres-empty">no strategy</span>
              </div>
              <button class="slot-remove" @click.stop="removeFromSlot(i)" title="Remove">×</button>
            </div>

            <div v-else class="slot-empty">
              Drop driver here, or click a driver then this slot
            </div>

            <!-- Expanded tyre picker -->
            <div v-if="expandedSlot === i && slot" class="tyre-picker" @click.stop>
              <div class="tyre-picker-head">
                Stint strategy for {{ slot }}
                <button class="picker-clear" @click="clearTyres(slot)" v-if="tyreStrategies[slot]?.length">clear</button>
              </div>
              <div class="stint-rows">
                <div
                  v-for="stintIdx in MAX_STINTS"
                  :key="stintIdx"
                  class="stint-row"
                >
                  <div class="stint-label">{{ stintIdx === 1 ? 'Start' : `Stint ${stintIdx}` }}</div>
                  <div class="compound-buttons">
                    <button
                      v-for="c in COMPOUNDS"
                      :key="c"
                      class="compound-btn"
                      :class="[c.toLowerCase(), {
                        active: (tyreStrategies[slot] || [])[stintIdx - 1] === c
                      }]"
                      @click="setStint(slot, stintIdx - 1, c)"
                    >{{ compoundShort(c) }}</button>
                    <button
                      v-if="(tyreStrategies[slot] || [])[stintIdx - 1]"
                      class="compound-btn clear"
                      @click="clearStint(slot, stintIdx - 1)"
                      title="Clear this stint"
                    >×</button>
                  </div>
                </div>
              </div>
              <div class="picker-hint">Click a stint slot to clear it. Strategy is optional but earns points.</div>
            </div>
          </div>
        </div>

        <!-- Submit bar -->
        <div class="submit-bar">
          <div class="submit-meta">
            <div class="submit-row">
              <span>Positions filled</span>
              <strong>{{ filledSlots }}/10</strong>
            </div>
            <div class="submit-row">
              <span>Tyre strategies</span>
              <strong>{{ filledStrategies }}/{{ filledSlots }}</strong>
            </div>
            <div class="submit-row" v-if="existingPrediction">
              <span>Status</span>
              <strong class="updating-tag">UPDATING EXISTING</strong>
            </div>
          </div>
          <button
            class="submit-btn"
            :disabled="filledSlots === 0 || submitting"
            @click="submit"
          >
            {{ submitting ? 'Submitting…' : (existingPrediction ? 'Update Prediction' : 'Lock In Prediction') }}
          </button>
        </div>

        <div v-if="submitMessage" class="submit-message" :class="submitMessageType">
          {{ submitMessage }}
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import api from '@/services/api.js'
import { DRIVERS_2026, teamColor, driverByCode } from '@/data/drivers.js'

const COMPOUNDS  = ['SOFT', 'MEDIUM', 'HARD', 'INTERMEDIATE', 'WET']
const MAX_STINTS = 4

export default {
  name: 'PredictRace',

  data() {
    return {
      year:  parseInt(this.$route.params.year, 10),
      round: parseInt(this.$route.params.round, 10),

      loading:     true,
      windowInfo:  null,
      windowState: null,

      slots:           Array(10).fill(null),    // [code|null] length 10
      tyreStrategies:  {},                       // { code: [compound, ...] }

      selectedFromPool: null,
      dragOverIndex:    null,
      expandedSlot:     null,

      existingPrediction: null,
      myPrediction:       null,

      submitting:         false,
      submitMessage:      '',
      submitMessageType:  'info',

      countdownTimer: null,
      secondsUntilOpen: 0,
      secondsUntilLock: 0,

      COMPOUNDS,
      MAX_STINTS,
    }
  },

  computed: {
    availableDrivers() {
      const placed = new Set(this.slots.filter(Boolean))
      return DRIVERS_2026.filter(d => !placed.has(d.code))
    },
    filledSlots() {
      return this.slots.filter(Boolean).length
    },
    filledStrategies() {
      return this.slots.filter(c => c && (this.tyreStrategies[c]?.length > 0)).length
    },
  },

  async mounted() {
    await this.loadWindowState()
    if (this.windowState === 'window_open' || this.windowState === 'locked' || this.windowState === 'race_finished') {
      await this.loadExistingPrediction()
    }
    this.loading = false
    this.startCountdown()
  },

  beforeUnmount() {
    clearInterval(this.countdownTimer)
  },

  methods: {
    teamColor,
    driverByCode,

    async loadWindowState() {
      try {
        const info = await api.getPredictionWindow(this.year, this.round)
        this.windowInfo  = info
        this.windowState = info.state
        this.secondsUntilOpen = info.seconds_until_open || 0
        this.secondsUntilLock = info.seconds_until_lock || 0
      } catch (e) {
        console.error('Window load failed:', e)
        this.windowState = 'pre_quali'
      }
    },

    async loadExistingPrediction() {
      try {
        const pred = await api.getMyRacePrediction(this.year, this.round)
        if (pred) {
          this.existingPrediction = pred
          this.myPrediction = pred
          // Hydrate slots and tyres
          this.slots = Array(10).fill(null)
          pred.predicted_order.forEach((code, i) => {
            if (i < 10) this.slots[i] = code
          })
          this.tyreStrategies = { ...(pred.tyre_strategies || {}) }
        }
      } catch (e) {
        // 404 is expected when no prediction yet
        if (e.response?.status !== 404) console.error('Load existing failed:', e)
      }
    },

    startCountdown() {
      this.countdownTimer = setInterval(() => {
        if (this.windowState === 'pre_quali' && this.secondsUntilOpen > 0) {
          this.secondsUntilOpen -= 1
          if (this.secondsUntilOpen === 0) this.loadWindowState()
        }
        if (this.windowState === 'window_open' && this.secondsUntilLock > 0) {
          this.secondsUntilLock -= 1
          if (this.secondsUntilLock === 0) this.loadWindowState()
        }
      }, 1000)
    },

    formatDuration(secs) {
      if (secs <= 0) return '—'
      const d = Math.floor(secs / 86400)
      const h = Math.floor((secs % 86400) / 3600)
      const m = Math.floor((secs % 3600) / 60)
      const s = secs % 60
      if (d > 0) return `${d}d ${h}h ${m}m`
      if (h > 0) return `${h}h ${m}m ${s}s`
      return `${m}m ${s}s`
    },

    positionClass(i) {
      if (i === 0) return 'p1'
      if (i === 1) return 'p2'
      if (i === 2) return 'p3'
      return ''
    },

    compoundShort(c) {
      return { SOFT:'S', MEDIUM:'M', HARD:'H', INTERMEDIATE:'INT', WET:'W' }[c] || c
    },

    // ── Drag & drop ────────────────────────────────────────────────────────
    onDragStart(event, code, source) {
      event.dataTransfer.setData('driver-code', code)
      event.dataTransfer.setData('source', source)
      event.dataTransfer.effectAllowed = 'move'
    },

    onDrop(event, slotIndex) {
      event.preventDefault()
      const code = event.dataTransfer.getData('driver-code')
      if (!code) return
      this.placeDriver(code, slotIndex)
      this.dragOverIndex = null
    },

    // ── Click-to-place fallback (a11y + mobile) ───────────────────────────
    onPoolClick(code) {
      this.selectedFromPool = this.selectedFromPool === code ? null : code
    },

    onSlotClick(slotIndex) {
      if (this.selectedFromPool) {
        this.placeDriver(this.selectedFromPool, slotIndex)
        this.selectedFromPool = null
      } else if (this.slots[slotIndex]) {
        // Toggle expand for tyre picker
        this.expandedSlot = this.expandedSlot === slotIndex ? null : slotIndex
      }
    },

    placeDriver(code, slotIndex) {
      // If driver is already in another slot, vacate that slot first
      const existingIdx = this.slots.indexOf(code)
      if (existingIdx !== -1 && existingIdx !== slotIndex) {
        this.slots[existingIdx] = null
      }
      // If slot has a different driver, evict them (their strategy stays)
      this.slots[slotIndex] = code
      this.slots = [...this.slots]   // trigger reactivity
      this.expandedSlot = slotIndex   // auto-open tyre picker
    },

    removeFromSlot(slotIndex) {
      const code = this.slots[slotIndex]
      if (!code) return
      this.slots[slotIndex] = null
      this.slots = [...this.slots]
      // Keep their tyre strategy in case they re-add the driver
      if (this.expandedSlot === slotIndex) this.expandedSlot = null
    },

    // ── Tyre picker ────────────────────────────────────────────────────────
    setStint(code, stintIndex, compound) {
      const current = [...(this.tyreStrategies[code] || [])]
      // Pad with empty if user is setting stint 3 before stint 2
      while (current.length <= stintIndex) current.push(null)
      current[stintIndex] = compound
      this.tyreStrategies = { ...this.tyreStrategies, [code]: current }
    },

    clearStint(code, stintIndex) {
      const current = [...(this.tyreStrategies[code] || [])]
      current[stintIndex] = null
      // Trim trailing nulls
      while (current.length > 0 && current[current.length - 1] == null) current.pop()
      if (current.length === 0) {
        const updated = { ...this.tyreStrategies }
        delete updated[code]
        this.tyreStrategies = updated
      } else {
        this.tyreStrategies = { ...this.tyreStrategies, [code]: current }
      }
    },

    clearTyres(code) {
      const updated = { ...this.tyreStrategies }
      delete updated[code]
      this.tyreStrategies = updated
    },

    // ── Submit ─────────────────────────────────────────────────────────────
    async submit() {
      this.submitting = true
      this.submitMessage = ''

      // Build payload: order is non-null slots only.
      const predicted_order = this.slots.filter(Boolean)

      // Tyre strategies: only include drivers in predicted_order with non-empty strategies.
      // Filter out null stints from inside each strategy.
      const tyre_strategies = {}
      for (const code of predicted_order) {
        const stints = (this.tyreStrategies[code] || []).filter(Boolean)
        if (stints.length > 0) tyre_strategies[code] = stints
      }

      try {
        const result = await api.submitRacePrediction(this.year, this.round, {
          predicted_order,
          tyre_strategies,
        })
        this.existingPrediction = result.prediction
        this.submitMessage      = result.action === 'created'
          ? 'Prediction locked in.'
          : 'Prediction updated.'
        this.submitMessageType  = 'success'
      } catch (e) {
        this.submitMessage     = e.response?.data?.error || 'Submission failed.'
        this.submitMessageType = 'error'
      } finally {
        this.submitting = false
      }
    },
  }
}
</script>

<style scoped>
.predict-race {
  min-height: calc(100vh - 56px);
  background: var(--bg-primary);
  font-family: 'Work Sans', sans-serif;
  color: var(--text-primary);
}

/* ── Header ── */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  padding: 2.5rem 3rem 2rem;
  border-bottom: 1px solid var(--bg-card);
  gap: 2rem;
}
.header-tag {
  font-size: 0.62rem;
  letter-spacing: 0.2em;
  color: var(--accent);
  font-weight: 700;
  margin-bottom: 0.5rem;
  font-family: 'DM Mono', monospace;
}
.page-title {
  font-family: 'Bebas Neue', sans-serif;
  font-size: clamp(2.2rem, 5vw, 3.6rem);
  letter-spacing: 0.03em;
  margin: 0 0 0.4rem;
  line-height: 1;
}
.header-meta {
  font-size: 0.82rem;
  color: var(--text-muted);
  font-family: 'DM Mono', monospace;
}

.status-block {
  text-align: right;
  padding: 0.75rem 1rem;
  border: 1px solid var(--border-primary);
  border-radius: 2px;
  min-width: 180px;
}
.status-block.live { border-color: rgba(225,6,0,0.3); background: var(--accent-dim); }
.status-block.locked { border-color: var(--border-secondary); }
.status-label {
  font-size: 0.6rem;
  letter-spacing: 0.15em;
  color: var(--text-muted);
  font-family: 'DM Mono', monospace;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.4rem;
  margin-bottom: 0.3rem;
}
.live-dot {
  width: 6px; height: 6px;
  background: var(--accent);
  border-radius: 50%;
  animation: blink 1.2s infinite;
}
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.2} }
.status-value {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 1.6rem;
  color: var(--accent);
  letter-spacing: 0.05em;
  line-height: 1;
}
.status-block.locked .status-value,
.status-block.finished .status-value { color: var(--text-secondary); }

/* ── Info states ── */
.loading-state, .info-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  padding: 6rem 2rem;
  color: var(--text-muted);
  text-align: center;
}
.loading-pip {
  width: 10px; height: 10px;
  background: var(--accent);
  border-radius: 50%;
  animation: pulse 1s infinite;
}
@keyframes pulse { 0%,100%{transform:scale(1);opacity:1} 50%{transform:scale(2);opacity:0.4} }
.info-icon { font-size: 3rem; }
.info-state h2 {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 2rem;
  color: var(--text-primary);
  letter-spacing: 0.04em;
  margin: 0;
}
.info-state p { font-size: 0.9rem; color: var(--text-muted); max-width: 480px; line-height: 1.6; }
.info-link {
  margin-top: 1rem;
  color: var(--accent);
  text-decoration: none;
  font-size: 0.85rem;
  font-weight: 600;
  letter-spacing: 0.05em;
}

/* ── Prediction layout ── */
.prediction-layout {
  display: grid;
  grid-template-columns: 1fr 1.2fr;
  gap: 0;
  min-height: calc(100vh - 56px - 140px);
}

/* Driver pool (left) */
.driver-pool {
  padding: 1.5rem 2rem;
  border-right: 1px solid var(--bg-card);
  overflow-y: auto;
}
.pool-header { margin-bottom: 1.25rem; }
.pool-title {
  font-size: 0.62rem;
  letter-spacing: 0.2em;
  color: var(--accent);
  font-weight: 700;
  font-family: 'DM Mono', monospace;
}
.pool-hint {
  font-size: 0.7rem;
  color: var(--text-muted);
  margin-top: 0.3rem;
}
.pool-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 0.5rem;
}
.driver-card {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.6rem 0.75rem;
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 2px;
  cursor: grab;
  transition: all 0.15s;
  position: relative;
  user-select: none;
}
.driver-card:hover    { border-color: var(--team-color); background: var(--bg-hover); }
.driver-card:focus    { outline: 2px solid var(--accent); outline-offset: 2px; }
.driver-card.selected { border-color: var(--accent); background: var(--accent-dim); }
.driver-card:active   { cursor: grabbing; }
.driver-card::before {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 3px;
  background: var(--team-color);
}
.driver-num {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 1.5rem;
  color: var(--team-color);
  letter-spacing: 0.02em;
  line-height: 1;
  min-width: 28px;
  text-align: center;
}
.driver-body { flex: 1; min-width: 0; }
.driver-code {
  font-family: monospace;
  font-size: 0.85rem;
  font-weight: 800;
  color: var(--text-primary);
  letter-spacing: 0.04em;
}
.driver-name {
  font-size: 0.7rem;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ── Slots column (right) ── */
.slots-column {
  display: flex;
  flex-direction: column;
  padding: 1.5rem 2rem;
}
.slots-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 1rem;
}
.slots-title {
  font-size: 0.62rem;
  letter-spacing: 0.2em;
  color: var(--accent);
  font-weight: 700;
  font-family: 'DM Mono', monospace;
}
.slots-status {
  font-size: 0.78rem;
  color: var(--text-muted);
  font-family: 'DM Mono', monospace;
}

.slots-list {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  flex: 1;
}
.slot-row {
  display: grid;
  grid-template-columns: 40px 1fr;
  align-items: center;
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 2px;
  transition: all 0.15s;
  min-height: 48px;
  position: relative;
}
.slot-row.filled    { background: var(--bg-card); cursor: pointer; }
.slot-row.targeting { border-color: var(--accent); background: var(--accent-dim); }
.slot-row.expanded  { border-color: var(--text-secondary); }

.slot-pos {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 1.4rem;
  color: var(--text-muted);
  text-align: center;
  line-height: 1;
  letter-spacing: 0.05em;
}
.slot-pos.p1 { color: #ffd700; }
.slot-pos.p2 { color: #c0c0c0; }
.slot-pos.p3 { color: #cd7f32; }

.slot-driver {
  display: grid;
  grid-template-columns: 36px 1fr auto 28px;
  align-items: center;
  gap: 0.75rem;
  padding: 0.6rem 0.75rem;
  position: relative;
}
.slot-driver::before {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 2px;
  background: var(--team-color);
}
.slot-num {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 1.3rem;
  color: var(--team-color);
  text-align: center;
  line-height: 1;
}
.slot-info { display: flex; flex-direction: column; gap: 0.1rem; min-width: 0; }
.slot-code {
  font-family: monospace;
  font-size: 0.85rem;
  font-weight: 800;
  color: var(--text-primary);
}
.slot-name {
  font-size: 0.7rem;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.slot-tyres {
  display: flex;
  align-items: center;
  gap: 3px;
}
.tyres-empty {
  font-size: 0.62rem;
  color: var(--text-faint);
  font-style: italic;
}
.tyre-pip {
  width: 11px; height: 11px;
  border-radius: 50%;
  border: 1px solid var(--border-primary);
}
.tyre-pip.soft         { background: #cc2222; }
.tyre-pip.medium       { background: #cccc00; }
.tyre-pip.hard         { background: #cccccc; }
.tyre-pip.intermediate { background: #00aa44; }
.tyre-pip.wet          { background: #2255cc; }

.slot-remove {
  background: transparent;
  border: 1px solid var(--border-primary);
  color: var(--text-muted);
  width: 24px; height: 24px;
  border-radius: 2px;
  font-size: 1rem;
  line-height: 1;
  cursor: pointer;
  transition: all 0.12s;
  padding: 0;
}
.slot-remove:hover { border-color: var(--accent); color: var(--accent); }

.slot-empty {
  padding: 0.7rem 0.75rem;
  color: var(--text-faint);
  font-size: 0.78rem;
  font-style: italic;
}

/* Tyre picker */
.tyre-picker {
  grid-column: 1 / -1;
  padding: 0.85rem 1rem 1rem;
  border-top: 1px solid var(--border-primary);
  background: var(--bg-primary);
  cursor: default;
}
.tyre-picker-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.7rem;
  letter-spacing: 0.1em;
  color: var(--text-secondary);
  margin-bottom: 0.6rem;
  font-family: 'DM Mono', monospace;
}
.picker-clear {
  background: transparent;
  border: none;
  color: var(--text-muted);
  font-size: 0.65rem;
  text-decoration: underline;
  cursor: pointer;
}
.picker-clear:hover { color: var(--accent); }

.stint-rows { display: flex; flex-direction: column; gap: 0.35rem; }
.stint-row {
  display: grid;
  grid-template-columns: 60px 1fr;
  align-items: center;
  gap: 0.6rem;
}
.stint-label {
  font-size: 0.65rem;
  color: var(--text-muted);
  font-family: 'DM Mono', monospace;
  letter-spacing: 0.05em;
}
.compound-buttons { display: flex; gap: 0.3rem; flex-wrap: wrap; }
.compound-btn {
  padding: 0.3rem 0.6rem;
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  color: var(--text-muted);
  font-family: monospace;
  font-size: 0.72rem;
  font-weight: 700;
  cursor: pointer;
  border-radius: 2px;
  min-width: 32px;
  transition: all 0.12s;
}
.compound-btn:hover { border-color: var(--text-secondary); color: var(--text-primary); }
.compound-btn.soft.active         { background: rgba(200,0,0,0.3);    color: #ff9999; border-color: #aa0000; }
.compound-btn.medium.active       { background: rgba(200,200,0,0.25); color: #ffff77; border-color: #999900; }
.compound-btn.hard.active         { background: rgba(220,220,220,0.2); color: var(--text-primary); border-color: #aaa; }
.compound-btn.intermediate.active { background: rgba(0,180,60,0.25);  color: #77ff99; border-color: #007733; }
.compound-btn.wet.active          { background: rgba(0,80,220,0.25);  color: #99aaff; border-color: #0055aa; }
.compound-btn.clear {
  background: transparent;
  border-color: var(--border-primary);
  color: var(--text-faint);
  padding: 0.3rem 0.5rem;
  font-size: 0.85rem;
}
.compound-btn.clear:hover { border-color: var(--accent); color: var(--accent); }

.picker-hint {
  margin-top: 0.6rem;
  font-size: 0.65rem;
  color: var(--text-faint);
  font-style: italic;
}

/* Submit bar */
.submit-bar {
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid var(--bg-card);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1.5rem;
}
.submit-meta {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.submit-row {
  display: flex;
  gap: 0.6rem;
  font-size: 0.75rem;
  color: var(--text-muted);
  font-family: 'DM Mono', monospace;
}
.submit-row strong { color: var(--text-primary); font-weight: 600; }
.updating-tag {
  color: var(--accent) !important;
  font-size: 0.65rem;
  letter-spacing: 0.1em;
}

.submit-btn {
  background: var(--accent);
  color: var(--text-inverse);
  border: none;
  padding: 0.85rem 2rem;
  font-family: 'Bebas Neue', sans-serif;
  font-size: 1.05rem;
  letter-spacing: 0.1em;
  cursor: pointer;
  border-radius: 2px;
  transition: background 0.15s, opacity 0.15s;
  min-height: 44px;
}
.submit-btn:hover:not(:disabled) { background: var(--accent-hover); }
.submit-btn:disabled             { opacity: 0.35; cursor: not-allowed; }

.submit-message {
  margin-top: 0.75rem;
  padding: 0.6rem 0.9rem;
  border-radius: 2px;
  font-size: 0.82rem;
  font-family: 'DM Mono', monospace;
}
.submit-message.success { background: rgba(39,174,96,0.1); border: 1px solid rgba(39,174,96,0.25); color: #5fcf85; }
.submit-message.error   { background: var(--accent-dim); border: 1px solid rgba(225,6,0,0.3); color: var(--accent); }

@media (max-width: 900px) {
  .prediction-layout { grid-template-columns: 1fr; }
  .driver-pool { border-right: none; border-bottom: 1px solid var(--bg-card); max-height: 50vh; }
  .page-header { flex-direction: column; align-items: flex-start; padding: 1.5rem; }
  .status-block { width: 100%; text-align: left; }
  .status-label { justify-content: flex-start; }
  .submit-bar { flex-direction: column; align-items: stretch; }
  .submit-btn { width: 100%; }
}
</style>