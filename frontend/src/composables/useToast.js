import { reactive } from 'vue'

let nextId = 1

const toasts = reactive([])

export function useToast() {
  function add({ type = 'info', title, message, icon, duration = 4000 }) {
    const id = nextId++
    toasts.push({ id, type, title, message, icon: icon || defaultIcon(type) })
    if (duration > 0) setTimeout(() => remove(id), duration)
  }

  function remove(id) {
    const i = toasts.findIndex(t => t.id === id)
    if (i !== -1) toasts.splice(i, 1)
  }

  // Shorthand helpers
  const success = (title, message) => add({ type: 'success', title, message })
  const error   = (title, message) => add({ type: 'error',   title, message })
  const info    = (title, message) => add({ type: 'info',    title, message })
  const warning = (title, message) => add({ type: 'warning', title, message })
  const pit     = (title, message) => add({ type: 'pit',     title, message, icon: '🔧', duration: 5000 })

  return { toasts, add, remove, success, error, info, warning, pit }
}

function defaultIcon(type) {
  return { success:'✅', error:'❌', info:'ℹ️', warning:'⚠️', pit:'🔧' }[type] || 'ℹ️'
}
