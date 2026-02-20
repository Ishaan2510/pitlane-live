<template>
  <div v-if="weather" class="weather-panel">
    <h4 class="panel-title">Weather</h4>
    <div class="weather-grid">
      <div class="weather-item">
        <span class="label">🌡️ Track</span>
        <span class="value">{{ weather.track_temp }}°C</span>
      </div>
      <div class="weather-item">
        <span class="label">🌡️ Air</span>
        <span class="value">{{ weather.air_temp }}°C</span>
      </div>
      <div class="weather-item">
        <span class="label">💧 Humidity</span>
        <span class="value">{{ weather.humidity }}%</span>
      </div>
      <div class="weather-item">
        <span class="label">💨 Wind</span>
        <span class="value">{{ weather.wind_speed }} km/h</span>
      </div>
      <div v-if="weather.rainfall" class="weather-item">
        <span class="label">🌧️</span>
        <span class="value">Rain</span>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'WeatherPanel',
  props: {
    weather: { type: Object, default: null }
  }
}
</script>

<style scoped>
.weather-panel {
  padding: 1rem;
  border: 1px solid var(--color-border);
  background: rgba(255, 255, 255, 0.02);
  margin-bottom: 1rem;
}

.panel-title {
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--color-muted);
  margin-bottom: 0.75rem;
}

.weather-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.5rem;
}

.weather-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.weather-item .label {
  font-size: 0.75rem;
  color: var(--color-muted);
}

.weather-item .value {
  font-weight: 500;
  font-family: monospace;
}
</style>
