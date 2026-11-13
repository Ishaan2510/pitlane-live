<template>
  <!-- Shared empty / error state: a label, one line of text, an optional action.
       Pass `to` for a link, or listen for @action for a button (e.g. retry). -->
  <div class="state-panel" role="status">
    <div class="sp-label">{{ label }}</div>
    <p v-if="text" class="sp-text">{{ text }}</p>
    <router-link v-if="action && to" :to="to" class="sp-btn">{{ action }}</router-link>
    <button v-else-if="action" type="button" class="sp-btn" @click="$emit('action')">{{ action }}</button>
  </div>
</template>

<script setup>
defineProps({
  label:  { type: String, required: true },
  text:   { type: String, default: '' },
  action: { type: String, default: '' },
  to:     { type: [String, Object], default: null },
})
defineEmits(['action'])
</script>

<style scoped>
.state-panel {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  padding: 3.5rem 1.5rem;
  border: 1px solid var(--border-primary);
  text-align: center;
}
.sp-label {
  font-family: 'DM Mono', monospace;
  font-size: 0.68rem;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--accent);
}
.sp-text {
  font-size: 0.88rem;
  color: var(--text-secondary);
  max-width: 44ch;
}
.sp-btn {
  margin-top: 0.5rem;
  padding: 0.55rem 1.4rem;
  background: none;
  border: 1px solid var(--border-secondary);
  color: var(--text-primary);
  font-family: 'DM Mono', monospace;
  font-size: 0.68rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  text-decoration: none;
  cursor: pointer;
  transition: border-color var(--dur-base) var(--ease), color var(--dur-base) var(--ease), scale var(--dur-fast) var(--ease);
}
.sp-btn:hover { border-color: var(--accent); color: var(--accent); }
</style>
