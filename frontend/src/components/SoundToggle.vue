<template>
  <button
    v-if="sound.available"
    class="sound-toggle"
    :class="{ playing, hint: sound.openedBefore && !playing, waiting }"
    type="button"
    :aria-pressed="playing"
    :aria-label="label"
    :title="label"
    @click="toggle"
  >
    <svg viewBox="0 0 16 16" aria-hidden="true">
      <rect v-for="i in 4" :key="i" class="bar" :x="i * 4 - 3" y="1" width="2" height="14" />
    </svg>
  </button>
</template>

<script setup>
import { computed } from 'vue'
import { sound, toggle } from '@/services/soundtrack'

const playing = computed(() => sound.status === 'playing')
const waiting = computed(() => sound.status === 'loading' || sound.status === 'buffering')
const label   = computed(() => (playing.value || waiting.value ? 'Pause soundtrack' : 'Play soundtrack'))
</script>

<style scoped>
/* Same box as ThemeToggle so the two read as a pair. */
.sound-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  background: var(--toggle-bg);
  border: 1px solid var(--toggle-border);
  border-radius: 6px;
  color: var(--toggle-icon);
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s, color 0.2s;
  flex-shrink: 0;
}
.sound-toggle:hover { border-color: var(--accent); color: var(--accent); }
.sound-toggle.playing,
.sound-toggle.waiting,
.sound-toggle.hint { color: var(--accent); }

.sound-toggle svg { width: 16px; height: 16px; }

.bar {
  fill: currentColor;
  transform-box: fill-box;
  transform-origin: 50% 100%;
  transform: scaleY(0.2);   /* idle: flat */
}
.playing .bar { animation: eq 640ms var(--ease) infinite alternate; }
.playing .bar:nth-child(1) { animation-duration: 520ms; }
.playing .bar:nth-child(2) { animation-duration: 760ms; }
.playing .bar:nth-child(3) { animation-duration: 440ms; }
.playing .bar:nth-child(4) { animation-duration: 680ms; }
@keyframes eq {
  from { transform: scaleY(0.25); }
  to   { transform: scaleY(1); }
}

.waiting svg { animation: eq-wait 900ms var(--ease) infinite alternate; }
@keyframes eq-wait { to { opacity: 0.35; } }

@media (prefers-reduced-motion: reduce) {
  .playing .bar, .waiting svg { animation: none; }
  /* still show "playing" without motion: uneven static bars */
  .playing .bar:nth-child(1) { transform: scaleY(0.5); }
  .playing .bar:nth-child(2) { transform: scaleY(1); }
  .playing .bar:nth-child(3) { transform: scaleY(0.7); }
  .playing .bar:nth-child(4) { transform: scaleY(0.4); }
}
</style>
