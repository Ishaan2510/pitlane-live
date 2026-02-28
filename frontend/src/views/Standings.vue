<template>
  <div class="standings">

    <!-- Header -->
    <div class="page-header">
      <div class="header-inner">
        <div class="header-label">SEASON 2026</div>
        <h1 class="header-title">STANDINGS</h1>
        <p class="header-sub">Global prediction leaderboard</p>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading-screen">
      <div class="loading-pip"></div>
      <p>Loading standings…</p>
    </div>

    <!-- Empty -->
    <div v-else-if="leaders.length === 0" class="empty-state">
      <div class="empty-icon">🏁</div>
      <h2>No predictions yet</h2>
      <p>Be the first to make a prediction on race day</p>
      <router-link to="/live" class="btn-red">Go to Live Race →</router-link>
    </div>

    <!-- Table -->
    <div v-else class="table-wrap">
      <div class="table-header">
        <span class="col-rank">RK</span>
        <span class="col-user">DRIVER</span>
        <span class="col-pts">PTS</span>
        <span class="col-acc">ACCURACY</span>
        <span class="col-preds">PREDICTIONS</span>
      </div>

      <div
        v-for="user in leaders"
        :key="user.rank"
        class="table-row"
        :class="{
          'rank-1': user.rank === 1,
          'rank-2': user.rank === 2,
          'rank-3': user.rank === 3,
          'is-me': user.username === currentUser
        }"
      >
        <div class="col-rank">
          <span class="rank-num" :class="`r${user.rank}`">
            {{ user.rank <= 3 ? ['🥇','🥈','🥉'][user.rank-1] : user.rank }}
          </span>
        </div>

        <div class="col-user">
          <div class="user-avatar">{{ user.username.slice(0,2).toUpperCase() }}</div>
          <div class="user-info">
            <span class="user-name">{{ user.username }}</span>
            <span class="you-tag" v-if="user.username === currentUser">YOU</span>
          </div>
        </div>

        <div class="col-pts">
          <span class="pts-value">{{ user.totalPoints.toLocaleString() }}</span>
        </div>

        <div class="col-acc">
          <div class="acc-bar">
            <div class="acc-fill" :style="{ width: user.accuracy + '%' }"></div>
          </div>
          <span class="acc-text">{{ user.accuracy }}%</span>
        </div>

        <div class="col-preds">
          <span class="preds-count">{{ user.predictionsCount }}</span>
        </div>
      </div>
    </div>

  </div>
</template>

<script>
import { useAuthStore } from '@/stores/auth'

export default {
  name: 'Standings',
  data() {
    return {
      leaders: [],
      loading: true
    }
  },
  computed: {
    currentUser() {
      return useAuthStore().user?.username || null
    }
  },
  async mounted() {
    try {
      const res = await fetch('/api/leaderboard')
      this.leaders = await res.json()
    } catch (e) {
      console.error(e)
    } finally {
      this.loading = false
    }
  }
}
</script>

<style scoped>
.standings {
  min-height: 100vh;
  background: #080808;
  font-family: 'Work Sans', sans-serif;
}

.page-header {
  border-bottom: 1px solid #111;
  padding: 4rem 5rem 2.5rem;
  position: relative;
}
.page-header::after {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 3px;
  background: linear-gradient(to bottom, #e10600, transparent);
}
.header-label {
  font-size: 0.62rem;
  letter-spacing: 0.18em;
  color: #e10600;
  font-weight: 700;
  margin-bottom: 0.4rem;
}
.header-title {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 4rem;
  color: #f5f5f5;
  letter-spacing: 0.04em;
  margin: 0 0 0.4rem;
}
.header-sub {
  color: #333;
  font-size: 0.82rem;
}

/* Loading */
.loading-screen {
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

/* Empty */
.empty-state {
  text-align: center;
  padding: 6rem 2rem;
}
.empty-icon { font-size: 3rem; margin-bottom: 1.5rem; }
.empty-state h2 {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 2rem;
  color: #fff;
  margin-bottom: 0.5rem;
}
.empty-state p { color: #444; margin-bottom: 2rem; }
.btn-red {
  background: #e10600;
  color: #fff;
  padding: 0.6rem 1.4rem;
  text-decoration: none;
  font-size: 0.82rem;
  font-weight: 700;
  letter-spacing: 0.06em;
}

/* Table */
.table-wrap {
  max-width: 1000px;
  margin: 2rem auto;
  padding: 0 5rem 6rem;
}

.table-header {
  display: grid;
  grid-template-columns: 60px 1fr 100px 180px 120px;
  padding: 0.5rem 1rem;
  border-bottom: 1px solid #111;
  margin-bottom: 0.25rem;
}
.table-header span {
  font-size: 0.6rem;
  letter-spacing: 0.12em;
  color: #2a2a2a;
  font-weight: 700;
  text-transform: uppercase;
}

.table-row {
  display: grid;
  grid-template-columns: 60px 1fr 100px 180px 120px;
  align-items: center;
  padding: 0.85rem 1rem;
  border-bottom: 1px solid #0e0e0e;
  transition: background 0.12s;
  position: relative;
}
.table-row::before {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 2px;
  background: transparent;
}
.table-row.rank-1::before { background: #ffd700; }
.table-row.rank-2::before { background: #c0c0c0; }
.table-row.rank-3::before { background: #cd7f32; }
.table-row.is-me { background: rgba(225,6,0,0.04); }
.table-row.is-me::before { background: #e10600; }
.table-row:hover { background: rgba(255,255,255,0.02); }

/* Rank */
.rank-num {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 1.2rem;
  color: #2a2a2a;
}
.rank-num.r1 { color: #ffd700; }
.rank-num.r2 { color: #c0c0c0; }
.rank-num.r3 { color: #cd7f32; }

/* User */
.col-user {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.user-avatar {
  width: 30px; height: 30px;
  background: #1a1a1a;
  border: 1px solid #222;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.7rem;
  font-weight: 700;
  color: #555;
  flex-shrink: 0;
}
.table-row.is-me .user-avatar {
  background: rgba(225,6,0,0.15);
  border-color: rgba(225,6,0,0.3);
  color: #e10600;
}
.user-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.user-name {
  font-size: 0.9rem;
  font-weight: 600;
  color: #888;
}
.table-row.rank-1 .user-name,
.table-row.rank-2 .user-name,
.table-row.rank-3 .user-name { color: #ddd; }
.you-tag {
  font-size: 0.58rem;
  background: rgba(225,6,0,0.2);
  color: #e10600;
  border: 1px solid rgba(225,6,0,0.3);
  padding: 0.1rem 0.35rem;
  font-weight: 800;
  letter-spacing: 0.08em;
}

/* Points */
.pts-value {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 1.3rem;
  color: #e10600;
  letter-spacing: 0.03em;
}

/* Accuracy bar */
.col-acc {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}
.acc-bar {
  flex: 1;
  height: 3px;
  background: #1a1a1a;
  border-radius: 2px;
  overflow: hidden;
}
.acc-fill {
  height: 100%;
  background: #e10600;
  border-radius: 2px;
  transition: width 0.5s ease;
}
.acc-text {
  font-size: 0.78rem;
  color: #555;
  font-family: monospace;
  width: 38px;
  text-align: right;
}

/* Predictions count */
.preds-count {
  font-family: monospace;
  font-size: 0.85rem;
  color: #333;
}
</style>