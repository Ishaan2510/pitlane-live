<template>
  <div class="app-container">
    <nav class="navbar">
      <div class="nav-brand">
        <h1>🏎️ PitLane Live</h1>
        <p class="tagline">Real-Time F1 Strategy Platform</p>
      </div>
      <div class="nav-links">
        <router-link to="/" class="nav-link">Races</router-link>
        <router-link to="/leaderboard" class="nav-link">Leaderboard</router-link>
      </div>
    </nav>
    <main class="main-content"><router-view /></main>
  </div>
</template>

<script>
export default { name: 'App' }
</script>

<style scoped>
.app-container { min-height: 100vh; background: linear-gradient(135deg,#0f0f0f,#1a1a1a); }
.navbar {
  background: rgba(20,20,20,.95); backdrop-filter: blur(10px);
  padding: 1.5rem 3rem; display: flex; justify-content: space-between;
  align-items: center; border-bottom: 2px solid #e10600;
  box-shadow: 0 4px 20px rgba(225,6,0,.2);
}
.nav-brand h1 {
  font-size: 2rem;
  background: linear-gradient(135deg,#e10600,#ff4444);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  margin-bottom: .25rem;
}
.tagline { font-size: .875rem; color: #888; font-style: italic; }
.nav-links { display: flex; gap: 2rem; }
.nav-link {
  color: #fff; text-decoration: none; font-size: 1.1rem;
  padding: .5rem 1rem; border-radius: 8px; transition: all .3s ease;
}
.nav-link:hover { background: rgba(225,6,0,.1); color: #e10600; }
.nav-link.router-link-active { background: #e10600; color: #fff; }
.main-content { padding: 2rem 3rem; max-width: 1400px; margin: 0 auto; }
</style>
