<template>
  <div class="progress-bar">
    <div class="progress-fill" :style="{ width: progress + '%' }"></div>
    <div class="progress-label">
      Lap {{ currentLap }} / {{ totalLaps }}
    </div>
  </div>
</template>

<script>
export default {
  name: 'ProgressBar',
  props: {
    currentLap: { type: Number, required: true },
    totalLaps: { type: Number, required: true }
  },
  computed: {
    progress() {
      return (this.currentLap / this.totalLaps) * 100
    }
  }
}
</script>

<style scoped>
.progress-bar {
  position: relative;
  height: 40px;
  background: rgba(255, 255, 255, 0.05);
  border-top: 1px solid var(--color-border);
}

.progress-fill {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  background: var(--color-accent);
  transition: width 0.3s var(--ease);
}

.progress-label {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-family: monospace;
  font-weight: 600;
  font-size: 0.9rem;
  z-index: 2;
  color: var(--color-fg);
  text-shadow: 0 0 4px rgba(0, 0, 0, 0.8);
}
</style>
