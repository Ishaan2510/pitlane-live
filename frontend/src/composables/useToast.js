import { reactive } from 'vue'

let nextId = 1
const toasts = reactive([])

export function useToast() {
  function add({ message, duration = 3000 }) {
    const id = nextId++
    toasts.push({ id, message })
    
    if (duration > 0) {
      setTimeout(() => remove(id), duration)
    }
  }

  function remove(id) {
    const i = toasts.findIndex(t => t.id === id)
    if (i !== -1) toasts.splice(i, 1)
  }

  // Simple helpers
  const show = (message) => add({ message })

  return { toasts, add, remove, show }
}
