<template>
  <div class="app">
    <ColdStartOverlay />
    <Navbar />
    <main>
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
    <footer class="site-footer">
      Data: <a href="https://openf1.org" target="_blank" rel="noopener">OpenF1</a>,
      <a href="https://jolpi.ca" target="_blank" rel="noopener">Jolpica</a> and FastF1.
      Not affiliated with Formula 1.
    </footer>
  </div>
</template>

<script>
import Navbar from '@/components/Navbar.vue'
import ColdStartOverlay from '@/components/ColdStartOverlay.vue'
export default {
  name: 'App',
  components: { Navbar, ColdStartOverlay }
}
</script>

<style scoped>
.app { min-height: 100vh; }
main { padding-top: 56px; }
.site-footer {
  padding: 1.25rem 1rem;
  text-align: center;
  font-size: 0.72rem;
  color: var(--text-secondary);
}
.site-footer a { color: inherit; text-decoration: underline; }
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>