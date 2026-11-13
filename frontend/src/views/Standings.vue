<template>
  <div class="standings">

    <div class="page-header">
      <div class="header-inner">
        <div class="header-label">SEASON</div>
        <h1 class="page-title">STANDINGS</h1>
        <p class="page-sub">Top predictors on the grid</p>
      </div>
    </div>

    <div v-if="loading" class="standings-wrap" aria-busy="true" aria-label="Loading standings">
      <div class="skeleton-stack">
        <div class="skeleton" v-for="i in 8" :key="i"></div>
      </div>
    </div>

    <div v-else-if="error || leaders.length === 0" class="standings-wrap">
      <StatePanel
        v-if="error"
        label="Standings unavailable"
        text="The leaderboard could not be loaded."
        action="Retry"
        @action="load"
      />
      <StatePanel
        v-else
        label="No standings yet"
        text="Be the first to make predictions on race day."
        action="Join the grid"
        to="/register"
      />
    </div>

    <div v-else class="standings-wrap">

      <!-- Top 3 podium -->
      <div class="podium" v-if="leaders.length >= 3">
        <div class="podium-card p2">
          <div class="podium-pos">2</div>
          <div class="podium-avatar">{{ leaders[1].username.slice(0,2).toUpperCase() }}</div>
          <div class="podium-name">{{ leaders[1].username }}</div>
          <div class="podium-pts">{{ leaders[1].totalPoints }} <span>PTS</span></div>
          <div class="podium-acc">{{ leaders[1].accuracy }}% acc</div>
        </div>
        <div class="podium-card p1">
          <div class="podium-crown">👑</div>
          <div class="podium-pos">1</div>
          <div class="podium-avatar gold">{{ leaders[0].username.slice(0,2).toUpperCase() }}</div>
          <div class="podium-name">{{ leaders[0].username }}</div>
          <div class="podium-pts">{{ leaders[0].totalPoints }} <span>PTS</span></div>
          <div class="podium-acc">{{ leaders[0].accuracy }}% acc</div>
        </div>
        <div class="podium-card p3">
          <div class="podium-pos">3</div>
          <div class="podium-avatar">{{ leaders[2].username.slice(0,2).toUpperCase() }}</div>
          <div class="podium-name">{{ leaders[2].username }}</div>
          <div class="podium-pts">{{ leaders[2].totalPoints }} <span>PTS</span></div>
          <div class="podium-acc">{{ leaders[2].accuracy }}% acc</div>
        </div>
      </div>

      <!-- Full table -->
      <div class="table-wrap">
        <div class="table-header">
          <span>POS</span>
          <span>DRIVER</span>
          <span>POINTS</span>
          <span>ACCURACY</span>
          <span>PREDICTIONS</span>
        </div>
        <div
          v-for="user in leaders"
          :key="user.rank"
          class="table-row"
          :class="{
            'is-p1': user.rank === 1,
            'is-p2': user.rank === 2,
            'is-p3': user.rank === 3,
            'is-me': currentUser && user.username === currentUser.username
          }"
        >
          <span class="col-pos">
            <span class="pos-num">{{ user.rank }}</span>
          </span>
          <span class="col-driver">
            <span class="driver-avatar">{{ user.username.slice(0,2).toUpperCase() }}</span>
            <span class="driver-name">{{ user.username }}</span>
            <span class="you-tag" v-if="currentUser && user.username === currentUser.username">YOU</span>
          </span>
          <span class="col-pts">{{ user.totalPoints.toLocaleString() }}</span>
          <span class="col-acc">
            <div class="acc-bar">
              <div class="acc-fill" :style="{ width: user.accuracy + '%' }"></div>
            </div>
            <span class="acc-text">{{ user.accuracy }}%</span>
          </span>
          <span class="col-preds">{{ user.predictionsCount }}</span>
        </div>
      </div>

    </div>
  </div>
</template>

<script>
import { useAuthStore } from '@/stores/auth'
import { apiUrl } from '@/services/apiBase'
import StatePanel from '@/components/StatePanel.vue'

export default {
  name: 'Standings',
  components: { StatePanel },
  data() {
    return {
      leaders: [],
      loading: true,
      error:   false
    }
  },
  computed: {
    currentUser() {
      return useAuthStore().user
    }
  },
  mounted() {
    this.load()
  },
  methods: {
    async load() {
      this.loading = true
      this.error   = false
      try {
        const res  = await fetch(apiUrl('/leaderboard'))
        const data = await res.json()
        if (!res.ok || !Array.isArray(data)) throw new Error('Leaderboard request failed')
        this.leaders = data
      } catch (e) {
        console.error(e)
        this.error = true
      } finally {
        this.loading = false
      }
    }
  }
}
</script>

<style scoped>
.standings {
  min-height: 100vh;
  background: var(--bg-primary);
  font-family: 'Work Sans', sans-serif;
}

.page-header {
  border-bottom: 1px solid var(--bg-hover);
  padding: 3rem 5rem 2rem;
  position: relative;
}
.page-header::after {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 3px;
  background: linear-gradient(to bottom, var(--accent), transparent);
}
.header-label {
  font-size: 0.62rem;
  letter-spacing: 0.18em;
  color: var(--accent);
  font-weight: 700;
  margin-bottom: 0.4rem;
}
.page-title {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 4rem;
  letter-spacing: 0.05em;
  color: var(--text-primary);
  margin: 0 0 0.4rem;
}
.page-sub {
  font-size: 0.82rem;
  color: var(--text-muted);
}

/* Standings wrap */
.standings-wrap {
  max-width: 1100px;
  margin: 0 auto;
  padding: 3rem 5rem 6rem;
}
@media (max-width: 768px) {
  .standings-wrap { padding: 1.5rem 1rem 4rem; }
}

/* Podium */
.podium {
  display: flex;
  justify-content: center;
  align-items: flex-end;
  gap: 1rem;
  margin-bottom: 3rem;
}
.podium-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.4rem;
  padding: 1.5rem 1.2rem 1.2rem;
  border: 1px solid var(--border-primary);
  min-width: 160px;
  position: relative;
  transition: border-color 0.2s;
}
.podium-card:hover { border-color: var(--border-secondary); }
.podium-card.p1 {
  border-color: rgba(255,215,0,0.2);
  background: rgba(255,215,0,0.03);
  padding-top: 2rem;
}
.podium-card.p2 { margin-bottom: 20px; }
.podium-card.p3 { margin-bottom: 20px; }

.podium-crown { position: absolute; top: -16px; font-size: 1.4rem; }

.podium-pos {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 0.9rem;
  color: var(--text-muted);
  letter-spacing: 0.1em;
}
.podium-card.p1 .podium-pos { color: #ffd700; }
.podium-card.p2 .podium-pos { color: #c0c0c0; }
.podium-card.p3 .podium-pos { color: #cd7f32; }

.podium-avatar {
  width: 44px; height: 44px;
  background: var(--bg-hover);
  border: 1px solid var(--border-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--text-secondary);
}
.podium-avatar.gold {
  background: rgba(255,215,0,0.1);
  border-color: rgba(255,215,0,0.3);
  color: #ffd700;
}

.podium-name { font-size: 0.85rem; font-weight: 600; color: var(--text-primary); }
.podium-pts {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 1.6rem;
  color: var(--text-primary);
  letter-spacing: 0.05em;
}
.podium-pts span { font-size: 0.8rem; color: var(--text-secondary); letter-spacing: 0.1em; }
.podium-acc { font-size: 0.72rem; color: var(--text-muted); }

/* Table */
.table-wrap { border: 1px solid var(--bg-card); }
.table-header {
  display: grid;
  grid-template-columns: 60px 1fr 120px 180px 120px;
  padding: 0.6rem 1.5rem;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--bg-card);
}
.table-header span {
  font-size: 0.62rem;
  letter-spacing: 0.12em;
  color: var(--text-muted);
  font-weight: 700;
  text-transform: uppercase;
}
.table-row {
  display: grid;
  grid-template-columns: 60px 1fr 120px 180px 120px;
  align-items: center;
  padding: 0.9rem 1.5rem;
  border-bottom: 1px solid var(--bg-secondary);
  transition: background 0.12s;
  position: relative;
}
.table-row::before {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 2px;
}
.table-row.is-p1::before { background: #ffd700; }
.table-row.is-p2::before { background: #c0c0c0; }
.table-row.is-p3::before { background: #cd7f32; }
.table-row.is-me  { background: var(--accent-dim); }
.table-row:hover  { background: var(--bg-secondary); }

.col-pos .pos-num {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 1.2rem;
  color: var(--border-secondary);
}
.is-p1 .pos-num { color: #ffd700; }
.is-p2 .pos-num { color: #c0c0c0; }
.is-p3 .pos-num { color: #cd7f32; }

.col-driver {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.driver-avatar {
  width: 30px; height: 30px;
  background: var(--bg-card);
  border: 1px solid var(--border-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--text-secondary);
  flex-shrink: 0;
}
.is-me .driver-avatar {
  background: var(--accent-dim);
  border-color: rgba(225,6,0,0.3);
  color: var(--accent);
}
.driver-name { font-size: 0.9rem; font-weight: 600; color: var(--text-primary); }
.you-tag {
  font-size: 0.6rem;
  font-weight: 800;
  letter-spacing: 0.1em;
  color: var(--accent);
  background: var(--accent-dim);
  border: 1px solid rgba(225,6,0,0.2);
  padding: 0.1rem 0.35rem;
}

.col-pts {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 1.3rem;
  color: var(--text-primary);
  letter-spacing: 0.03em;
}

.col-acc { display: flex; align-items: center; gap: 0.75rem; }
.acc-bar {
  width: 80px; height: 3px;
  background: var(--border-primary);
  border-radius: 2px;
  overflow: hidden;
}
.acc-fill { height: 100%; background: var(--accent); border-radius: 2px; }
.acc-text { font-size: 0.8rem; color: var(--text-secondary); font-family: monospace; }

.col-preds { font-size: 0.85rem; color: var(--text-muted); font-family: monospace; }
</style>