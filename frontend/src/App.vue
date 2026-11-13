<template>
  <div class="app" :class="{ 'dock-open': sound.open }">
    <IntroSequence />
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
      Music played via YouTube. Not affiliated with Formula 1.
    </footer>
    <SoundDock />
  </div>
</template>

<script>
import Navbar from '@/components/Navbar.vue'
import ColdStartOverlay from '@/components/ColdStartOverlay.vue'
import IntroSequence from '@/components/IntroSequence.vue'
import SoundDock from '@/components/SoundDock.vue'
import { sound } from '@/services/soundtrack'
export default {
  name: 'App',
  components: { Navbar, ColdStartOverlay, IntroSequence, SoundDock },
  setup() { return { sound } }
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
/* On phones the dock spans the bottom edge: keep the footer readable above it. */
@media (max-width: 480px) {
  .dock-open .site-footer { padding-bottom: 260px; }
}
.fade-enter-active, .fade-leave-active { transition: opacity var(--dur-base) var(--ease); }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>