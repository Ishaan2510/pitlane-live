<template>
  <teleport to="body">
    <transition-group name="toast" tag="div" class="toast-container">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        class="toast"
        :class="toast.type"
      >
        <span class="toast-icon">{{ toast.icon }}</span>
        <div class="toast-body">
          <p class="toast-title">{{ toast.title }}</p>
          <p class="toast-message">{{ toast.message }}</p>
        </div>
        <button class="toast-close" @click="remove(toast.id)">×</button>
      </div>
    </transition-group>
  </teleport>
</template>

<script>
export default {
  name: 'ToastNotification',
  props: {
    toasts: { type: Array, default: () => [] }
  },
  emits: ['remove'],
  methods: {
    remove(id) { this.$emit('remove', id) }
  }
}
</script>

<style scoped>
.toast-container {
  position: fixed;
  top: 1.5rem;
  right: 1.5rem;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  pointer-events: none;
}

.toast {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem 1.25rem;
  border-radius: 12px;
  min-width: 320px;
  max-width: 420px;
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255,255,255,0.1);
  box-shadow: 0 8px 32px rgba(0,0,0,0.4);
  pointer-events: all;
  cursor: default;
}

.toast.success  { background: rgba(0, 180, 80, 0.85);  border-color: #00b450; }
.toast.error    { background: rgba(225, 6, 0, 0.85);   border-color: #e10600; }
.toast.info     { background: rgba(30, 120, 255, 0.85);border-color: #1e78ff; }
.toast.warning  { background: rgba(255, 165, 0, 0.85); border-color: #ffa500; }
.toast.pit      { background: rgba(60, 0, 120, 0.9);   border-color: #9900ff; }

.toast-icon { font-size: 1.75rem; flex-shrink: 0; }

.toast-body { flex: 1; }
.toast-title   { color: #fff; font-weight: 700; font-size: 0.95rem; margin-bottom: 0.2rem; }
.toast-message { color: rgba(255,255,255,0.85); font-size: 0.85rem; }

.toast-close {
  background: none; border: none; color: rgba(255,255,255,0.7);
  font-size: 1.4rem; cursor: pointer; padding: 0 0.25rem;
  line-height: 1; transition: color 0.2s;
}
.toast-close:hover { color: #fff; }

/* Slide-in animation */
.toast-enter-active { animation: slideIn 0.35s ease; }
.toast-leave-active { animation: slideOut 0.3s ease forwards; }

@keyframes slideIn {
  from { opacity: 0; transform: translateX(100px); }
  to   { opacity: 1; transform: translateX(0); }
}
@keyframes slideOut {
  from { opacity: 1; transform: translateX(0); }
  to   { opacity: 0; transform: translateX(100px); }
}
</style>
