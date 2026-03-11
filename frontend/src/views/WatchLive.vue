<template>
  <div class="watch-live">

    <!-- ── Hero bar ── -->
    <div class="hero">
      <div class="hero-left">
        <!-- Only show RACE IN PROGRESS pill if it's actually race day -->
        <div class="live-pill" v-if="isRaceDay">
          <span class="live-dot"></span>
          RACE IN PROGRESS
        </div>
        <div class="race-info" v-if="nextRace">
          <h1 class="race-name">{{ nextRace.name }}</h1>
          <p class="race-location">{{ nextRace.location }}, {{ nextRace.country }}</p>
        </div>
        <div class="race-info" v-else>
          <h1 class="race-name">Formula 1</h1>
          <p class="race-location">2026 Season</p>
        </div>
      </div>
      <div class="hero-right" v-if="nextRace && !isRaceDay">
        <div class="countdown-label">NEXT RACE IN</div>
        <div class="countdown">{{ countdown }}</div>
      </div>
      <div class="hero-right" v-else-if="isRaceDay">
        <div class="countdown-label">RACE DAY</div>
        <div class="countdown live-red">LIVE</div>
      </div>
    </div>

    <!-- ── Main content ── -->
    <div class="main">

      <div class="section-label">WATCH LIVE ON</div>
      <div class="platforms">

        <a href="https://www.fancode.com/formula1/" target="_blank" class="platform-card fancode">
          <div class="platform-top">
            <div class="platform-name">FanCode</div>
            <div class="platform-tag">INDIA</div>
          </div>
          <div class="platform-desc">Official F1 broadcast partner in India. Live race, qualifying and practice sessions.</div>
          <div class="platform-cta">
            WATCH NOW
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
              <path d="M2 6h8M6 2l4 4-4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
        </a>

        <a href="https://f1tv.formula1.com" target="_blank" class="platform-card f1tv">
          <div class="platform-top">
            <div class="platform-name">F1 TV</div>
            <div class="platform-tag">GLOBAL</div>
          </div>
          <div class="platform-desc">Official F1 streaming service. Multi-camera feeds, onboard cameras, live timing and radio.</div>
          <div class="platform-cta">
            WATCH NOW
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
              <path d="M2 6h8M6 2l4 4-4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
        </a>

      </div>

      <div class="divider"></div>

      <!-- Race weekend schedule -->
      <template v-if="nextRace">
        <div class="section-label">RACE WEEKEND — {{ nextRace.name }}</div>
        <div class="weekend-grid">

          <!-- Sprint weekend -->
          <template v-if="nextRace.is_sprint">
            <div class="session-row" :class="{ highlight: sessions.fp1 === 'live' }">
              <div class="session-name">
                <span v-if="sessions.fp1 === 'live'" class="live-dot small"></span>
                Practice 1
              </div>
              <div class="session-status" :class="sessions.fp1">{{ sessionLabel(sessions.fp1) }}</div>
            </div>
            <div class="session-row" :class="{ highlight: sessions.quali === 'live' }">
              <div class="session-name">
                <span v-if="sessions.quali === 'live'" class="live-dot small"></span>
                Sprint Qualifying
              </div>
              <div class="session-status" :class="sessions.quali">{{ sessionLabel(sessions.quali) }}</div>
            </div>
            <div class="session-row" :class="{ highlight: sessions.sprint === 'live' }">
              <div class="session-name">
                <span v-if="sessions.sprint === 'live'" class="live-dot small"></span>
                Sprint Race
              </div>
              <div class="session-status" :class="sessions.sprint">{{ sessionLabel(sessions.sprint) }}</div>
            </div>
            <div class="session-row" :class="{ highlight: sessions.qualiMain === 'live' }">
              <div class="session-name">
                <span v-if="sessions.qualiMain === 'live'" class="live-dot small"></span>
                Qualifying
              </div>
              <div class="session-status" :class="sessions.qualiMain">{{ sessionLabel(sessions.qualiMain) }}</div>
            </div>
            <div class="session-row" :class="{ highlight: sessions.race === 'live' }">
              <div class="session-name">
                <span v-if="sessions.race === 'live'" class="live-dot small"></span>
                Race
              </div>
              <div class="session-status" :class="sessions.race">{{ sessionLabel(sessions.race) }}</div>
            </div>
          </template>

          <!-- Standard weekend -->
          <template v-else>
            <div class="session-row" :class="{ highlight: sessions.fp1 === 'live' }">
              <div class="session-name">
                <span v-if="sessions.fp1 === 'live'" class="live-dot small"></span>
                Practice 1
              </div>
              <div class="session-status" :class="sessions.fp1">{{ sessionLabel(sessions.fp1) }}</div>
            </div>
            <div class="session-row" :class="{ highlight: sessions.fp2 === 'live' }">
              <div class="session-name">
                <span v-if="sessions.fp2 === 'live'" class="live-dot small"></span>
                Practice 2
              </div>
              <div class="session-status" :class="sessions.fp2">{{ sessionLabel(sessions.fp2) }}</div>
            </div>
            <div class="session-row" :class="{ highlight: sessions.fp3 === 'live' }">
              <div class="session-name">
                <span v-if="sessions.fp3 === 'live'" class="live-dot small"></span>
                Practice 3
              </div>
              <div class="session-status" :class="sessions.fp3">{{ sessionLabel(sessions.fp3) }}</div>
            </div>
            <div class="session-row" :class="{ highlight: sessions.quali === 'live' }">
              <div class="session-name">
                <span v-if="sessions.quali === 'live'" class="live-dot small"></span>
                Qualifying
              </div>
              <div class="session-status" :class="sessions.quali">{{ sessionLabel(sessions.quali) }}</div>
            </div>
            <div class="session-row" :class="{ highlight: sessions.race === 'live' }">
              <div class="session-name">
                <span v-if="sessions.race === 'live'" class="live-dot small"></span>
                Race
              </div>
              <div class="session-status" :class="sessions.race">{{ sessionLabel(sessions.race) }}</div>
            </div>
          </template>

        </div>
      </template>

      <div class="divider"></div>

      <div class="section-label">COMING UP ON PITLANE LIVE</div>
      <div class="coming-up">
        <div class="coming-card">
          <div class="coming-icon">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <circle cx="10" cy="10" r="7" stroke="#e10600" stroke-width="1.5"/>
              <path d="M10 6v4l2.5 2.5" stroke="#e10600" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
          </div>
          <div>
            <div class="coming-title">Race Replay</div>
            <div class="coming-desc">Full race replay with lap-by-lap timing available within 1 hour of the chequered flag.</div>
          </div>
          <router-link to="/replay" class="coming-link">GO →</router-link>
        </div>
        <div class="coming-card">
          <div class="coming-icon">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <rect x="3" y="5" width="14" height="11" rx="1.5" stroke="#e10600" stroke-width="1.5"/>
              <path d="M7 5V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v1" stroke="#e10600" stroke-width="1.5"/>
              <path d="M7 10h6M7 13h4" stroke="#e10600" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
          </div>
          <div>
            <div class="coming-title">Full Season Calendar</div>
            <div class="coming-desc">24 races, sprint weekends marked. Check the full 2026 schedule and results.</div>
          </div>
          <router-link to="/" class="coming-link">GO →</router-link>
        </div>
      </div>

    </div>
  </div>
</template>

<script>
export default {
  name: 'WatchLive',

  data() {
    return {
      nextRace:  null,
      countdown: '—',
      ticker:    null,
    }
  },

  computed: {
    // Days until race day. 0 = today is race day, negative = past
    daysUntilRace() {
      if (!this.nextRace) return null
      const today    = new Date()
      const raceDate = new Date(this.nextRace.date)
      today.setHours(0, 0, 0, 0)
      raceDate.setHours(0, 0, 0, 0)
      return Math.round((raceDate - today) / 86400000)
    },

    isRaceDay() {
      return this.daysUntilRace === 0
    },

    sessions() {
      const d = this.daysUntilRace
      if (d === null) return {}
      return this.nextRace?.is_sprint
        ? this.sprintSessions(d)
        : this.standardSessions(d)
    }
  },

  async mounted() {
    await this.loadRace()
    this.ticker = setInterval(this.tick, 1000)
  },

  beforeUnmount() {
    clearInterval(this.ticker)
  },

  methods: {
    async loadRace() {
      try {
        const res  = await fetch('/api/schedule')
        const data = await res.json()
        // Use is_next flag — do NOT use status === 'live' as that triggers on race day
        this.nextRace = data.find(r => r.is_next) || null
      } catch { /* silent */ }
    },

    tick() {
      if (!this.nextRace) return
      const target = this.nextRace.race_time_utc
        ? new Date(this.nextRace.race_time_utc)
        : new Date(this.nextRace.date + 'T12:00:00Z')
      const diff = target - new Date()
      if (diff <= 0) { this.countdown = 'NOW'; return }
      const h = Math.floor(diff / 3600000)
      const m = Math.floor((diff % 3600000) / 60000)
      const s = Math.floor((diff % 60000) / 1000)
      this.countdown = `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`
    },

    // Standard weekend: FP1+FP2 on Friday (D-2), FP3+Quali on Saturday (D-1), Race on Sunday (D-0)
    standardSessions(d) {
      if (d > 2)   return { fp1: 'upcoming', fp2: 'upcoming', fp3: 'upcoming', quali: 'upcoming', race: 'upcoming' }
      if (d === 2) return { fp1: 'past',     fp2: 'past',     fp3: 'upcoming', quali: 'upcoming', race: 'upcoming' }
      if (d === 1) return { fp1: 'past',     fp2: 'past',     fp3: 'past',     quali: 'past',     race: 'upcoming' }
      if (d === 0) return { fp1: 'past',     fp2: 'past',     fp3: 'past',     quali: 'past',     race: 'live'     }
      return               { fp1: 'past',     fp2: 'past',     fp3: 'past',     quali: 'past',     race: 'past'     }
    },

    // Sprint weekend: FP1+Sprint Quali on Friday (D-2), Sprint Race+Quali on Saturday (D-1), Race on Sunday (D-0)
    sprintSessions(d) {
      if (d > 2)   return { fp1: 'upcoming', quali: 'upcoming', sprint: 'upcoming', qualiMain: 'upcoming', race: 'upcoming' }
      if (d === 2) return { fp1: 'past',     quali: 'past',     sprint: 'upcoming', qualiMain: 'upcoming', race: 'upcoming' }
      if (d === 1) return { fp1: 'past',     quali: 'past',     sprint: 'past',     qualiMain: 'past',     race: 'upcoming' }
      if (d === 0) return { fp1: 'past',     quali: 'past',     sprint: 'past',     qualiMain: 'past',     race: 'live'     }
      return               { fp1: 'past',     quali: 'past',     sprint: 'past',     qualiMain: 'past',     race: 'past'     }
    },

    sessionLabel(status) {
      if (status === 'past')     return 'COMPLETED'
      if (status === 'live')     return 'LIVE NOW'
      if (status === 'upcoming') return 'UPCOMING'
      return '—'
    }
  }
}
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Mono:wght@400;500&family=Work+Sans:wght@400;500;600;700&display=swap');

.watch-live {
  min-height: calc(100vh - 56px);
  background: var(--bg-primary);
  font-family: 'Work Sans', sans-serif;
  color: var(--text-primary);
}

.hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 2.5rem 3rem;
  border-bottom: 1px solid var(--bg-card);
  background: var(--bg-secondary);
  gap: 2rem;
}
.live-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  background: var(--accent-dim);
  border: 1px solid rgba(225,6,0,0.3);
  color: var(--accent);
  font-size: 0.65rem;
  font-weight: 800;
  letter-spacing: 0.14em;
  padding: 0.3rem 0.75rem;
  border-radius: 2px;
  margin-bottom: 1rem;
  font-family: 'DM Mono', monospace;
}
.live-dot {
  width: 6px; height: 6px;
  background: var(--accent);
  border-radius: 50%;
  animation: blink 1.2s ease-in-out infinite;
}
.live-dot.small { width: 5px; height: 5px; }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.2} }

.race-name {
  font-family: 'Bebas Neue', sans-serif;
  font-size: clamp(2rem, 4vw, 3.2rem);
  color: var(--text-primary);
  letter-spacing: 0.03em;
  margin: 0 0 0.3rem;
  line-height: 1;
}
.race-location {
  font-size: 0.82rem;
  color: var(--text-muted);
  font-family: 'DM Mono', monospace;
  letter-spacing: 0.04em;
}
.hero-right { text-align: right; flex-shrink: 0; }
.countdown-label {
  font-size: 0.6rem;
  letter-spacing: 0.18em;
  color: var(--text-muted);
  font-family: 'DM Mono', monospace;
  margin-bottom: 0.4rem;
}
.countdown {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 2.8rem;
  color: var(--accent);
  letter-spacing: 0.08em;
  line-height: 1;
}
.countdown.live-red { animation: blink 1s ease-in-out infinite; }

.main { max-width: 900px; margin: 0 auto; padding: 3rem 2rem; }
.section-label {
  font-size: 0.6rem;
  letter-spacing: 0.2em;
  color: var(--text-muted);
  font-family: 'DM Mono', monospace;
  font-weight: 500;
  margin-bottom: 1.25rem;
}
.divider { height: 1px; background: var(--bg-card); margin: 2.5rem 0; }

.platforms { display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; }
.platform-card {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 1.4rem;
  border: 1px solid var(--border-primary);
  background: var(--bg-secondary);
  text-decoration: none;
  border-radius: 2px;
  transition: all 0.2s;
  position: relative;
  overflow: hidden;
}
.platform-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
}
.platform-card.fancode::before { background: #00c4ff; }
.platform-card.f1tv::before    { background: var(--accent); }
.platform-card:hover { border-color: var(--border-secondary); background: var(--bg-card); transform: translateY(-2px); }
.platform-top { display: flex; align-items: center; justify-content: space-between; }
.platform-name { font-family: 'Bebas Neue', sans-serif; font-size: 1.3rem; color: var(--text-primary); letter-spacing: 0.05em; }
.platform-tag  { font-size: 0.58rem; letter-spacing: 0.12em; color: var(--text-muted); font-family: 'DM Mono', monospace; background: var(--bg-hover); padding: 0.2rem 0.5rem; border: 1px solid var(--border-primary); }
.platform-desc { font-size: 0.78rem; color: var(--text-muted); line-height: 1.65; flex: 1; }
.platform-cta  { display: flex; align-items: center; gap: 0.5rem; font-size: 0.7rem; font-weight: 700; letter-spacing: 0.1em; font-family: 'DM Mono', monospace; transition: gap 0.2s; }
.fancode .platform-cta { color: #00c4ff; }
.f1tv   .platform-cta { color: var(--accent); }
.platform-card:hover .platform-cta { gap: 0.75rem; }

.weekend-grid {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--border-primary);
  border-radius: 2px;
  overflow: hidden;
}
.session-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1.1rem;
  border-bottom: 1px solid var(--border-primary);
  background: var(--bg-secondary);
}
.session-row:last-child { border-bottom: none; }
.session-row.highlight  { background: var(--accent-dim); }
.session-name {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  font-size: 0.82rem;
  color: var(--text-secondary);
  font-family: 'DM Mono', monospace;
}
.session-row.highlight .session-name { color: var(--text-primary); font-weight: 500; }
.session-status {
  font-size: 0.6rem;
  letter-spacing: 0.14em;
  font-family: 'DM Mono', monospace;
  padding: 0.2rem 0.6rem;
  border-radius: 2px;
}
.session-status.past     { color: var(--text-faint);  background: var(--bg-hover); border: 1px solid var(--border-primary); }
.session-status.upcoming { color: var(--text-muted);  background: var(--bg-hover); border: 1px solid var(--border-primary); }
.session-status.live     { color: var(--accent); background: var(--accent-dim); border: 1px solid rgba(225,6,0,0.25); animation: live-pulse 2s ease-in-out infinite; }
@keyframes live-pulse { 0%,100%{opacity:1} 50%{opacity:0.6} }

.coming-up { display: flex; flex-direction: column; gap: 0.75rem; }
.coming-card {
  display: flex;
  align-items: center;
  gap: 1.1rem;
  padding: 1rem 1.25rem;
  border: 1px solid var(--border-primary);
  background: var(--bg-secondary);
  border-radius: 2px;
}
.coming-icon {
  width: 40px; height: 40px;
  background: var(--accent-dim);
  border: 1px solid rgba(225,6,0,0.12);
  border-radius: 2px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.coming-title { font-size: 0.85rem; font-weight: 700; color: var(--text-primary); margin-bottom: 0.2rem; }
.coming-desc  { font-size: 0.75rem; color: var(--text-muted); line-height: 1.5; }
.coming-link {
  margin-left: auto;
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.1em;
  color: var(--accent);
  text-decoration: none;
  font-family: 'DM Mono', monospace;
  padding: 0.4rem 0.9rem;
  border: 1px solid rgba(225,6,0,0.25);
  border-radius: 2px;
  white-space: nowrap;
  transition: all 0.15s;
  flex-shrink: 0;
}
.coming-link:hover { background: var(--accent-dim); border-color: var(--accent); }

@media (max-width: 700px) {
  .hero      { flex-direction: column; align-items: flex-start; padding: 1.5rem; }
  .hero-right { text-align: left; }
  .platforms { grid-template-columns: 1fr; }
  .main      { padding: 2rem 1.25rem; }
}
</style>