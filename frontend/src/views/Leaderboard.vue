<template>
  <div class="leaderboard">
    <div class="header">
      <h2>🏆 Global Leaderboard</h2>
      <p class="subtitle">Top F1 Strategy Predictors</p>
    </div>
    <div v-if="loading" class="loading"><div class="spinner"></div><p>Loading...</p></div>
    <div v-else class="leaderboard-container">

      <!-- Podium -->
      <div class="podium">
        <div class="podium-place second">
          <div class="medal">🥈</div>
          <div class="user-info">
            <h3>{{ leaders[1].username }}</h3>
            <p class="points">{{ leaders[1].totalPoints }} pts</p>
            <p class="accuracy">{{ leaders[1].accuracy }}% accuracy</p>
          </div>
          <div class="rank-badge">2</div>
        </div>
        <div class="podium-place first">
          <div class="medal">🥇</div>
          <div class="user-info">
            <h3>{{ leaders[0].username }}</h3>
            <p class="points">{{ leaders[0].totalPoints }} pts</p>
            <p class="accuracy">{{ leaders[0].accuracy }}% accuracy</p>
          </div>
          <div class="rank-badge champion">1</div>
        </div>
        <div class="podium-place third">
          <div class="medal">🥉</div>
          <div class="user-info">
            <h3>{{ leaders[2].username }}</h3>
            <p class="points">{{ leaders[2].totalPoints }} pts</p>
            <p class="accuracy">{{ leaders[2].accuracy }}% accuracy</p>
          </div>
          <div class="rank-badge">3</div>
        </div>
      </div>

      <!-- Table -->
      <div class="rankings-table">
        <div class="table-header">
          <span>Rank</span><span>User</span><span>Points</span>
          <span>Accuracy</span><span>Predictions</span>
        </div>
        <div v-for="user in leaders" :key="user.rank"
             class="table-row" :class="{ 'top-three': user.rank <= 3 }">
          <span><span class="rank-number">{{ user.rank }}</span></span>
          <span><span class="username">{{ user.username }}</span></span>
          <span><span class="points-value">{{ user.totalPoints.toLocaleString() }}</span></span>
          <span>
            <div class="accuracy-bar">
              <div class="accuracy-fill" :style="{ width: user.accuracy + '%' }"></div>
              <span class="accuracy-text">{{ user.accuracy }}%</span>
            </div>
          </span>
          <span style="color:#888">{{ user.predictionsCount }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import api from '../services/api.js'
export default {
  name: 'Leaderboard',
  data() { return { leaders: [], loading: true } },
  async mounted() {
    try { this.leaders = await api.getLeaderboard() }
    catch(e) { console.error(e) }
    finally { this.loading = false }
  }
}
</script>

<style scoped>
.leaderboard { max-width: 1200px; margin: 0 auto; }
.header { text-align:center;margin-bottom:3rem; }
.header h2 { font-size:2.5rem;color:#fff;margin-bottom:.5rem; }
.subtitle { color:#888;font-size:1.1rem; }
.loading { text-align:center;padding:4rem; }
.spinner { width:50px;height:50px;border:4px solid rgba(225,6,0,.1);border-top-color:#e10600;border-radius:50%;animation:spin 1s linear infinite;margin:0 auto 1rem; }
@keyframes spin { to{transform:rotate(360deg)} }
.podium { display:flex;justify-content:center;align-items:flex-end;gap:1rem;margin-bottom:3rem;padding:2rem; }
.podium-place { background:rgba(30,30,30,.8);border-radius:12px;padding:2rem 1.5rem;text-align:center;min-width:200px;border:2px solid rgba(255,255,255,.1);position:relative;transition:all .3s; }
.podium-place:hover { transform:translateY(-10px);border-color:#e10600; }
.podium-place.first  { order:2;border-color:#ffd700;background:linear-gradient(135deg,rgba(255,215,0,.1),rgba(30,30,30,.8)); }
.podium-place.second { order:1;border-color:#c0c0c0; }
.podium-place.third  { order:3;border-color:#cd7f32; }
.medal { font-size:3rem;margin-bottom:1rem; }
.user-info h3 { font-size:1.3rem;color:#fff;margin-bottom:.5rem; }
.points { font-size:1.5rem;color:#e10600;font-weight:bold;margin:.5rem 0; }
.accuracy { color:#888;font-size:.9rem; }
.rank-badge { position:absolute;top:-15px;right:-15px;background:#e10600;width:40px;height:40px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:1.2rem;font-weight:bold;border:3px solid #000; }
.rank-badge.champion { background:linear-gradient(135deg,#ffd700,#ffed4e);color:#000;font-size:1.5rem; }
.rankings-table { background:rgba(30,30,30,.8);border-radius:12px;overflow:hidden;border:2px solid rgba(255,255,255,.1); }
.table-header { display:grid;grid-template-columns:80px 1fr 150px 180px 120px;gap:1rem;padding:1.5rem 2rem;background:rgba(0,0,0,.5);font-weight:bold;color:#888;text-transform:uppercase;font-size:.85rem;border-bottom:2px solid rgba(255,255,255,.1); }
.table-row { display:grid;grid-template-columns:80px 1fr 150px 180px 120px;gap:1rem;padding:1.5rem 2rem;border-bottom:1px solid rgba(255,255,255,.05);transition:all .3s;align-items:center; }
.table-row:hover { background:rgba(225,6,0,.1); }
.table-row.top-three { background:rgba(255,215,0,.05); }
.rank-number { background:rgba(225,6,0,.2);color:#e10600;width:40px;height:40px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:bold;font-size:1.1rem; }
.username { color:#fff;font-weight:600;font-size:1.1rem; }
.points-value { color:#e10600;font-weight:bold;font-size:1.1rem; }
.accuracy-bar { position:relative;background:rgba(255,255,255,.1);height:30px;border-radius:15px;overflow:hidden; }
.accuracy-fill { position:absolute;top:0;left:0;height:100%;background:linear-gradient(90deg,#e10600,#ff4444);transition:width .5s; }
.accuracy-text { position:relative;z-index:1;color:#fff;font-weight:600;line-height:30px;padding:0 1rem;text-shadow:0 0 4px rgba(0,0,0,.8); }
</style>
