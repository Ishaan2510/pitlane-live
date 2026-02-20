<template>
  <div v-if="driver" class="telemetry-panel">
    <div class="panel-header">
      <h4>{{ driver.driver }}</h4>
      <span class="team-name">{{ driver.team }}</span>
    </div>
    
    <div class="telemetry-grid">
      <div class="telemetry-item">
        <span class="label">Speed (avg)</span>
        <span class="value">{{ formatSpeed(driver.avg_speed) }}</span>
      </div>
      
      <div class="telemetry-item">
        <span class="label">Speed (max)</span>
        <span class="value">{{ formatSpeed(driver.max_speed) }}</span>
      </div>
      
      <div class="telemetry-item">
        <span class="label">Gap</span>
        <span class="value">{{ driver.gap }}</span>
      </div>
      
      <div class="telemetry-item">
        <span class="label">Tire</span>
        <span class="value">
          <span class="tire-badge" :class="driver.compound.toLowerCase()">
            {{ driver.compound }}
          </span>
        </span>
      </div>
      
      <div class="telemetry-item">
        <span class="label">Tire Age</span>
        <span class="value">{{ driver.tire_life }} laps</span>
      </div>
      
      <div class="telemetry-item">
        <span class="label">Position</span>
        <span class="value">P{{ driver.position }}</span>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'TelemetryPanel',
  props: {
    driver: { type: Object, default: null }
  },
  methods: {
    formatSpeed(speed) {
      if (!speed) return 'N/A'
      return `${Math.round(speed)} km/h`
    }
  }
}
</script>

<style scoped>
.telemetry-panel {
  padding: 1.5rem;
  border: 1px solid var(--color-border);
  background: rgba(255, 255, 255, 0.02);
}

.panel-header {
  margin-bottom: 1rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--color-border);
}

.panel-header h4 {
  font-family: var(--font-display);
  font-size: 1.5rem;
  margin-bottom: 0.25rem;
}

.team-name {
  font-size: 0.85rem;
  color: var(--color-muted);
}

.telemetry-grid {
  display: grid;
  gap: 1rem;
}

.telemetry-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.telemetry-item:last-child {
  border-bottom: none;
}

.telemetry-item .label {
  font-size: 0.85rem;
  color: var(--color-muted);
}

.telemetry-item .value {
  font-weight: 500;
  font-family: monospace;
}

.tire-badge {
  padding: 0.25rem 0.5rem;
  border-radius: 2px;
  font-size: 0.75rem;
  font-weight: 600;
}

.tire-badge.soft {
  background: rgba(255, 0, 0, 0.2);
  color: #ff6666;
}

.tire-badge.medium {
  background: rgba(255, 255, 0, 0.2);
  color: #ffff66;
}

.tire-badge.hard {
  background: rgba(255, 255, 255, 0.2);
  color: #fff;
}
</style>
