<template>
  <div class="telemetry-panel">

    <!-- Empty / no selection -->
    <div v-if="!driver" class="empty-state">
      <div class="empty-icon">👆</div>
      <p>Click a driver on the track<br>or in the leaderboard</p>
    </div>

    <template v-else>
      <!-- Header -->
      <div class="panel-header">
        <div class="driver-badge" :style="{ borderColor: teamColor }">
          <span class="driver-code">{{ driver.driver }}</span>
          <span class="driver-pos">P{{ driver.position }}</span>
        </div>
        <div class="driver-meta">
          <span class="team-name" :style="{ color: teamColor }">{{ driver.team }}</span>
          <span class="gap-label" :class="{ leader: driver.gap === 'LEADER' }">
            {{ driver.gap || 'LEADER' }}
          </span>
        </div>
      </div>

      <!-- Stats 2-col grid -->
      <div class="stats-grid">

        <div class="stat-card" :class="{ unavailable: !hasSpeed }">
          <span class="stat-icon">🏎️</span>
          <span class="stat-label">Avg Speed</span>
          <span class="stat-value" :class="{ muted: !hasSpeed }">
            {{ formatSpeed(driver.avg_speed) }}
          </span>
        </div>

        <div class="stat-card" :class="{ unavailable: !hasSpeed }">
          <span class="stat-icon">⚡</span>
          <span class="stat-label">Top Speed</span>
          <span class="stat-value" :class="{ muted: !hasSpeed }">
            {{ formatSpeed(driver.max_speed) }}
          </span>
        </div>

        <div class="stat-card tire-card" :class="tireClass">
          <span class="stat-icon">{{ tireEmoji }}</span>
          <span class="stat-label">Compound</span>
          <span class="stat-value">{{ driver.compound || '–' }}</span>
        </div>

        <div class="stat-card">
          <span class="stat-icon">📏</span>
          <span class="stat-label">Tire Age</span>
          <span class="stat-value">{{ driver.tire_life != null ? driver.tire_life + ' laps' : '–' }}</span>
        </div>

        <div class="stat-card">
          <span class="stat-icon">⏱️</span>
          <span class="stat-label">Last Lap</span>
          <span class="stat-value mono">{{ formatLapTime(driver.lap_time) }}</span>
        </div>

        <div class="stat-card" :class="{ pitting: driver.pit_in || driver.pit_out }">
          <span class="stat-icon">{{ pitIcon }}</span>
          <span class="stat-label">Pit Status</span>
          <span class="stat-value">{{ pitStatus }}</span>
        </div>

      </div>

      <!-- Speed note when unavailable -->
      <div v-if="!hasSpeed" class="speed-note">
        ℹ️ Speed telemetry unavailable for this lap
      </div>

      <!-- Tire wear -->
      <div class="tire-wear-section">
        <div class="tire-wear-header">
          <span class="tw-label">Tire Condition</span>
          <span class="tw-pct">{{ tireWearPct }}%</span>
        </div>
        <div class="tire-wear-bar">
          <div class="tire-wear-fill" :class="tireWearClass" :style="{ width: tireWearPct + '%' }"></div>
        </div>
      </div>
    </template>

  </div>
</template>

<script>
const TEAM_COLORS = {
  'Red Bull Racing': '#3671C6',
  'Ferrari':         '#E8002D',
  'Mercedes':        '#27F4D2',
  'McLaren':         '#FF8000',
  'Aston Martin':    '#229971',
  'Alpine':          '#FF87BC',
  'Williams':        '#64C4FF',
  'RB':              '#6692FF',
  'Haas F1 Team':    '#B6BABD',
  'Kick Sauber':     '#52E252',
}

const PIT_WINDOW = { SOFT: 20, MEDIUM: 32, HARD: 45 }

export default {
  name: 'TelemetryPanel',
  props: {
    driver: { type: Object, default: null }
  },
  computed: {
    teamColor()  { return TEAM_COLORS[this.driver?.team] || '#888' },
    tireEmoji()  { return { SOFT:'🔴', MEDIUM:'🟡', HARD:'⚪' }[this.driver?.compound] || '⚫' },
    tireClass()  { return this.driver?.compound?.toLowerCase() || '' },
    hasSpeed()   {
      const d = this.driver
      return d && (d.avg_speed != null && !isNaN(d.avg_speed))
    },
    pitIcon()   {
      if (this.driver?.pit_in)  return '🔧'
      if (this.driver?.pit_out) return '✅'
      return '🏁'
    },
    pitStatus() {
      if (this.driver?.pit_in)  return 'In Pits'
      if (this.driver?.pit_out) return 'Out Lap'
      return 'Racing'
    },
    tireWearPct() {
      if (!this.driver) return 0
      const max = PIT_WINDOW[this.driver.compound] || 30
      return Math.min(Math.round(((this.driver.tire_life || 0) / max) * 100), 100)
    },
    tireWearClass() {
      const p = this.tireWearPct
      if (p < 50) return 'fresh'
      if (p < 80) return 'used'
      return 'critical'
    }
  },
  methods: {
    formatSpeed(val) {
      if (val == null || isNaN(val)) return 'N/A'
      return `${Math.round(val)} km/h`
    },
    // FastF1 returns pandas Timedelta strings like "0 days 00:01:32.456000"
    formatLapTime(lapTime) {
      if (!lapTime) return '–'
      // Match "MM:SS.mmm" inside the string
      const match = lapTime.match(/(\d+):(\d+\.\d+)/)
      if (match) {
        const mins = match[1]
        const secs = parseFloat(match[2]).toFixed(3).padStart(6, '0')
        return `${mins}:${secs}`
      }
      return lapTime
    }
  }
}
</script>

<style scoped>
.telemetry-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

/* ── Empty State ── */
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.9rem;
  padding: 2rem 1.5rem;
  color: var(--color-muted);
  text-align: center;
}
.empty-icon { font-size: 2rem; opacity: 0.4; }
.empty-state p { font-size: 0.82rem; line-height: 1.6; }

/* ── Header ── */
.panel-header {
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  gap: 0.9rem;
  flex-shrink: 0;
}
.driver-badge {
  border: 2px solid #888;
  border-radius: 6px;
  padding: 0.25rem 0.55rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 50px;
}
.driver-code { font-family: monospace; font-size: 1rem; font-weight: 800; color: #fff; letter-spacing: 0.04em; }
.driver-pos  { font-size: 0.68rem; color: #aaa; font-weight: 600; }
.driver-meta { display: flex; flex-direction: column; gap: 0.2rem; }
.team-name   { font-size: 0.8rem; font-weight: 600; }
.gap-label   { font-size: 0.82rem; color: #aaa; font-family: monospace; }
.gap-label.leader { color: #ffd700; font-weight: 700; }

/* ── Stats Grid ── */
.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1px;
  background: var(--color-border);
  border-top: 1px solid var(--color-border);
  flex-shrink: 0;
}
.stat-card {
  background: rgba(10,10,10,0.95);
  padding: 0.8rem 0.9rem;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}
.stat-card.pitting    { background: rgba(225,6,0,0.08); }
.stat-card.unavailable { opacity: 0.7; }

.stat-icon  { font-size: 0.95rem; }
.stat-label { font-size: 0.67rem; color: #555; text-transform: uppercase; letter-spacing: 0.06em; }
.stat-value { font-size: 0.9rem; font-weight: 700; color: #fff; }
.stat-value.mono  { font-family: monospace; font-size: 0.82rem; }
.stat-value.muted { color: #555; font-weight: 400; font-size: 0.8rem; }

/* Tire compound tints */
.tire-card.soft   { background: rgba(200,0,0,0.1); }
.tire-card.medium { background: rgba(180,180,0,0.1); }
.tire-card.hard   { background: rgba(200,200,200,0.06); }

/* Speed note */
.speed-note {
  padding: 0.55rem 1rem;
  font-size: 0.72rem;
  color: #555;
  border-top: 1px solid var(--color-border);
  text-align: center;
  flex-shrink: 0;
}

/* ── Tire Wear ── */
.tire-wear-section {
  padding: 0.85rem 1.25rem;
  border-top: 1px solid var(--color-border);
  flex-shrink: 0;
}
.tire-wear-header { display: flex; justify-content: space-between; margin-bottom: 0.45rem; }
.tw-label { font-size: 0.7rem; color: #555; text-transform: uppercase; letter-spacing: 0.06em; }
.tw-pct   { font-size: 0.78rem; font-weight: 700; color: #aaa; }
.tire-wear-bar { height: 7px; background: rgba(255,255,255,0.08); border-radius: 4px; overflow: hidden; }
.tire-wear-fill { height: 100%; border-radius: 4px; transition: width 0.4s ease, background 0.4s ease; }
.tire-wear-fill.fresh    { background: linear-gradient(90deg,#00cc66,#44ff88); }
.tire-wear-fill.used     { background: linear-gradient(90deg,#ffaa00,#ffdd44); }
.tire-wear-fill.critical { background: linear-gradient(90deg,#cc0000,#ff4444); animation: pulse 1s infinite; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.55} }
</style>
