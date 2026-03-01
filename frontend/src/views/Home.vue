<template>
  <div class="home">

    <!-- ════════════════════════════════════════════
         HERO — Next Race Countdown
    ════════════════════════════════════════════ -->
    <section class="hero" v-if="nextRace">
      <div class="hero-inner">

        <!-- Left: meta -->
        <div class="hero-meta">
          <div class="hero-label">NEXT RACE</div>
          <div class="hero-round">RD {{ nextRace.round }}</div>
        </div>

        <!-- Centre: race name + countdown -->
        <div class="hero-main">
          <h1 class="hero-title">{{ nextRace.name }}</h1>
          <div class="hero-location">
            {{ nextRace.location }}&nbsp;&nbsp;·&nbsp;&nbsp;{{ nextRace.country }}&nbsp;&nbsp;·&nbsp;&nbsp;{{ formatDate(nextRace.date) }}
            <span v-if="nextRace.is_sprint" class="sprint-badge">SPRINT</span>
          </div>

          <!-- Countdown — separators as real elements, no CSS ::after -->
          <div class="countdown" v-if="countdown.total > 0">
            <template v-for="(unit, idx) in countdownUnits" :key="unit.label">
              <div class="cd-unit">
                <div class="cd-digits">
                  <span
                    v-for="(digit, i) in unit.digits"
                    :key="i"
                    class="cd-digit"
                    :class="{ flip: unit.flipping }"
                  >{{ digit }}</span>
                </div>
                <div class="cd-label">{{ unit.label }}</div>
              </div>
              <!-- Colon separator between units (not after last) -->
              <div v-if="idx < countdownUnits.length - 1" class="cd-sep">:</div>
            </template>
          </div>
          <div class="countdown-live" v-else>
            <span class="live-dot-hero"></span> RACE DAY
          </div>
        </div>

        <!-- Right: quick nav -->
        <div class="hero-actions">
          <router-link to="/live" class="hero-btn primary">Watch Live</router-link>
          <router-link to="/replay" class="hero-btn secondary">Replays</router-link>
          <router-link to="/standings" class="hero-btn ghost">Standings</router-link>
        </div>

      </div>

      <!-- Ticker: next few races -->
      <div class="ticker" v-if="upcomingRaces.length > 1">
        <div class="ticker-label">UP NEXT</div>
        <div class="ticker-items">
          <span
            v-for="race in upcomingRaces.slice(1, 5)"
            :key="race.round"
            class="ticker-item"
          >
            RD {{ race.round }} — {{ race.name }} — {{ formatDate(race.date) }}
          </span>
        </div>
      </div>
    </section>

    <!-- Hero skeleton while loading -->
    <section class="hero hero-loading" v-else-if="loading">
      <div class="skeleton-title"></div>
      <div class="skeleton-sub"></div>
      <div class="skeleton-countdown"></div>
    </section>

    <!-- ════════════════════════════════════════════
         CALENDAR
    ════════════════════════════════════════════ -->
    <section class="calendar">
      <div class="cal-header">
        <h2 class="cal-title">{{ selectedYear }} SEASON</h2>
        <div class="year-toggle">
          <button
            v-for="y in availableYears"
            :key="y"
            class="year-btn"
            :class="{ active: selectedYear === y }"
            @click="switchYear(y)"
          >{{ y }}</button>
        </div>
      </div>

      <div v-if="loading" class="cal-loading">
        <div class="cal-skeleton" v-for="i in 12" :key="i"></div>
      </div>

      <div v-else class="cal-list">
        <div
          v-for="race in races"
          :key="race.round"
          class="cal-row"
          :class="{
            completed: race.status === 'completed',
            upcoming:  race.status === 'upcoming',
            live:      race.status === 'live',
            next:      race.is_next,
          }"
          @click="navigateToRace(race)"
        >
          <div class="cr-round">
            <span class="cr-rd">RD</span>
            <span class="cr-num">{{ String(race.round).padStart(2, '0') }}</span>
          </div>

          <div class="cr-status-col">
            <span v-if="race.status === 'live'"            class="status-pip live-pip"></span>
            <span v-else-if="race.status === 'completed'"  class="status-pip done-pip">✓</span>
            <span v-else-if="race.is_next"                 class="status-pip next-pip">▶</span>
            <span v-else                                    class="status-pip"></span>
          </div>

          <div class="cr-info">
            <div class="cr-name">{{ race.name }}</div>
            <div class="cr-loc">{{ race.location }}, {{ race.country }}
              <span v-if="race.is_sprint" class="sprint-tag">S</span>
            </div>
          </div>

          <div class="cr-date">{{ formatDateLong(race.date) }}</div>

          <div class="cr-action">
            <span v-if="race.status === 'live'"            class="cr-cta live-cta">LIVE →</span>
            <span v-else-if="race.status === 'completed'"  class="cr-cta replay-cta">REPLAY →</span>
            <span v-else-if="race.is_next"                 class="cr-cta next-cta">UPCOMING →</span>
            <span v-else                                    class="cr-cta muted-cta">{{ daysUntil(race.date) }}</span>
          </div>
        </div>
      </div>
    </section>

  </div>
</template>

<script>
const CURRENT_YEAR = new Date().getFullYear()

export default {
  name: 'Home',

  data() {
    return {
      races:          [],
      loading:        true,
      selectedYear:   CURRENT_YEAR,
      availableYears: [CURRENT_YEAR - 1, CURRENT_YEAR],
      countdown:      { days: 0, hours: 0, minutes: 0, seconds: 0, total: 0 },
      countdownTimer: null,
      flipStates:     { days: false, hours: false, minutes: false, seconds: false },
      prevCountdown:  { days: -1, hours: -1, minutes: -1, seconds: -1 },
    }
  },

  computed: {
    nextRace() {
      return this.races.find(r => r.is_next) || null
    },
    upcomingRaces() {
      return this.races.filter(r => r.status === 'upcoming' || r.status === 'live')
    },
    countdownUnits() {
      return [
        { label: 'DAYS', digits: String(this.countdown.days).padStart(2, '0').split(''),    flipping: this.flipStates.days },
        { label: 'HRS',  digits: String(this.countdown.hours).padStart(2, '0').split(''),   flipping: this.flipStates.hours },
        { label: 'MIN',  digits: String(this.countdown.minutes).padStart(2, '0').split(''), flipping: this.flipStates.minutes },
        { label: 'SEC',  digits: String(this.countdown.seconds).padStart(2, '0').split(''), flipping: true },
      ]
    }
  },

  async mounted() {
    await this.loadSchedule()
    this.startCountdown()
  },

  beforeUnmount() {
    clearInterval(this.countdownTimer)
  },

  methods: {
    async loadSchedule() {
      this.loading = true
      try {
        const res  = await fetch(`/api/schedule?year=${this.selectedYear}`)
        this.races = await res.json()
      } catch (e) {
        console.error('Failed to load schedule:', e)
        this.races = []
      } finally {
        this.loading = false
      }
    },

    async switchYear(year) {
      if (year === this.selectedYear) return
      this.selectedYear = year
      clearInterval(this.countdownTimer)
      await this.loadSchedule()
      this.startCountdown()
    },

    startCountdown() {
      this.tickCountdown()
      this.countdownTimer = setInterval(this.tickCountdown, 1000)
    },

    tickCountdown() {
      if (!this.nextRace) return
      const raceDate = new Date(this.nextRace.date + 'T14:00:00Z')
      const diff     = raceDate - new Date()

      if (diff <= 0) {
        this.countdown = { days: 0, hours: 0, minutes: 0, seconds: 0, total: 0 }
        return
      }

      const days    = Math.floor(diff / 86400000)
      const hours   = Math.floor((diff % 86400000) / 3600000)
      const minutes = Math.floor((diff % 3600000)  / 60000)
      const seconds = Math.floor((diff % 60000)    / 1000)

      this.flipStates = {
        days:    days    !== this.prevCountdown.days,
        hours:   hours   !== this.prevCountdown.hours,
        minutes: minutes !== this.prevCountdown.minutes,
        seconds: true
      }
      this.prevCountdown = { days, hours, minutes, seconds }
      this.countdown     = { days, hours, minutes, seconds, total: diff }

      setTimeout(() => {
        this.flipStates = { days: false, hours: false, minutes: false, seconds: false }
      }, 400)
    },

    navigateToRace(race) {
      if (race.status === 'live')      this.$router.push('/live')
      else if (race.status === 'completed') this.$router.push('/replay')
    },

    formatDate(dateStr) {
      return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    },
    formatDateLong(dateStr) {
      return new Date(dateStr).toLocaleDateString('en-US', { day: 'numeric', month: 'short' })
    },
    daysUntil(dateStr) {
      const d = Math.ceil((new Date(dateStr) - new Date()) / 86400000)
      if (d <= 0)  return 'TODAY'
      if (d === 1) return 'TOMORROW'
      return `IN ${d}D`
    }
  }
}
</script>

<style scoped>
.home {
  min-height: 100vh;
  background: #080808;
  font-family: 'Work Sans', sans-serif;
}

/* ════════════════════════════════════════════════════
   HERO
════════════════════════════════════════════════════ */
.hero {
  border-bottom: 1px solid #161616;
  position: relative;
  overflow: hidden;
}
.hero::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(225,6,0,0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(225,6,0,0.03) 1px, transparent 1px);
  background-size: 60px 60px;
  pointer-events: none;
}
.hero::after {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 3px;
  background: linear-gradient(to bottom, #e10600, transparent);
}

.hero-inner {
  display: grid;
  grid-template-columns: 120px 1fr 180px;
  gap: 0;
  padding: 4rem 5rem 2.5rem;
  align-items: start;
}

.hero-meta { padding-top: 0.5rem; }
.hero-label {
  font-size: 0.62rem;
  letter-spacing: 0.18em;
  color: #e10600;
  font-weight: 700;
  margin-bottom: 0.4rem;
}
.hero-round {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 3.5rem;
  color: #1e1e1e;
  line-height: 1;
}

.hero-main { padding: 0 3rem; }
.hero-title {
  font-family: 'Bebas Neue', sans-serif;
  font-size: clamp(2.8rem, 5vw, 5rem);
  line-height: 0.95;
  color: #f5f5f5;
  margin-bottom: 0.75rem;
}
.hero-location {
  font-size: 0.8rem;
  color: #444;
  font-weight: 500;
  letter-spacing: 0.04em;
  margin-bottom: 2.5rem;
  display: flex;
  align-items: center;
  gap: 0.3rem;
  flex-wrap: wrap;
}
.sprint-badge {
  background: rgba(255,160,0,0.15);
  border: 1px solid rgba(255,160,0,0.3);
  color: #ffaa00;
  font-size: 0.6rem;
  font-weight: 800;
  padding: 0.15rem 0.45rem;
  letter-spacing: 0.1em;
  border-radius: 2px;
}

/* ── Countdown ── */
.countdown {
  display: flex;
  align-items: flex-end;
  gap: 0;           /* gap managed by cd-unit margin and cd-sep */
}

.cd-unit {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.4rem;
  margin: 0 6px;    /* space around each unit */
}
.cd-unit:first-child { margin-left: 0; }

/* The colon separator — real element, no CSS tricks */
.cd-sep {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 2.4rem;
  color: #2a2a2a;
  line-height: 1;
  padding-bottom: 22px; /* align with digit mid-point above label */
  flex-shrink: 0;
  user-select: none;
}

.cd-digits {
  display: flex;
  gap: 3px;
}

.cd-digit {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 64px;
  background: #0f0f0f;
  border: 1px solid #1a1a1a;
  font-family: 'Bebas Neue', sans-serif;
  font-size: 2.8rem;
  color: #f5f5f5;
  position: relative;
  overflow: hidden;
}
.cd-digit::after {
  content: '';
  position: absolute;
  left: 0; right: 0; top: 50%;
  height: 1px;
  background: rgba(0,0,0,0.5);
}
.cd-digit.flip { animation: flip-digit 0.35s ease; }
@keyframes flip-digit {
  0%   { transform: rotateX(0);      color: #f5f5f5; }
  40%  { transform: rotateX(-90deg); color: #e10600; }
  60%  { transform: rotateX(-90deg); color: #e10600; }
  100% { transform: rotateX(0);      color: #f5f5f5; }
}

.cd-label {
  font-size: 0.58rem;
  letter-spacing: 0.14em;
  color: #333;
  font-weight: 700;
}

.countdown-live {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  font-family: 'Bebas Neue', sans-serif;
  font-size: 2.5rem;
  letter-spacing: 0.08em;
  color: #e10600;
}
.live-dot-hero {
  width: 10px; height: 10px;
  background: #e10600;
  border-radius: 50%;
  animation: pulse-hero 1s ease infinite;
}
@keyframes pulse-hero {
  0%, 100% { transform: scale(1);   opacity: 1; }
  50%       { transform: scale(1.8); opacity: 0.5; }
}

/* Actions */
.hero-actions {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding-top: 0.5rem;
}
.hero-btn {
  display: block;
  padding: 0.6rem 1rem;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-decoration: none;
  text-align: center;
  border-radius: 2px;
  transition: all 0.15s;
  white-space: nowrap;
}
.hero-btn.primary  { background: #e10600; color: #fff; border: 1px solid #e10600; }
.hero-btn.primary:hover  { background: #ff1a0d; transform: translateX(2px); }
.hero-btn.secondary { background: transparent; color: #f5f5f5; border: 1px solid #2a2a2a; }
.hero-btn.secondary:hover { border-color: #f5f5f5; transform: translateX(2px); }
.hero-btn.ghost { background: transparent; color: #444; border: 1px solid #141414; }
.hero-btn.ghost:hover { color: #888; border-color: #333; }

/* Ticker */
.ticker {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  padding: 0.75rem 5rem;
  border-top: 1px solid #111;
  overflow: hidden;
}
.ticker-label {
  font-size: 0.58rem;
  letter-spacing: 0.14em;
  color: #e10600;
  font-weight: 800;
  white-space: nowrap;
  flex-shrink: 0;
}
.ticker-items {
  display: flex;
  gap: 2.5rem;
  overflow: hidden;
}
.ticker-item {
  font-size: 0.72rem;
  color: #2e2e2e;
  font-weight: 600;
  letter-spacing: 0.04em;
  white-space: nowrap;
}

/* Hero skeleton */
.hero-loading { padding: 4rem 5rem; display: flex; flex-direction: column; gap: 1rem; }
.skeleton-title, .skeleton-sub, .skeleton-countdown {
  background: #111; border-radius: 2px;
  animation: shimmer 1.5s ease infinite;
}
.skeleton-title    { height: 72px; width: 55%; }
.skeleton-sub      { height: 16px; width: 30%; }
.skeleton-countdown { height: 80px; width: 42%; }
@keyframes shimmer {
  0%, 100% { opacity: 0.4; }
  50%       { opacity: 0.7; }
}

/* ════════════════════════════════════════════════════
   CALENDAR
════════════════════════════════════════════════════ */
.calendar { max-width: 1400px; margin: 0 auto; padding: 3rem 5rem 6rem; }
.cal-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 2rem;
  border-bottom: 1px solid #111;
  padding-bottom: 1rem;
}
.cal-title { font-family: 'Bebas Neue', sans-serif; font-size: 1.4rem; letter-spacing: 0.1em; color: #222; }
.year-toggle { display: flex; gap: 0.35rem; }
.year-btn {
  padding: 0.3rem 0.85rem;
  background: transparent;
  border: 1px solid #1a1a1a;
  color: #333;
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
  border-radius: 2px;
  transition: all 0.12s;
}
.year-btn:hover  { border-color: #444; color: #888; }
.year-btn.active { background: #f5f5f5; color: #080808; border-color: #f5f5f5; }

.cal-loading { display: flex; flex-direction: column; gap: 1px; }
.cal-skeleton { height: 56px; background: #0e0e0e; animation: shimmer 1.5s ease infinite; }
.cal-skeleton:nth-child(odd) { animation-delay: 0.15s; }

.cal-list { display: flex; flex-direction: column; }
.cal-row {
  display: grid;
  grid-template-columns: 80px 32px 1fr 160px 110px;
  align-items: center;
  padding: 1.1rem 0;
  border-bottom: 1px solid #0e0e0e;
  transition: background 0.12s;
  position: relative;
  cursor: default;
}
.cal-row.completed         { opacity: 0.4; cursor: pointer; }
.cal-row.completed:hover   { opacity: 0.7; background: rgba(255,255,255,0.01); }
.cal-row.upcoming:hover    { background: rgba(255,255,255,0.015); cursor: pointer; }
.cal-row.live              { background: rgba(225,6,0,0.04); cursor: pointer; }
.cal-row.live:hover        { background: rgba(225,6,0,0.07); }
.cal-row.next              { border-top: 1px solid rgba(225,6,0,0.25); padding-top: 1.2rem; }
.cal-row.next .cr-name     { color: #f5f5f5; }
.cal-row.next .cr-num      { color: #e10600; }

.cr-round { display: flex; flex-direction: column; align-items: flex-start; }
.cr-rd  { font-size: 0.52rem; letter-spacing: 0.1em; color: #222; font-weight: 700; }
.cr-num { font-family: 'Bebas Neue', sans-serif; font-size: 1.5rem; color: #2a2a2a; line-height: 1; }

.cr-status-col { display: flex; justify-content: center; }
.status-pip { font-size: 0.65rem; color: #2a2a2a; width: 16px; text-align: center; font-weight: 700; }
.live-pip   { display: block; width: 8px; height: 8px; background: #e10600; border-radius: 50%; animation: pulse-hero 1s ease infinite; margin: auto; }
.done-pip   { color: #2a2a2a; font-size: 0.6rem; }
.next-pip   { color: #e10600; }

.cr-info    { padding: 0 1rem; }
.cr-name    { font-size: 0.95rem; font-weight: 600; color: #888; margin-bottom: 0.15rem; }
.cr-loc     { font-size: 0.72rem; color: #2a2a2a; display: flex; align-items: center; gap: 0.35rem; }
.sprint-tag { background: rgba(255,160,0,0.12); color: #ffaa00; font-size: 0.55rem; font-weight: 800; padding: 0.05rem 0.3rem; border-radius: 2px; }

.cr-date    { font-family: monospace; font-size: 0.8rem; color: #2a2a2a; font-weight: 600; }
.cal-row.next .cr-date { color: #555; }
.cal-row.live .cr-date { color: #888; }

.cr-cta     { font-size: 0.68rem; font-weight: 800; letter-spacing: 0.08em; display: block; text-align: right; }
.live-cta   { color: #e10600; }
.replay-cta { color: #2a2a2a; }
.next-cta   { color: #e10600; opacity: 0.6; }
.muted-cta  { color: #1e1e1e; font-weight: 600; }
.cal-row.next .next-cta  { opacity: 1; }
.cal-row:hover .replay-cta { color: #555; }

/* ════════════════════════════════════════════════════
   MOBILE
════════════════════════════════════════════════════ */
@media (max-width: 768px) {
  .hero-inner {
    grid-template-columns: 1fr;
    padding: 2rem 1.5rem 1.5rem;
    gap: 1.5rem;
  }
  .hero-meta {
    display: flex;
    align-items: center;
    gap: 1rem;
  }
  .hero-round { font-size: 2rem; }
  .hero-main  { padding: 0; }
  .hero-title { font-size: clamp(2.2rem, 10vw, 3.5rem); margin-bottom: 0.5rem; }
  .hero-location { margin-bottom: 1.5rem; font-size: 0.72rem; }

  /* Countdown: smaller digits on mobile */
  .cd-digit {
    width: 36px;
    height: 50px;
    font-size: 2.1rem;
  }
  .cd-sep {
    font-size: 1.8rem;
    padding-bottom: 16px;
  }
  .cd-unit { margin: 0 3px; }

  .hero-actions {
    flex-direction: row;
    flex-wrap: wrap;
    gap: 0.4rem;
  }
  .hero-btn { flex: 1; min-width: 100px; padding: 0.55rem 0.5rem; font-size: 0.7rem; }

  .ticker { padding: 0.6rem 1.5rem; gap: 0.75rem; }
  .ticker-items { gap: 1.5rem; }

  /* Calendar: hide date column on mobile, tighten layout */
  .calendar { padding: 1.5rem 1rem 4rem; }
  .cal-row  { grid-template-columns: 56px 24px 1fr 70px; }
  .cr-date  { display: none; }
  .cr-name  { font-size: 0.82rem; }
  .cr-loc   { font-size: 0.65rem; }
  .cr-cta   { font-size: 0.6rem; }
  .cr-num   { font-size: 1.2rem; }
}

@media (max-width: 480px) {
  .hero-inner { padding: 1.5rem 1rem 1rem; }
  .cd-digit   { width: 30px; height: 42px; font-size: 1.75rem; }
  .cd-sep     { font-size: 1.5rem; padding-bottom: 12px; }
  .countdown  { gap: 0; }
}
</style>