<template>
  <teleport to="body">
    <div class="toast-tray">
      <transition-group name="toast" tag="div" class="toast-list">
        <div
          v-for="toast in toasts"
          :key="toast.id"
          class="toast"
          :class="toast.type"
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
/* Centred at the bottom — never covers left/right sidebars */
.toast-tray {
  position: fixed;
  bottom: 3rem;
  left: 50%;
  transform: translateX(-50%);
  z-index: 9999;
  pointer-events: none;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.4rem;
  min-width: 260px;
  max-width: 420px;
}

.toast-list {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.4rem;
  width: 100%;
}

.toast {
  padding: 0.5rem 1.1rem;
  border-radius: 6px;
  font-size: 0.82rem;
  font-weight: 600;
  letter-spacing: 0.01em;
  backdrop-filter: blur(8px);
  pointer-events: all;
  white-space: nowrap;
  box-shadow: 0 4px 16px rgba(0,0,0,0.5);

  /* Default: neutral dark */
  background: rgba(30, 30, 30, 0.95);
  color: #e0e0e0;
  border: 1px solid rgba(255,255,255,0.1);
}

/* Pit stop variant */
.toast.pit {
  background: rgba(30, 8, 8, 0.95);
  color: #ff9999;
  border-color: rgba(225, 6, 0, 0.4);
}

/* Enter/Leave animations */
.toast-enter-active { animation: pop-in  0.25s ease; }
.toast-leave-active { animation: pop-out 0.2s ease forwards; }

@keyframes pop-in  { from { opacity:0; transform:translateY(12px) scale(0.92); } to { opacity:1; transform:none; } }
@keyframes pop-out { from { opacity:1; transform:none; } to { opacity:0; transform:translateY(-8px) scale(0.9); } }
</style>
