<template>
  <div class="profile">
    <div class="page-header">
      <div class="header-inner">
        <div class="avatar-large">{{ initials }}</div>
        <div class="header-info">
          <div class="header-label">DRIVER PROFILE</div>
          <h1 class="page-title">{{ user.username }}</h1>
          <p class="page-sub">{{ user.email }}</p>
        </div>
      </div>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="loading-pip"></div>
      <p>Loading profile…</p>
    </div>

    <div v-else class="profile-body">
      <div class="stats-row">
        <div class="stat-card">
          <div class="stat-num">{{ user.total_score.toLocaleString() }}</div>
          <div class="stat-label">TOTAL POINTS</div>
        </div>
        <div class="stat-card">
          <div class="stat-num">{{ user.accuracy_rate }}%</div>
          <div class="stat-label">ACCURACY</div>
        </div>
        <div class="stat-card">
          <div class="stat-num">{{ realPredictions.length }}</div>
          <div class="stat-label">PREDICTIONS</div>
        </div>
        <div class="stat-card">
          <div class="stat-num">{{ rank || '—' }}</div>
          <div class="stat-label">GLOBAL RANK</div>
        </div>
      </div>

      <!-- Real race predictions -->
      <div class="section">
        <div class="section-heading">RECENT PREDICTIONS</div>
        <div v-if="realPredictions.length === 0" class="empty-preds">
          <p>No race predictions yet. Make your first call on race day!</p>
          <router-link to="/live" class="cta-btn">GO LIVE →</router-link>
        </div>
        <div v-else class="pred-list">
          <div class="pred-header">
            <span>DRIVER</span><span>ACTION</span><span>CONFIDENCE</span>
            <span>STATUS</span><span>POINTS</span><span>TIME</span>
          </div>
          <div v-for="pred in realPredictions" :key="pred.id" class="pred-row" :class="pred.status">
            <span class="pred-driver">{{ pred.driver }}</span>
            <span class="pred-action">{{ formatAction(pred.action) }}</span>
            <span class="pred-conf">{{ pred.confidence }}%</span>
            <span class="pred-status"><span class="status-badge" :class="pred.status">{{ pred.status }}</span></span>
            <span class="pred-points" :class="{ earned: pred.points > 0 }">{{ pred.points > 0 ? '+' + pred.points : '—' }}</span>
            <span class="pred-time">{{ formatTime(pred.timestamp) }}</span>
          </div>
        </div>
      </div>

      <!-- Simulation predictions -->
      <div class="section" v-if="simPredictions.length > 0">
        <div class="section-heading sim-heading" @click="showSim = !showSim">
          SIMULATION PREDICTIONS
          <span class="sim-count">{{ simPredictions.length }}</span>
          <span class="sim-toggle">{{ showSim ? '▲' : '▼' }}</span>
          <span class="sim-note">practice only — not scored</span>
        </div>
        <div v-if="showSim" class="pred-list sim-list">
          <div class="pred-header">
            <span>DRIVER</span><span>ACTION</span><span>CONFIDENCE</span>
            <span>STATUS</span><span>POINTS</span><span>TIME</span>
          </div>
          <div v-for="pred in simPredictions" :key="pred.id" class="pred-row sim-row">
            <span class="pred-driver">{{ pred.driver }}</span>
            <span class="pred-action">{{ formatAction(pred.action) }}</span>
            <span class="pred-conf">{{ pred.confidence }}%</span>
            <span class="pred-status"><span class="status-badge sim-badge">SIM</span></span>
            <span class="pred-points">—</span>
            <span class="pred-time">{{ formatTime(pred.timestamp) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { useAuthStore } from '@/stores/auth'
export default {
  name: 'Profile',
  data() {
    return { predictions: [], rank: null, loading: true, showSim: false }
  },
  computed: {
    user()    { return useAuthStore().user },
    initials(){ return this.user?.username?.slice(0,2).toUpperCase() || '??' },
    realPredictions() { return this.predictions.filter(p => p.race_id !== null && p.race_id !== undefined) },
    simPredictions()  { return this.predictions.filter(p => p.race_id === null  || p.race_id === undefined) }
  },
  async mounted() {
    await Promise.all([this.loadPredictions(), this.loadRank()])
    this.loading = false
  },
  methods: {
    async loadPredictions() {
      try {
        const token = localStorage.getItem('pitlane_token')
        const res = await fetch('/api/predictions/mine', { headers: { Authorization: `Bearer ${token}` } })
        this.predictions = await res.json()
      } catch(e) { console.error(e) }
    },
    async loadRank() {
      try {
        const res = await fetch('/api/leaderboard')
        const board = await res.json()
        const me = board.find(u => u.username === this.user?.username)
        if (me) this.rank = me.rank
      } catch(e) { console.error(e) }
    },
    formatAction(a) {
      return { pit_soft:'Pit → Soft', pit_medium:'Pit → Medium', pit_hard:'Pit → Hard', stay_out:'Stay Out' }[a] || a
    },
    formatTime(ts) {
      if (!ts) return '—'
      const iso = ts.endsWith('Z') ? ts : ts + 'Z'
      return new Date(iso).toLocaleString('en-IN', {
        timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        day:      'numeric',
        month:    'short',
        hour:     '2-digit',
        minute:   '2-digit',
        hour12:   true
      })
    }
  }
}
</script>

<style scoped>
.profile {
  min-height: 100vh;
  background: var(--bg-primary);
  font-family: 'Work Sans', sans-serif;
}

.page-header {
  border-bottom: 1px solid var(--bg-hover);
  padding: 3rem 5rem 2.5rem;
  position: relative;
}
.page-header::after {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 3px;
  background: linear-gradient(to bottom, var(--accent), transparent);
}
.header-inner { display: flex; align-items: center; gap: 2rem; }

.avatar-large {
  width: 72px; height: 72px;
  background: var(--accent-dim);
  border: 1px solid rgba(225,6,0,0.3);
  color: var(--accent);
  font-size: 1.6rem;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.header-label {
  font-size: 0.62rem;
  letter-spacing: 0.18em;
  color: var(--accent);
  font-weight: 700;
  margin-bottom: 0.3rem;
}
.page-title {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 3rem;
  letter-spacing: 0.05em;
  color: var(--text-primary);
  margin: 0 0 0.2rem;
}
.page-sub { font-size: 0.82rem; color: var(--text-muted); }

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  padding: 6rem;
  color: var(--text-muted);
}
.loading-pip {
  width: 10px; height: 10px;
  background: var(--accent);
  border-radius: 50%;
  animation: pulse 1s ease infinite;
}
@keyframes pulse { 0%,100%{ transform:scale(1); opacity:1; } 50%{ transform:scale(2); opacity:0.4; } }

.profile-body { max-width: 1100px; margin: 0 auto; padding: 3rem 5rem 6rem; }

.stats-row {
  display: grid;
  grid-template-columns: repeat(4,1fr);
  gap: 1px;
  background: var(--bg-card);
  border: 1px solid var(--bg-card);
  margin-bottom: 3rem;
}
.stat-card {
  background: var(--bg-primary);
  padding: 1.75rem 1.5rem;
  text-align: center;
}
.stat-num {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 2.8rem;
  color: var(--text-primary);
  letter-spacing: 0.03em;
  line-height: 1;
  margin-bottom: 0.4rem;
}
.stat-label { font-size: 0.6rem; letter-spacing: 0.14em; color: var(--text-muted); font-weight: 700; }

.section { margin-bottom: 2.5rem; }
.section-heading {
  font-size: 0.62rem;
  letter-spacing: 0.18em;
  color: var(--text-muted);
  font-weight: 700;
  margin-bottom: 1.5rem;
}
.sim-heading { display: flex; align-items: center; gap: 0.6rem; cursor: pointer; user-select: none; }
.sim-heading:hover { color: var(--text-secondary); }
.sim-count {
  background: var(--bg-hover);
  color: var(--text-secondary);
  font-size: 0.58rem;
  padding: 0.1rem 0.4rem;
  border-radius: 2px;
}
.sim-toggle { color: var(--border-secondary); font-size: 0.55rem; }
.sim-note   { color: var(--text-faint); font-size: 0.58rem; letter-spacing: 0.08em; margin-left: auto; font-style: italic; }

.empty-preds {
  text-align: center;
  padding: 4rem 2rem;
  border: 1px solid var(--bg-card);
  color: var(--text-muted);
}
.empty-preds p { margin-bottom: 1.5rem; }
.cta-btn {
  display: inline-block;
  padding: 0.7rem 1.8rem;
  background: var(--accent);
  color: var(--text-inverse);
  text-decoration: none;
  font-size: 0.85rem;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.pred-list { border: 1px solid var(--bg-card); }
.sim-list  { border-color: var(--border-primary); opacity: 0.65; }

.pred-header {
  display: grid;
  grid-template-columns: 100px 160px 110px 110px 80px 1fr;
  padding: 0.6rem 1.5rem;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--bg-card);
}
.pred-header span { font-size: 0.6rem; letter-spacing: 0.12em; color: var(--text-faint); font-weight: 700; }

.pred-row {
  display: grid;
  grid-template-columns: 100px 160px 110px 110px 80px 1fr;
  align-items: center;
  padding: 0.85rem 1.5rem;
  border-bottom: 1px solid var(--bg-secondary);
  transition: background 0.12s;
}
.pred-row:hover { background: var(--bg-secondary); }
.sim-row { opacity: 0.7; }

.pred-driver { font-family: monospace; font-weight: 700; font-size: 0.88rem; color: var(--text-primary); }
.pred-action { font-size: 0.82rem; color: var(--text-secondary); }
.pred-conf   { font-family: monospace; font-size: 0.82rem; color: var(--text-secondary); }
.pred-points { font-family: 'Bebas Neue', sans-serif; font-size: 1.1rem; color: var(--text-faint); letter-spacing: 0.05em; }
.pred-points.earned { color: #27ae60; }
.pred-time   { font-size: 0.75rem; color: var(--text-faint); font-family: monospace; }

.status-badge {
  font-size: 0.6rem;
  font-weight: 800;
  letter-spacing: 0.1em;
  padding: 0.15rem 0.45rem;
  text-transform: uppercase;
}
.status-badge.pending { background: var(--bg-hover);              color: var(--text-secondary); }
.status-badge.correct { background: rgba(39,174,96,0.15);         color: #27ae60; }
.status-badge.wrong   { background: var(--accent-dim);            color: var(--accent); }
.sim-badge            { background: rgba(60,60,180,0.15);         color: #4488cc; }

@media (max-width: 768px) {
  .page-header { padding: 2rem 1.5rem; }
  .profile-body { padding: 1.5rem 1rem 4rem; }
  .stats-row { grid-template-columns: repeat(2,1fr); }
  .pred-header, .pred-row { grid-template-columns: 70px 1fr 70px 80px; }
  .pred-header span:nth-child(3),
  .pred-header span:nth-child(6),
  .pred-conf,
  .pred-time { display: none; }
}
</style>