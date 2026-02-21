<template>
  <div class="app">
    <nav class="nav">
      <router-link to="/" class="nav-logo">PITLANE</router-link>
      <div class="nav-links">
        <router-link to="/" class="nav-link">Races</router-link>
        <router-link to="/replay" class="nav-link">Replay</router-link>
        <router-link to="/leaderboard" class="nav-link">Standings</router-link>
      </div>
    </nav>
    
    <main>
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<script>
export default { name: 'App' }
</script>

<style scoped>
.app {
  min-height: 100vh;
}

.nav {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 3rem;
  background: rgba(10, 10, 10, 0.8);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--color-border);
}

.nav-logo {
  font-family: var(--font-display);
  font-size: 1.3rem;
  letter-spacing: 0.05em;
  color: var(--color-fg);
  text-decoration: none;
  transition: color 0.3s var(--ease);
}

.nav-logo:hover {
  color: var(--color-accent);
}

.nav-links {
  display: flex;
  gap: 3rem;
}

.nav-link {
  color: var(--color-muted);
  text-decoration: none;
  font-size: 0.9rem;
  font-weight: 500;
  transition: color 0.3s var(--ease);
  position: relative;
}

.nav-link::after {
  content: '';
  position: absolute;
  bottom: -4px;
  left: 0;
  width: 0;
  height: 1px;
  background: var(--color-fg);
  transition: width 0.3s var(--ease);
}

.nav-link:hover,
.nav-link.router-link-active {
  color: var(--color-fg);
}

.nav-link.router-link-active::after {
  width: 100%;
}

main {
  padding-top: 65px;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s var(--ease);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
