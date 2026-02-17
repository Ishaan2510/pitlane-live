<template>
  <div class="driver-card" :class="{ 'is-selected': selected }" @click="$emit('select', driver)">

    <div class="position-badge" :class="positionClass">P{{ driver.position }}</div>

    <div class="driver-info">
      <h4>{{ driver.driver }}</h4>
      <p class="team" :style="{ color: teamColor }">{{ driver.team }}</p>
    </div>

    <div class="driver-stats">
      <div class="stat">
        <span class="stat-label">Gap</span>
        <span class="stat-value gap" :class="{ leader: driver.gap === 'LEADER' }">
          {{ driver.gap }}
        </span>
      </div>

      <div class="stat">
        <span class="stat-label">Tire</span>
        <span class="stat-value tire-badge" :class="driver.tireCompound.toLowerCase()">
          {{ tireEmoji }} {{ driver.tireCompound }}
        </span>
      </div>

      <div class="stat">
        <span class="stat-label">Tire Age</span>
        <div class="tire-age-bar">
          <div
            class="tire-age-fill"
            :class="tireDegradationClass"
            :style="{ width: tireAgePercent + '%' }"
          ></div>
          <span class="tire-age-text">{{ driver.tireAge }} laps</span>
        </div>
      </div>

      <div class="stat">
        <span class="stat-label">Last Pit</span>
        <span class="stat-value">Lap {{ driver.lastPitLap }}</span>
      </div>
    </div>

    <!-- Pit warning indicator -->
    <div v-if="pitWarning" class="pit-warning">⚠️ Pit Window Open</div>
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
  'Haas':            '#B6BABD',
  'Sauber':          '#52E252',
}

// Typical pit windows by compound (laps)
const PIT_WINDOW = { SOFT: 20, MEDIUM: 30, HARD: 40 }

export default {
  name: 'DriverCard',
  props: {
    driver:   { type: Object, required: true },
    selected: { type: Boolean, default: false }
  },
  emits: ['select'],
  computed: {
    teamColor() {
      return TEAM_COLORS[this.driver.team] || '#888'
    },
    tireEmoji() {
      return { SOFT: '🔴', MEDIUM: '🟡', HARD: '⚪' }[this.driver.tireCompound] || '⚫'
    },
    tireAgePercent() {
      const max = PIT_WINDOW[this.driver.tireCompound] || 30
      return Math.min((this.driver.tireAge / max) * 100, 100)
    },
    tireDegradationClass() {
      const pct = this.tireAgePercent
      if (pct < 50)  return 'fresh'
      if (pct < 75)  return 'used'
      return 'critical'
    },
    pitWarning() {
      return this.tireAgePercent >= 80
    },
    positionClass() {
      if (this.driver.position === 1) return 'p1'
      if (this.driver.position === 2) return 'p2'
      if (this.driver.position === 3) return 'p3'
      return ''
    }
  }
}
</script>

<style scoped>
.driver-card {
  background: rgba(30,30,30,0.85);
  border-radius: 12px;
  padding: 1.25rem 1.5rem;
  display: flex;
  align-items: center;
  gap: 1.5rem;
  border: 2px solid rgba(255,255,255,0.08);
  transition: all 0.25s ease;
  cursor: pointer;
  position: relative;
  overflow: hidden;
}
.driver-card:hover    { border-color: #e10600; transform: translateX(4px); }
.driver-card.is-selected { border-color: #e10600; background: rgba(225,6,0,0.08); }

/* Subtle left accent line */
.driver-card::before {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 4px;
  background: var(--accent, #444);
  border-radius: 4px 0 0 4px;
}

.position-badge {
  width: 48px; height: 48px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.1rem; font-weight: 800; flex-shrink: 0;
  background: rgba(255,255,255,0.1); color: #fff;
}
.position-badge.p1 { background: #ffd700; color: #000; }
.position-badge.p2 { background: #c0c0c0; color: #000; }
.position-badge.p3 { background: #cd7f32; color: #fff; }

.driver-info { min-width: 180px; }
.driver-info h4 { font-size: 1.1rem; color: #fff; margin-bottom: 0.2rem; font-weight: 700; }
.team { font-size: 0.85rem; font-weight: 600; }

.driver-stats { display: flex; gap: 1.75rem; flex-wrap: wrap; align-items: center; }
.stat { display: flex; flex-direction: column; gap: 0.2rem; }
.stat-label { color: #666; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.05em; }
.stat-value { color: #fff; font-weight: 600; font-size: 0.9rem; }
.stat-value.leader { color: #ffd700; font-weight: 800; }

/* Tire badge */
.tire-badge { padding: 0.2rem 0.6rem; border-radius: 4px; font-size: 0.85rem; font-weight: 700; }
.tire-badge.soft   { background: #c00;  color: #fff; }
.tire-badge.medium { background: #cc0;  color: #000; }
.tire-badge.hard   { background: #ddd;  color: #000; }

/* Tire age bar */
.tire-age-bar {
  position: relative;
  width: 100px; height: 20px;
  background: rgba(255,255,255,0.1);
  border-radius: 10px;
  overflow: hidden;
}
.tire-age-fill {
  position: absolute;
  top: 0; left: 0; height: 100%;
  border-radius: 10px;
  transition: width 0.5s ease, background 0.5s ease;
}
.tire-age-fill.fresh    { background: linear-gradient(90deg,#00cc66,#00ff88); }
.tire-age-fill.used     { background: linear-gradient(90deg,#ffaa00,#ffcc44); }
.tire-age-fill.critical { background: linear-gradient(90deg,#cc0000,#ff4444); animation: pulse-bar 1s infinite; }

@keyframes pulse-bar {
  0%,100% { opacity: 1; }
  50%      { opacity: 0.6; }
}

.tire-age-text {
  position: relative; z-index: 1;
  color: #fff; font-size: 0.75rem; font-weight: 700;
  line-height: 20px; padding: 0 0.5rem;
  text-shadow: 0 0 4px rgba(0,0,0,0.8);
}

/* Pit warning */
.pit-warning {
  position: absolute; top: 0.5rem; right: 0.75rem;
  font-size: 0.75rem; color: #ffaa00; font-weight: 700;
  animation: blink 1.2s ease infinite;
}
@keyframes blink {
  0%,100% { opacity: 1; }
  50%      { opacity: 0.3; }
}
</style>
