<template>
  <div class="telemetry-panel">
    <div class="section-title">TELEMETRY</div>

    <!-- Empty state -->
    <div v-if="!driver" class="empty-state">
      <div class="empty-icon">🏎</div>
      <p>Click a driver on the track or in the leaderboard</p>
    </div>

    <!-- Driver data -->
    <template v-else>
      <!-- Driver header -->
      <div class="driver-header">
        <div class="driver-name">{{ driver.driver }}</div>
        <div class="driver-team" :style="{ color: teamColor }">{{ driver.team }}</div>
      </div>

      <!-- Stats -->
      <div class="stat-list">

        <div class="stat-row">
          <span class="stat-label">Position</span>
          <span class="stat-value pos">P{{ driver.position }}</span>
        </div>

        <div class="stat-row">
          <span class="stat-label">Gap</span>
          <span class="stat-value" :class="{ leader: driver.gap === 'LEADER' }">
            {{ driver.gap || '—' }}
          </span>
        </div>

        <div class="divider" />

        <div class="stat-row">
          <span class="stat-label">Tyre</span>
          <span class="tyre-pill" :class="(driver.compound || 'unknown').toLowerCase()">
            {{ tireEmoji }} {{ driver.compound || '?' }}
          </span>
        </div>

        <div class="stat-row">
          <span class="stat-label">Tyre Age</span>
          <span class="stat-value">{{ driver.tire_life ?? '—' }} laps</span>
        </div>

        <div class="divider" />

        <div class="stat-row">
          <span class="stat-label">Lap Time</span>
          <span class="stat-value mono">{{ formatLapTime(driver.lap_time) }}</span>
        </div>

        <div class="divider" />

        <!-- Speed section — fetched on demand -->
        <div class="speed-header">
          <span v-if="loading" class="fetching">Fetching speed data…</span>
          <span v-else-if="hasSpeedData" class="fetched">Live telemetry</span>
        </div>

        <div class="stat-row">
          <span class="stat-label">Avg Speed</span>
          <span class="stat-value">
            <span v-if="loading" class="loading-dot">…</span>
            <span v-else>{{ formatSpeed(enriched.avg_speed ?? driver.avg_speed) }}</span>
          </span>
        </div>

        <div class="stat-row">
          <span class="stat-label">Top Speed</span>
          <span class="stat-value">
            <span v-if="loading" class="loading-dot">…</span>
            <span v-else>{{ formatSpeed(enriched.max_speed ?? driver.max_speed) }}</span>
          </span>
        </div>

      </div>
    </template>
  </div>
</template>

<script>
const TEAM_COLORS = {
  'Red Bull Racing': '#3671C6', 'Ferrari': '#E8002D', 'Mercedes': '#27F4D2',
  'McLaren': '#FF8000', 'Aston Martin': '#229971', 'Alpine': '#FF87BC',
  'Williams': '#64C4FF', 'RB': '#6692FF', 'Kick Sauber': '#52E252',
  'Haas F1 Team': '#B6BABD'
}

export default {
  name: 'TelemetryPanel',

  props: {
    driver:   { type: Object,  default: null },
    enriched: { type: Object,  default: () => ({}) },
    loading:  { type: Boolean, default: false }
  },

  computed: {
    teamColor()    { return TEAM_COLORS[this.driver?.team] || '#888' },
    tireEmoji()    { return { SOFT:'🔴', MEDIUM:'🟡', HARD:'⚪', INTERMEDIATE:'🟢', WET:'🔵' }[this.driver?.compound] || '⚫' },
    hasSpeedData() {
      return (
        this.enriched.avg_speed != null ||
        this.driver?.avg_speed  != null
      )
    }
  },

  methods: {
    formatSpeed(v) {
      return v == null ? 'N/A' : `${Math.round(v)} km/h`
    },
    formatLapTime(t) {
      if (!t) return '—'
      // FastF1 returns timedelta strings like "0 days 00:01:32.456000"
      // Try to extract m:ss.mmm
      const match = t.match(/(\d+):(\d{2}\.\d+)/)
      if (match) return `${match[1]}:${parseFloat(match[2]).toFixed(3).padStart(6,'0')}`
      return t.slice(0, 12)
    }
  }
}
</script>

<style scoped>
.telemetry-panel {
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0;
  height: 100%;
}

.section-title {
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: #555;
  margin-bottom: 0.75rem;
  padding: 0 0.1rem;
}

/* ── Empty state ── */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  gap: 0.75rem;
  text-align: center;
  padding: 1rem 0.5rem;
}
.empty-icon { font-size: 1.6rem; }
.empty-state p {
  font-size: 0.78rem;
  color: #444;
  line-height: 1.5;
}

/* ── Driver header ── */
.driver-header {
  padding: 0.6rem 0.25rem 0.75rem;
  border-bottom: 1px solid #1c1c1c;
  margin-bottom: 0.5rem;
}
.driver-name {
  font-family: monospace;
  font-size: 1.05rem;
  font-weight: 800;
  color: #fff;
  letter-spacing: 0.05em;
}
.driver-team {
  font-size: 0.72rem;
  font-weight: 600;
  margin-top: 0.15rem;
}

/* ── Stat rows ── */
.stat-list {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.stat-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.45rem 0.25rem;
  border-bottom: 1px solid rgba(255,255,255,0.03);
}
.stat-label {
  font-size: 0.72rem;
  color: #555;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.stat-value {
  font-size: 0.85rem;
  font-weight: 600;
  color: #ddd;
}
.stat-value.leader { color: #ffd700; font-weight: 800; }
.stat-value.pos    { color: #fff; }
.mono { font-family: monospace; font-size: 0.8rem; }

.divider {
  height: 1px;
  background: #1c1c1c;
  margin: 0.4rem 0;
}

/* ── Tyre pill ── */
.tyre-pill {
  display: inline-block;
  padding: 0.15rem 0.5rem;
  border-radius: 3px;
  font-size: 0.75rem;
  font-weight: 700;
}
.tyre-pill.soft         { background: rgba(200,0,0,0.3);     color: #ff7777; }
.tyre-pill.medium       { background: rgba(200,200,0,0.25);  color: #ffff77; }
.tyre-pill.hard         { background: rgba(200,200,200,0.2); color: #ddd;    }
.tyre-pill.intermediate { background: rgba(0,180,0,0.25);   color: #77ff77; }
.tyre-pill.wet          { background: rgba(0,100,255,0.25); color: #77aaff; }
.tyre-pill.unknown      { background: rgba(100,100,100,0.2); color: #888;   }

/* ── Speed section ── */
.speed-header {
  padding: 0.3rem 0.25rem 0.1rem;
}
.fetching { font-size: 0.68rem; color: #444; font-style: italic; }
.fetched  { font-size: 0.68rem; color: #2a6; }

.loading-dot { color: #555; animation: pulse 1s ease infinite; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.25} }
</style>