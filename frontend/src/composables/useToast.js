import { reactive } from 'vue'

let nextId = 1
const toasts = reactive([])
const MAX_TOASTS = 3

export function useToast() {
  function add({ message, duration = 3000, type = 'info' }) {
    // Drop oldest toast if we're at capacity
    while (toasts.length >= MAX_TOASTS) toasts.shift()

    const id = nextId++
    toasts.push({ id, message, type })

    if (duration > 0) {
      setTimeout(() => remove(id), duration)
    }
  }

  function remove(id) {
    const i = toasts.findIndex(t => t.id === id)
    if (i !== -1) toasts.splice(i, 1)
  }

  // Generic one-liner
  const show = (message, type = 'info') => add({ message, type })

  // Pit-stop specific: short-lived, visually distinct
  const pit  = (message) => add({ message, duration: 1800, type: 'pit' })

  return { toasts, add, remove, show, pit }
}
