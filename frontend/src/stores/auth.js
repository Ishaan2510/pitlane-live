import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

const API = `${import.meta.env.VITE_API_URL || 'http://localhost:5000'}/api`

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('pitlane_token') || null)
  const user  = ref(JSON.parse(localStorage.getItem('pitlane_user') || 'null'))

  const isLoggedIn = computed(() => !!token.value)

  function _persist(t, u) {
    token.value = t
    user.value  = u
    localStorage.setItem('pitlane_token', t)
    localStorage.setItem('pitlane_user', JSON.stringify(u))
  }

  function logout() {
    token.value = null
    user.value  = null
    localStorage.removeItem('pitlane_token')
    localStorage.removeItem('pitlane_user')
  }

  async function register(username, email, password) {
    const res  = await fetch(`${API}/auth/register`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ username, email, password })
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.error || 'Registration failed')
    _persist(data.token, data.user)
    return data.user
  }

  async function login(identifier, password) {
    const res  = await fetch(`${API}/auth/login`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ identifier, password })
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.error || 'Login failed')
    _persist(data.token, data.user)
    return data.user
  }

  async function fetchMe() {
    if (!token.value) return
    const res = await fetch(`${API}/auth/me`, {
      headers: { Authorization: `Bearer ${token.value}` }
    })
    if (!res.ok) { logout(); return }
    user.value = await res.json()
    localStorage.setItem('pitlane_user', JSON.stringify(user.value))
  }

  return { token, user, isLoggedIn, register, login, logout, fetchMe }
})