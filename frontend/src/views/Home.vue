<template>
  <div class="home">
    <div class="header">
      <h2>2025 F1 Season</h2>
      <p class="subtitle">Predict pit strategies and compete in real-time</p>
    </div>

    <div v-if="loading" class="loading">
      <div class="spinner"></div><p>Loading races...</p>
    </div>

    <div v-else class="races-grid">
      <div v-for="race in races" :key="race.id"
           class="race-card" :class="race.status" @click="goToRace(race.id)">
        <div class="race-status-badge" :class="race.status">{{ race.status.toUpperCase() }}</div>
        <div class="race-header">
          <h3>{{ race.country }} {{ race.name }}</h3>
          <p class="circuit">{{ race.circuit }}</p>
        </div>
        <div class="race-details">
          <div class="detail-item"><span class="label">Date:</span><span class="value">{{ formatDate(race.date) }}</span></div>
          <div class="detail-item"><span class="label">Laps:</span><span class="value">{{ race.laps }}</span></div>
          <div v-if="race.currentLap" class="detail-item live-indicator">
            <span class="label">Current Lap:</span>
            <span class="value">{{ race.currentLap }} / {{ race.laps }}</span>
          </div>
        </div>
        <button class="action-btn" :class="race.status">{{ getButtonText(race.status) }}</button>
      </div>
    </div>
  </div>
</template>

<script>
import api from '../services/api.js'
export default {
  name: 'Home',
  data() { return { races: [], loading: true } },
  async mounted() {
    try { this.races = await api.getRaces() }
    catch (e) { console.error(e) }
    finally { this.loading = false }
  },
  methods: {
    formatDate(d) { return new Date(d).toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric'}) },
    getButtonText(s) { return s==='live'?'🔴 Watch Live':s==='upcoming'?'View Details':'View Results' },
    goToRace(id) { this.$router.push(`/race/${id}`) }
  }
}
</script>

<style scoped>
.home { max-width: 1200px; margin: 0 auto; }
.header { margin-bottom: 2rem; text-align: center; }
.header h2 { font-size: 2.5rem; color: #fff; margin-bottom: .5rem; }
.subtitle { color: #888; font-size: 1.1rem; }
.loading { text-align: center; padding: 4rem; }
.spinner {
  width: 50px; height: 50px; border: 4px solid rgba(225,6,0,.1);
  border-top-color: #e10600; border-radius: 50%;
  animation: spin 1s linear infinite; margin: 0 auto 1rem;
}
@keyframes spin { to { transform: rotate(360deg); } }
.races-grid { display: grid; grid-template-columns: repeat(auto-fill,minmax(350px,1fr)); gap: 1.5rem; }
.race-card {
  background: rgba(30,30,30,.8); border-radius: 12px; padding: 1.5rem;
  cursor: pointer; transition: all .3s ease; border: 2px solid transparent;
  position: relative; overflow: hidden;
}
.race-card:hover { transform: translateY(-5px); border-color: #e10600; box-shadow: 0 10px 30px rgba(225,6,0,.3); }
.race-card.live { border-color: #0f0; animation: pulse 2s infinite; }
@keyframes pulse {
  0%,100% { box-shadow: 0 0 20px rgba(0,255,0,.3); }
  50%      { box-shadow: 0 0 40px rgba(0,255,0,.6); }
}
.race-status-badge {
  position: absolute; top: 1rem; right: 1rem;
  padding: .25rem .75rem; border-radius: 20px; font-size: .75rem; font-weight: bold;
}
.race-status-badge.live     { background: #0f0; color: #000; }
.race-status-badge.upcoming { background: #ffa500; color: #000; }
.race-status-badge.completed{ background: #666; color: #fff; }
.race-header { margin-bottom: 1rem; }
.race-header h3 { font-size: 1.5rem; color: #fff; margin-bottom: .5rem; }
.circuit { color: #888; font-size: .9rem; }
.race-details { margin: 1.5rem 0; display: flex; flex-direction: column; gap: .5rem; }
.detail-item { display: flex; justify-content: space-between; padding: .5rem; background: rgba(0,0,0,.3); border-radius: 6px; }
.label { color: #888; font-size: .9rem; }
.value { color: #fff; font-weight: 600; }
.live-indicator { background: rgba(0,255,0,.1); border: 1px solid rgba(0,255,0,.3); }
.action-btn { width: 100%; padding: .75rem; border: none; border-radius: 8px; font-size: 1rem; font-weight: 600; cursor: pointer; transition: all .3s ease; }
.action-btn.live      { background: #0f0; color: #000; }
.action-btn.upcoming  { background: #e10600; color: #fff; }
.action-btn.completed { background: #555; color: #fff; }
.action-btn:hover { transform: scale(1.05); filter: brightness(1.2); }
</style>
