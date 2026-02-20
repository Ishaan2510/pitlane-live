<template>
  <teleport to="body">
    <div class="toasts">
      <transition-group name="toast">
        <div
          v-for="toast in toasts"
          :key="toast.id"
          class="toast"
        >
          {{ toast.message }}
        </div>
      </transition-group>
    </div>
  </teleport>
</template>

<script>
export default {
  name: 'ToastNotification',
  props: {
    toasts: { type: Array, default: () => [] }
  },
  emits: ['remove']
}
</script>

<style scoped>
.toasts {
  position: fixed;
  bottom: 2rem;
  right: 2rem;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  pointer-events: none;
}

.toast {
  padding: 0.75rem 1.5rem;
  background: rgba(255, 255, 255, 0.95);
  color: #0a0a0a;
  border-radius: 4px;
  font-size: 0.85rem;
  font-weight: 500;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  pointer-events: all;
}

.toast-enter-active {
  animation: slide-in 0.3s ease;
}

.toast-leave-active {
  animation: slide-out 0.2s ease;
}

@keyframes slide-in {
  from {
    opacity: 0;
    transform: translateX(100%);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@keyframes slide-out {
  from {
    opacity: 1;
    transform: translateX(0);
  }
  to {
    opacity: 0;
    transform: translateX(100%);
  }
}
</style>
