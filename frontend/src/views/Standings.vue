<template>
  <div class="standings">

    <!-- Header -->
    <div class="page-header">
      <div class="header-inner">
        <div class="header-label">SEASON</div>
        <h1 class="page-title">STANDINGS</h1>
        <p class="page-sub">Top predictors on the grid</p>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading-state">
      <div class="loading-pip"></div>
      <p>Loading standings…</p>
    </div>

    <!-- Empty -->
    <div v-else-if="leaders.length === 0" class="empty-state">
      <div class="empty-icon">🏁</div>
      <h2>No standings yet</h2>
      <p>Be the first to make predictions on race day</p>
      <router-link to="/register" class="cta-btn">JOIN THE GRID →</router-link>
    </div>

    <!-- Table -->
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
      return useAuthStore().user
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
  border-bottom: 1px solid #161616;
  padding: 3rem 5rem 2rem;
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
.page-title {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 4rem;
  letter-spacing: 0.05em;
  color: #f5f5f5;
  margin: 0 0 0.4rem;
}
.page-sub {
  font-size: 0.82rem;
  color: #333;
}

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

/* Empty */
.empty-state {
  text-align: center;
  padding: 6rem 2rem;
}
.empty-icon { font-size: 3rem; margin-bottom: 1rem; }
.empty-state h2 {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 2.5rem;
  color: #fff;
  margin-bottom: 0.5rem;
}
.empty-state p { color: #444; margin-bottom: 2rem; }
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

/* Standings wrap */
.standings-wrap {
  max-width: 1100px;
  margin: 0 auto;
  padding: 3rem 5rem 6rem;
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
  border: 1px solid #1a1a1a;
  min-width: 160px;
  position: relative;
  transition: border-color 0.2s;
}
.podium-card:hover { border-color: #333; }
.podium-card.p1 {
  border-color: rgba(255,215,0,0.2);
  background: rgba(255,215,0,0.03);
  padding-top: 2rem;
}
.podium-card.p2 { margin-bottom: 20px; }
.podium-card.p3 { margin-bottom: 20px; }

.podium-crown {
  position: absolute;
  top: -16px;
  font-size: 1.4rem;
}
.podium-pos {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 0.9rem;
  color: #333;
  letter-spacing: 0.1em;
}
.podium-card.p1 .podium-pos { color: #ffd700; }
.podium-card.p2 .podium-pos { color: #c0c0c0; }
.podium-card.p3 .podium-pos { color: #cd7f32; }

.podium-avatar {
  width: 44px; height: 44px;
  background: #1a1a1a;
  border: 1px solid #2a2a2a;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.85rem;
  font-weight: 700;
  color: #888;
}
.podium-avatar.gold {
  background: rgba(255,215,0,0.1);
  border-color: rgba(255,215,0,0.3);
  color: #ffd700;
}

.podium-name {
  font-size: 0.85rem;
  font-weight: 600;
  color: #ddd;
}
.podium-pts {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 1.6rem;
  color: #fff;
  letter-spacing: 0.05em;
}
.podium-pts span {
  font-size: 0.8rem;
  color: #555;
  letter-spacing: 0.1em;
}
.podium-acc { font-size: 0.72rem; color: #444; }

/* Table */
.table-wrap {
  border: 1px solid #111;
}
.table-header {
  display: grid;
  grid-template-columns: 60px 1fr 120px 180px 120px;
  padding: 0.6rem 1.5rem;
  background: #0a0a0a;
  border-bottom: 1px solid #111;
}
.table-header span {
  font-size: 0.62rem;
  letter-spacing: 0.12em;
  color: #333;
  font-weight: 700;
  text-transform: uppercase;
}
.table-row {
  display: grid;
  grid-template-columns: 60px 1fr 120px 180px 120px;
  align-items: center;
  padding: 0.9rem 1.5rem;
  border-bottom: 1px solid #0e0e0e;
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
.table-row.is-me { background: rgba(225,6,0,0.04); }
.table-row:hover { background: rgba(255,255,255,0.02); }

.col-pos .pos-num {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 1.2rem;
  color: #2a2a2a;
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
  background: #111;
  border: 1px solid #1e1e1e;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.7rem;
  font-weight: 700;
  color: #555;
  flex-shrink: 0;
}
.is-me .driver-avatar {
  background: rgba(225,6,0,0.15);
  border-color: rgba(225,6,0,0.3);
  color: #e10600;
}
.driver-name {
  font-size: 0.9rem;
  font-weight: 600;
  color: #ccc;
}
.you-tag {
  font-size: 0.6rem;
  font-weight: 800;
  letter-spacing: 0.1em;
  color: #e10600;
  background: rgba(225,6,0,0.1);
  border: 1px solid rgba(225,6,0,0.2);
  padding: 0.1rem 0.35rem;
}

.col-pts {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 1.3rem;
  color: #fff;
  letter-spacing: 0.03em;
}

.col-acc {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.acc-bar {
  width: 80px; height: 3px;
  background: #1a1a1a;
  border-radius: 2px;
  overflow: hidden;
}
.acc-fill {
  height: 100%;
  background: #e10600;
  border-radius: 2px;
}
.acc-text {
  font-size: 0.8rem;
  color: #555;
  font-family: monospace;
}

.col-preds {
  font-size: 0.85rem;
  color: #333;
  font-family: monospace;
}
</style>