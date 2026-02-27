<template>
  <nav class="navbar">
    <router-link to="/" class="nav-logo">PITLANE<span class="logo-dot">.</span></router-link>

    <div class="nav-links">
      <router-link to="/live"      class="nav-link">LIVE</router-link>
      <router-link to="/standings" class="nav-link">STANDINGS</router-link>
    </div>

    <div class="nav-auth">
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
  </nav>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth   = useAuthStore()
const router = useRouter()

const initials = computed(() => {
  if (!auth.user?.username) return '?'
  return auth.user.username.slice(0, 2).toUpperCase()
})

function handleLogout() {
  auth.logout()
  router.push('/')
}
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Mono:wght@400;500&display=swap');

.navbar {
  position: fixed;
  top: 0; left: 0; right: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 40px;
  height: 56px;
  background: rgba(10,10,10,0.95);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid #1e1e1e;
  font-family: 'DM Mono', monospace;
}

.nav-logo {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 22px;
  letter-spacing: 3px;
  color: #f0f0f0;
  text-decoration: none;
}

.logo-dot { color: #e8202a; }

.nav-links {
  display: flex;
  gap: 32px;
}

.nav-link {
  font-size: 11px;
  letter-spacing: 2px;
  color: #555;
  text-decoration: none;
  transition: color 0.2s;
}

.nav-link:hover,
.nav-link.router-link-active { color: #e8e8e8; }

.nav-auth {
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
  border: 1px solid #222;
  transition: border-color 0.2s;
}

.user-pill:hover { border-color: #444; }

.user-avatar {
  width: 26px;
  height: 26px;
  background: #e8202a;
  color: #fff;
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
  color: #e8e8e8;
}

/* Buttons */
.nav-btn-ghost {
  background: none;
  border: 1px solid #333;
  color: #888;
  padding: 6px 14px;
  font-family: 'DM Mono', monospace;
  font-size: 10px;
  letter-spacing: 2px;
  cursor: pointer;
  text-decoration: none;
  transition: border-color 0.2s, color 0.2s;
  display: flex;
  align-items: center;
}

.nav-btn-ghost:hover { border-color: #888; color: #e8e8e8; }

.nav-btn-red {
  background: #e8202a;
  border: 1px solid #e8202a;
  color: #fff;
  padding: 6px 14px;
  font-family: 'DM Mono', monospace;
  font-size: 10px;
  letter-spacing: 2px;
  text-decoration: none;
  transition: background 0.2s;
  display: flex;
  align-items: center;
}

.nav-btn-red:hover { background: #c0181f; }

@media (max-width: 600px) {
  .navbar { padding: 0 20px; }
  .nav-links { display: none; }
}
</style>