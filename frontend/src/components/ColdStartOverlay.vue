<template>
  <transition name="overlay-fade">
    <div v-if="visible" class="cold-overlay">
      <div class="cold-inner">

        <!-- Logo -->
        <div class="cold-logo">PITLANE<span class="cold-dot">.</span></div>

        <!-- Animated F1 light sequence -->
        <div class="light-bar">
          <span
            v-for="n in 5"
            :key="n"
            class="light"
            :class="{ lit: litCount >= n }"
          ></span>
        </div>

        <!-- Status text -->
        <div class="cold-status">
          <span class="cold-pulse"></span>
          <span class="cold-text">{{ statusText }}</span>
        </div>

        <!-- Elapsed timer -->
        <div class="cold-elapsed">{{ elapsed }}s</div>

      </div>
    </div>
  </transition>
</template>

<script>
import { apiUrl } from '@/services/apiBase'

export default {
  name: 'ColdStartOverlay',

  data() {
    return {
      visible:    true,
      elapsed:    0,
      litCount:   0,
      statusText: 'Waking up the server',
      ticker:     null,
      lightTimer: null,
      pollTimer:  null,
    }
  },

  mounted() {
    // If backend responds instantly, skip the whole overlay
    this.checkBackend()

    // Tick elapsed counter every second
    this.ticker = setInterval(() => {
      this.elapsed++
      if (this.elapsed > 5 && this.elapsed <= 15) {
        this.statusText = 'Server is cold-starting on Render'
      } else if (this.elapsed > 15 && this.elapsed <= 40) {
        this.statusText = 'Almost there — loading race data'
      } else if (this.elapsed > 40) {
        this.statusText = 'Still warming up — hang tight'
      }
    }, 1000)

    // Animate F1 start lights (cycle 1→5 then reset)
    this.lightTimer = setInterval(() => {
      this.litCount++
      if (this.litCount > 5) this.litCount = 0
    }, 800)

    // Poll /health every 3 seconds
    this.pollTimer = setInterval(() => this.checkBackend(), 3000)
  },

  beforeUnmount() {
    clearInterval(this.ticker)
    clearInterval(this.lightTimer)
    clearInterval(this.pollTimer)
  },

  methods: {
    async checkBackend() {
      try {
        const res = await fetch(apiUrl('/api/health'), {
          signal: AbortSignal.timeout(5000),
        })
        if (res.ok) {
          this.dismiss()
        }
      } catch {
        // Still cold — keep waiting
      }
    },

    dismiss() {
      clearInterval(this.ticker)
      clearInterval(this.lightTimer)
      clearInterval(this.pollTimer)

      // Brief "lights out" moment before fade
      this.litCount   = 5
      this.statusText = 'Lights out and away we go'

      setTimeout(() => {
        this.visible = false
        this.$emit('ready')
      }, 600)
    },
  },
}
</script>

<style scoped>
.cold-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: #080808;
  display: flex;
  align-items: center;
  justify-content: center;
}

.cold-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2.5rem;
}

/* Logo */
.cold-logo {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 2.2rem;
  letter-spacing: 4px;
  color: #f5f5f5;
  user-select: none;
}
.cold-dot { color: #e10600; }

/* F1 start lights */
.light-bar {
  display: flex;
  gap: 12px;
}
.light {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #1a1a1a;
  border: 2px solid #2a2a2a;
  transition: background 0.3s, border-color 0.3s, box-shadow 0.3s;
}
.light.lit {
  background: #e10600;
  border-color: #e10600;
  box-shadow: 0 0 12px rgba(225, 6, 0, 0.6);
}

/* Status */
.cold-status {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}
.cold-pulse {
  width: 6px;
  height: 6px;
  background: #e10600;
  border-radius: 50%;
  animation: pulse 1.2s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50%      { opacity: 0.3; transform: scale(1.8); }
}
.cold-text {
  font-family: 'DM Mono', monospace;
  font-size: 0.78rem;
  color: #555;
  letter-spacing: 0.04em;
}

/* Elapsed */
.cold-elapsed {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 1rem;
  color: #1e1e1e;
  letter-spacing: 0.1em;
}

/* Fade out */
.overlay-fade-leave-active {
  transition: opacity 0.5s ease;
}
.overlay-fade-leave-to {
  opacity: 0;
}
</style>