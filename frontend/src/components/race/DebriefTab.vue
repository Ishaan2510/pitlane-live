<template>
  <div class="tab-pad"><StatePanel label="Debrief" text="This tab is being built." /></div>
</template>

<script setup>
import StatePanel from '@/components/StatePanel.vue'
defineProps({ year: Number, round: Number, event: Object, results: Array })
</script>

<style scoped>
.tab-pad { max-width: 900px; margin: 0 auto; padding: 3rem 1.5rem; }
</style>
