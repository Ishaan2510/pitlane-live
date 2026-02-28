<template>
  <div class="profile">

    <!-- Header -->
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

    <!-- Loading -->
    <div v-if="loading" class="loading-state">
      <div class="loading-pip"></div>
      <p>Loading profile…</p>
    </div>

    <div v-else class="profile-body">

      <!-- Stats row -->
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
          <div class="stat-num">{{ predictions.length }}</div>
          <div class="stat-label">PREDICTIONS</div>
        </div>
        <div class="stat-card">
          <div class="stat-num">{{ rank || '—' }}</div>
          <div class="stat-label">GLOBAL RANK</div>
        </div>
      </div>

      <!-- Recent predictions -->
      <div class="section">
        <div class="section-heading">RECENT PREDICTIONS</div>

        <div v-if="predictions.length === 0" class="empty-preds">
          <p>No predictions yet. Go make some on race day!</p>
          <router-link to="/live" class="cta-btn">GO LIVE →</router-link>
        </div>

        <div v-else class="pred-list">
          <div class="pred-header">
            <span>DRIVER</span>
            <span>ACTION</span>
            <span>CONFIDENCE</span>
            <span>STATUS</span>
            <span>POINTS</span>
            <span>TIME</span>
          </div>
          <div
            v-for="pred in predictions"
            :key="pred.id"
            class="pred-row"
            :class="pred.status"
          >
            <span class="pred-driver">{{ pred.driver }}</span>
            <span class="pred-action">{{ formatAction(pred.action) }}</span>
            <span class="pred-conf">{{ pred.confidence }}%</span>
            <span class="pred-status">
              <span class="status-badge" :class="pred.status">{{ pred.status }}</span>
            </span>
            <span class="pred-points" :class="{ earned: pred.points > 0 }">
              {{ pred.points > 0 ? '+' + pred.points : '—' }}
            </span>
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
    return {
      predictions: [],
      rank: null,
      loading: true
    }
  },
  computed: {
    user() {
      return useAuthStore().user
    },
    initials() {
      return this.user?.username?.slice(0, 2).toUpperCase() || '??'
    }
  },
  async mounted() {
    await Promise.all([
      this.loadPredictions(),
      this.loadRank()
    ])
    this.loading = false
  },
  methods: {
    async loadPredictions() {
      try {
        const token = localStorage.getItem('pitlane_token')
        const res = await fetch('/api/predictions/mine', {
          headers: { Authorization: `Bearer ${token}` }
        })
        this.predictions = await res.json()
      } catch (e) {
        console.error(e)
      }
    },
    async loadRank() {
      try {
        const res = await fetch('/api/leaderboard')
        const board = await res.json()
        const me = board.find(u => u.username === this.user?.username)
        if (me) this.rank = me.rank
      } catch (e) {
        console.error(e)
      }
    },
    formatAction(action) {
      return {
        pit_soft:   'Pit → Soft',
        pit_medium: 'Pit → Medium',
        pit_hard:   'Pit → Hard',
        stay_out:   'Stay Out'
      }[action] || action
    },
    formatTime(ts) {
      if (!ts) return '—'
      return new Date(ts).toLocaleDateString('en-US', {
        month: 'short', day: 'numeric',
        hour: '2-digit', minute: '2-digit'
      })
    }
  }
}
</script>

<style scoped>
.profile {
  min-height: 100vh;
  background: #080808;
  font-family: 'Work Sans', sans-serif;
}

/* Header */
.page-header {
  border-bottom: 1px solid #161616;
  padding: 3rem 5rem 2.5rem;
  position: relative;
}
.page-header::after {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 3px;
  background: linear-gradient(to bottom, #e10600, transparent);
}
.header-inner {
  display: flex;
  align-items: center;
  gap: 2rem;
}
.avatar-large {
  width: 72px; height: 72px;
  background: rgba(225,6,0,0.15);
  border: 1px solid rgba(225,6,0,0.3);
  color: #e10600;
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
  color: #e10600;
  font-weight: 700;
  margin-bottom: 0.3rem;
}
.page-title {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 3rem;
  letter-spacing: 0.05em;
  color: #f5f5f5;
  margin: 0 0 0.2rem;
}
.page-sub { font-size: 0.82rem; color: #333; }

/* Loading */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  padding: 6rem;
  color: #444;
}
.loading-pip {
  width: 10px; height: 10px;
  background: #e10600;
  border-radius: 50%;
  animation: pulse 1s ease infinite;
}
@keyframes pulse {
  0%,100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(2); opacity: 0.4; }
}

/* Body */
.profile-body {
  max-width: 1100px;
  margin: 0 auto;
  padding: 3rem 5rem 6rem;
}

/* Stats row */
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1px;
  background: #111;
  border: 1px solid #111;
  margin-bottom: 3rem;
}
.stat-card {
  background: #080808;
  padding: 1.75rem 1.5rem;
  text-align: center;
}
.stat-num {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 2.8rem;
  color: #fff;
  letter-spacing: 0.03em;
  line-height: 1;
  margin-bottom: 0.4rem;
}
.stat-label {
  font-size: 0.6rem;
  letter-spacing: 0.14em;
  color: #333;
  font-weight: 700;
}

/* Section */
.section-heading {
  font-size: 0.62rem;
  letter-spacing: 0.18em;
  color: #333;
  font-weight: 700;
  margin-bottom: 1.5rem;
}

/* Empty */
.empty-preds {
  text-align: center;
  padding: 4rem 2rem;
  border: 1px solid #111;
  color: #444;
}
.empty-preds p { margin-bottom: 1.5rem; }
.cta-btn {
  display: inline-block;
  padding: 0.7rem 1.8rem;
  background: #e10600;
  color: #fff;
  text-decoration: none;
  font-size: 0.85rem;
  font-weight: 700;
  letter-spacing: 0.08em;
}

/* Predictions table */
.pred-list { border: 1px solid #111; }

.pred-header {
  display: grid;
  grid-template-columns: 100px 160px 110px 110px 80px 1fr;
  padding: 0.6rem 1.5rem;
  background: #0a0a0a;
  border-bottom: 1px solid #111;
}
.pred-header span {
  font-size: 0.6rem;
  letter-spacing: 0.12em;
  color: #2a2a2a;
  font-weight: 700;
  text-transform: uppercase;
}

.pred-row {
  display: grid;
  grid-template-columns: 100px 160px 110px 110px 80px 1fr;
  align-items: center;
  padding: 0.85rem 1.5rem;
  border-bottom: 1px solid #0e0e0e;
  transition: background 0.12s;
}
.pred-row:hover { background: rgba(255,255,255,0.02); }

.pred-driver {
  font-family: monospace;
  font-weight: 700;
  font-size: 0.88rem;
  color: #ccc;
}
.pred-action { font-size: 0.82rem; color: #666; }
.pred-conf {
  font-family: monospace;
  font-size: 0.82rem;
  color: #555;
}
.pred-points {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 1.1rem;
  color: #2a2a2a;
  letter-spacing: 0.05em;
}
.pred-points.earned { color: #27ae60; }
.pred-time {
  font-size: 0.75rem;
  color: #2a2a2a;
  font-family: monospace;
}

/* Status badge */
.status-badge {
  font-size: 0.6rem;
  font-weight: 800;
  letter-spacing: 0.1em;
  padding: 0.15rem 0.45rem;
  text-transform: uppercase;
}
.status-badge.pending  { background: rgba(100,100,100,0.15); color: #555; }
.status-badge.correct  { background: rgba(39,174,96,0.15);  color: #27ae60; }
.status-badge.wrong    { background: rgba(225,6,0,0.12);    color: #e10600; }
</style>