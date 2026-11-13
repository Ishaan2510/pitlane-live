<template>
  <nav class="navbar" :class="{ 'menu-open': menuOpen }">
    <router-link to="/" class="nav-logo">PITLANE<span class="logo-dot">.</span></router-link>

    <!-- Inline links on desktop; below 720 px the same block is the dropdown menu -->
    <div id="nav-menu" ref="linksEl" class="nav-links" @click="menuOpen = false">
      <router-link v-for="link in LINKS" :key="link.to" :to="link.to" class="nav-link">{{ link.label }}</router-link>
      <span class="nav-indicator" :style="indicatorStyle" aria-hidden="true"></span>

      <!-- Account links move in here on small screens -->
      <div class="menu-auth">
        <template v-if="auth.isLoggedIn">
          <router-link to="/profile" class="nav-link">PROFILE</router-link>
          <button class="nav-link" type="button" @click="handleLogout">SIGN OUT</button>
        </template>
        <template v-else>
          <router-link to="/login" class="nav-link">SIGN IN</router-link>
          <router-link to="/register" class="nav-link accent">JOIN GRID</router-link>
        </template>
      </div>
    </div>

    <div class="nav-auth">
      <SoundToggle />
      <ThemeToggle />

      <div class="nav-account">
        <!-- Logged in -->
        <template v-if="auth.isLoggedIn">
          <router-link to="/profile" class="user-pill">
            <span class="user-avatar">{{ initials }}</span>
            <span class="user-name">{{ auth.user.username }}</span>
          </router-link>
          <button class="nav-btn-ghost" @click="handleLogout">OUT</button>
        </template>

        <!-- Guest -->
        <template v-else>
          <router-link to="/login"    class="nav-btn-ghost">SIGN IN</router-link>
          <router-link to="/register" class="nav-btn-red">JOIN GRID</router-link>
        </template>
      </div>

      <button
        class="menu-btn"
        type="button"
        aria-controls="nav-menu"
        :aria-expanded="menuOpen"
        :aria-label="menuOpen ? 'Close menu' : 'Open menu'"
        @click="menuOpen = !menuOpen"
      >
        <svg viewBox="0 0 16 16" aria-hidden="true">
          <path class="menu-line top" d="M2 5.5h12" />
          <path class="menu-line bottom" d="M2 10.5h12" />
        </svg>
      </button>
    </div>
  </nav>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import ThemeToggle from './ThemeToggle.vue'
import SoundToggle from './SoundToggle.vue'

const LINKS = [
  { to: '/live',      label: 'WATCH LIVE' },
  { to: '/replay',    label: 'REPLAY' },
  { to: '/standings', label: 'STANDINGS' },
  { to: '/the-grid',  label: 'THE GRID' },
]

const auth   = useAuthStore()
const router = useRouter()
const route  = useRoute()

const initials = computed(() => {
  if (!auth.user?.username) return '?'
  return auth.user.username.slice(0, 2).toUpperCase()
})

function handleLogout() {
  if (confirm('Are you sure you want to sign out?')) {
    auth.logout()
    router.push('/')
  }
}

// ── Mobile menu: closes on navigation and on Escape ──
const menuOpen = ref(false)
function onKeydown(e) {
  if (e.key === 'Escape') menuOpen.value = false
}

// ── Active-route underline: one bar that slides between links ──
const linksEl   = ref(null)
const indicator = ref(null)   // { x, width } of the active link, null when none is active
const indicatorStyle = computed(() => indicator.value
  ? { width: `${indicator.value.width}px`, transform: `translateX(${indicator.value.x}px)`, opacity: 1 }
  : { opacity: 0 })

function placeIndicator() {
  const active = linksEl.value?.querySelector(':scope > .router-link-active')
  indicator.value = active ? { x: active.offsetLeft, width: active.offsetWidth } : null
}

watch(() => route.fullPath, async () => {
  menuOpen.value = false
  await nextTick()
  placeIndicator()
})

onMounted(() => {
  router.isReady().then(() => nextTick(placeIndicator))
  document.fonts?.ready.then(placeIndicator)   // link widths change when DM Mono arrives
  window.addEventListener('resize', placeIndicator)
  window.addEventListener('keydown', onKeydown)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', placeIndicator)
  window.removeEventListener('keydown', onKeydown)
})
</script>

<style scoped>
.navbar {
  position: fixed;
  top: 0; left: 0; right: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 40px;
  height: 56px;
  background: var(--nav-bg);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--nav-border);
  font-family: 'DM Mono', monospace;
}

.nav-logo {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 22px;
  letter-spacing: 3px;
  color: var(--text-primary);
  text-decoration: none;
}

.logo-dot { color: var(--accent); }

.nav-links {
  position: relative;
  align-self: stretch;
  display: flex;
  align-items: center;
  gap: 32px;
}

.nav-link {
  font-family: inherit;
  font-size: 11px;
  letter-spacing: 2px;
  color: var(--text-muted);
  text-decoration: none;
  background: none;
  border: none;
  cursor: pointer;
  transition: color 0.2s;
}

.nav-link:hover,
.nav-link.router-link-active { color: var(--text-primary); }

.nav-indicator {
  position: absolute;
  left: 0;
  bottom: -1px;   /* sits on the navbar's border */
  height: 2px;
  background: var(--accent);
  pointer-events: none;
  transition: transform var(--dur-slow) var(--ease), width var(--dur-slow) var(--ease), opacity var(--dur-base) var(--ease);
}

.menu-auth { display: none; }

.nav-auth,
.nav-account {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* User pill */
.user-pill {
  display: flex;
  align-items: center;
  gap: 8px;
  text-decoration: none;
  padding: 4px 12px 4px 4px;
  border: 1px solid var(--border-primary);
  transition: border-color 0.2s;
}

.user-pill:hover { border-color: var(--text-muted); }

.user-avatar {
  width: 26px;
  height: 26px;
  background: var(--accent);
  color: var(--text-inverse);
  font-size: 10px;
  font-weight: 500;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.user-name {
  font-size: 11px;
  letter-spacing: 1px;
  color: var(--text-primary);
}

/* Buttons */
.nav-btn-ghost {
  background: none;
  border: 1px solid var(--border-primary);
  color: var(--text-secondary);
  padding: 6px 14px;
  font-family: 'DM Mono', monospace;
  font-size: 10px;
  letter-spacing: 2px;
  cursor: pointer;
  text-decoration: none;
  white-space: nowrap;
  transition: border-color 0.2s, color 0.2s, scale var(--dur-fast) var(--ease);
  display: flex;
  align-items: center;
}

.nav-btn-ghost:hover { border-color: var(--text-secondary); color: var(--text-primary); }

.nav-btn-red {
  background: var(--accent);
  border: 1px solid var(--accent);
  color: #fff;
  padding: 6px 14px;
  font-family: 'DM Mono', monospace;
  font-size: 10px;
  letter-spacing: 2px;
  text-decoration: none;
  white-space: nowrap;
  transition: background 0.2s, scale var(--dur-fast) var(--ease);
  display: flex;
  align-items: center;
}

.nav-btn-red:hover { background: var(--accent-hover); border-color: var(--accent-hover); }

/* Menu button: same box as the two toggles beside it */
.menu-btn {
  display: none;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  background: var(--toggle-bg);
  border: 1px solid var(--toggle-border);
  border-radius: 6px;
  color: var(--toggle-icon);
  cursor: pointer;
  transition: border-color 0.2s, color 0.2s, scale var(--dur-fast) var(--ease);
  flex-shrink: 0;
}
.menu-btn:hover { border-color: var(--accent); color: var(--accent); }
.menu-btn svg { width: 16px; height: 16px; }
.menu-line {
  fill: none;
  stroke: currentColor;
  stroke-width: 1.5;
  transform-box: view-box;
  transform-origin: center;
  transition: transform var(--dur-base) var(--ease);
}
.menu-open .menu-line.top    { transform: translateY(2.5px) rotate(45deg); }
.menu-open .menu-line.bottom { transform: translateY(-2.5px) rotate(-45deg); }

/* ── Below 720 px: links collapse into a dropdown under the bar ── */
@media (max-width: 720px) {
  .navbar { padding: 0 20px; }
  .nav-account { display: none; }
  .menu-btn { display: flex; }
  .nav-indicator { display: none; }

  .nav-links {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    margin-top: 1px;   /* clear the navbar's border */
    flex-direction: column;
    align-items: stretch;
    gap: 0;
    background: var(--bg-primary);
    border-bottom: 1px solid var(--nav-border);
    opacity: 0;
    transform: translateY(-8px);
    visibility: hidden;
    transition: opacity var(--dur-base) var(--ease), transform var(--dur-base) var(--ease), visibility 0s var(--dur-base);
  }
  .menu-open .nav-links {
    opacity: 1;
    transform: none;
    visibility: visible;
    transition-delay: 0s;
  }

  .nav-link {
    display: block;
    width: 100%;
    padding: 16px 20px;
    text-align: left;
    font-size: 12px;
    border-bottom: 1px solid var(--border-primary);
    border-left: 2px solid transparent;
  }
  .nav-link.router-link-active { border-left-color: var(--accent); }
  .nav-link.accent { color: var(--accent); }

  .menu-auth { display: block; }
  .menu-auth .nav-link:last-child { border-bottom: none; }
}
</style>
