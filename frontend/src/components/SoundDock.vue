<template>
  <!-- v-show, not v-if: the YouTube iframe lives in here and must survive open/close.
       Closing stops playback first, so nothing ever plays while this is hidden. -->
  <aside v-show="sound.open" class="dock" :class="{ minimised: sound.minimised }" aria-label="Soundtrack player">

    <!-- The YouTube player itself: always 200 x 200, never covered or clipped. -->
    <div ref="video" class="dock-video"></div>

    <div class="dock-panel">
      <div v-if="!sound.minimised" class="dock-info">
        <div class="dock-label" :class="{ pulsing: waiting }">{{ statusLabel }}</div>
        <div class="dock-title">{{ track.title }}</div>
        <div class="dock-artist">{{ track.artist }}</div>
      </div>

      <div class="dock-controls">
        <template v-if="!sound.minimised">
          <button class="dock-btn" type="button" :aria-label="playing ? 'Pause' : 'Play'" :title="playing ? 'Pause' : 'Play'" @click="toggle">
            <svg v-if="playing" viewBox="0 0 16 16" aria-hidden="true"><path d="M4 3h3v10H4zM9 3h3v10H9z" /></svg>
            <svg v-else viewBox="0 0 16 16" aria-hidden="true"><path d="M4 2.5v11l9-5.5z" /></svg>
          </button>
          <button v-if="sound.hasNext" class="dock-btn" type="button" aria-label="Next track" title="Next track" @click="next">
            <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M3 2.5v11l7-5.5zM11 3h2v10h-2z" /></svg>
          </button>
          <button class="dock-btn" type="button" :aria-pressed="sound.muted" :aria-label="sound.muted ? 'Unmute' : 'Mute'" :title="sound.muted ? 'Unmute' : 'Mute'" @click="toggleMute">
            <svg viewBox="0 0 16 16" aria-hidden="true">
              <path d="M2 6h3l4-3v10l-4-3H2z" />
              <path v-if="sound.muted" class="line" d="M11 6l4 4M15 6l-4 4" />
              <path v-else class="line" d="M11.5 5.5a3.5 3.5 0 0 1 0 5" />
            </svg>
          </button>
        </template>
        <button class="dock-btn" type="button" :aria-label="sound.minimised ? 'Expand player' : 'Minimise player'" :title="sound.minimised ? 'Expand' : 'Minimise'" @click="sound.minimised = !sound.minimised">
          <svg viewBox="0 0 16 16" aria-hidden="true">
            <path v-if="sound.minimised" class="line" d="M3 10l5-5 5 5" />
            <path v-else class="line" d="M3 12h10" />
          </svg>
        </button>
        <button class="dock-btn" type="button" aria-label="Close player and stop music" title="Close" @click="close">
          <svg viewBox="0 0 16 16" aria-hidden="true"><path class="line" d="M3 3l10 10M13 3L3 13" /></svg>
        </button>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { sound, currentTrack, setHost, toggle, next, toggleMute, close } from '@/services/soundtrack'

const video = ref(null)
onMounted(() => setHost(video.value))

const track   = computed(currentTrack)
const playing = computed(() => sound.status === 'playing' || sound.status === 'buffering')
const waiting = computed(() => sound.status === 'loading' || sound.status === 'buffering')
const statusLabel = computed(() => ({
  loading: 'LOADING', buffering: 'BUFFERING', playing: 'NOW PLAYING',
}[sound.status] || 'PAUSED'))
</script>

<style scoped>
.dock {
  position: fixed;
  right: 16px;
  bottom: 16px;
  z-index: 10000;   /* the video must never sit under another layer */
  display: flex;
  gap: 12px;
  padding: 12px;
  background: var(--bg-card);
  border: 1px solid var(--border-primary);
}

.dock-video {
  width: 200px;
  height: 200px;
  flex-shrink: 0;
  background: var(--bg-secondary);
}
.dock-video :deep(iframe) { display: block; width: 200px; height: 200px; border: 0; }

.dock-panel {
  width: 176px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 12px;
  min-width: 0;
}
.minimised .dock-panel { width: 32px; justify-content: flex-start; }

.dock-label {
  font-family: 'DM Mono', monospace;
  font-size: 10px;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--text-secondary);
  margin-bottom: 8px;
}
.dock-label.pulsing { animation: dock-pulse 900ms var(--ease) infinite alternate; }
@keyframes dock-pulse { to { opacity: 0.35; } }

.dock-title {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 1.5rem;
  line-height: 1;
  color: var(--text-primary);
  overflow-wrap: anywhere;
}
.dock-artist {
  margin-top: 6px;
  font-size: 0.72rem;
  color: var(--text-secondary);
  overflow-wrap: anywhere;
}

.dock-controls { display: flex; flex-wrap: wrap; gap: 4px; }
.minimised .dock-controls { flex-direction: column; }

.dock-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: 1px solid var(--border-primary);
  color: var(--text-secondary);
  cursor: pointer;
  transition: border-color 200ms var(--ease), color 200ms var(--ease);
}
.dock-btn:hover { border-color: var(--accent); color: var(--accent); }
.dock-btn:focus-visible { outline: 1px solid var(--accent); outline-offset: 2px; }
.dock-btn[aria-pressed="true"] { color: var(--accent); }
.dock-btn svg { width: 14px; height: 14px; fill: currentColor; }
.dock-btn .line { fill: none; stroke: currentColor; stroke-width: 1.5; }

@media (max-width: 480px) {
  .dock { left: 12px; right: 12px; bottom: 12px; }
  .dock-panel { width: auto; flex: 1; }
  .minimised.dock { left: 50%; right: auto; transform: translateX(-50%); }
  .minimised .dock-panel { flex: none; width: 32px; }
  .dock-title { font-size: 1.25rem; }
}

@media (prefers-reduced-motion: reduce) {
  .dock-label.pulsing { animation: none; }
}
</style>
