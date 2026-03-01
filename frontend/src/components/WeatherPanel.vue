<template>
  <div v-if="weather" class="weather-panel">
    <div class="panel-title">WEATHER</div>
    <div class="weather-grid">
      <div class="weather-item">
        <span class="w-label">
          <svg width="11" height="14" viewBox="0 0 11 14" fill="none">
            <rect x="4" y="0" width="3" height="8.5" rx="1.5" stroke="currentColor" stroke-width="1.2"/>
            <circle cx="5.5" cy="11" r="2.5" stroke="currentColor" stroke-width="1.2"/>
            <line x1="5.5" y1="8.5" x2="5.5" y2="9.5" stroke="currentColor" stroke-width="1.2"/>
            <line x1="7.5" y1="3" x2="9" y2="3" stroke="currentColor" stroke-width="1"/>
            <line x1="7.5" y1="5" x2="9" y2="5" stroke="currentColor" stroke-width="1"/>
          </svg>
          Track
        </span>
        <span class="w-value">{{ weather.track_temp }}°C</span>
      </div>
      <div class="weather-item">
        <span class="w-label">
          <svg width="11" height="14" viewBox="0 0 11 14" fill="none">
            <rect x="4" y="0" width="3" height="8.5" rx="1.5" stroke="currentColor" stroke-width="1.2" opacity="0.5"/>
            <circle cx="5.5" cy="11" r="2.5" stroke="currentColor" stroke-width="1.2"/>
            <line x1="5.5" y1="8.5" x2="5.5" y2="9.5" stroke="currentColor" stroke-width="1.2"/>
          </svg>
          Air
        </span>
        <span class="w-value">{{ weather.air_temp }}°C</span>
      </div>
      <div class="weather-item">
        <span class="w-label">
          <svg width="12" height="13" viewBox="0 0 12 13" fill="none">
            <path d="M6 1 C6 1 2 5.5 2 8a4 4 0 0 0 8 0C10 5.5 6 1 6 1z" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/>
          </svg>
          Humidity
        </span>
        <span class="w-value">{{ weather.humidity }}%</span>
      </div>
      <div class="weather-item">
        <span class="w-label">
          <svg width="14" height="10" viewBox="0 0 14 10" fill="none">
            <path d="M1 5h10M8 2l3 3-3 3" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M1 2.5h6a2 2 0 0 1 0 4H6" stroke="currentColor" stroke-width="1" stroke-linecap="round" opacity="0.4"/>
          </svg>
          Wind
        </span>
        <span class="w-value">{{ weather.wind_speed }} km/h</span>
      </div>
      <div v-if="weather.rainfall" class="weather-item weather-rain">
        <span class="w-label">
          <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
            <path d="M6.5 1 C6.5 1 2.5 5 2.5 7.5a4 4 0 0 0 8 0C10.5 5 6.5 1 6.5 1z" stroke="currentColor" stroke-width="1.2"/>
            <line x1="4" y1="10.5" x2="3" y2="12.5" stroke="currentColor" stroke-width="1" stroke-linecap="round"/>
            <line x1="6.5" y1="10.5" x2="5.5" y2="12.5" stroke="currentColor" stroke-width="1" stroke-linecap="round"/>
            <line x1="9" y1="10.5" x2="8" y2="12.5" stroke="currentColor" stroke-width="1" stroke-linecap="round"/>
          </svg>
          Rain
        </span>
        <span class="w-value rain-val">WET</span>
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
  border: 1px solid var(--color-border, #1a1a1a);
  background: rgba(255,255,255,0.015);
  margin-bottom: 1rem;
}
.panel-title {
  font-size: 0.58rem;
  letter-spacing: 0.14em;
  color: #333;
  font-weight: 700;
  margin-bottom: 0.85rem;
}
.weather-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.7rem 0.5rem;
}
.weather-item {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}
.w-label {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.65rem;
  color: #3a3a3a;
  font-weight: 500;
  letter-spacing: 0.03em;
}
.w-label svg { color: #3a3a3a; flex-shrink: 0; }
.w-value {
  font-family: monospace;
  font-size: 0.88rem;
  font-weight: 600;
  color: #aaa;
  padding-left: 1px;
}
.weather-rain .w-label svg { color: #5599ff; }
.rain-val { color: #5599ff; }
</style>