import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home.vue')
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { guestOnly: true }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/Register.vue'),
    meta: { guestOnly: true }
  },
  {
    path: '/live',
    name: 'WatchLive',
    component: () => import('@/views/WatchLive.vue')
  },
  {
    path: '/replay',
    name: 'Replay',
    component: () => import('@/views/RaceReplay.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/replay/:year/:round',
    name: 'RaceReplay',
    component: () => import('@/views/RaceReplay.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/standings',
    name: 'Standings',
    component: () => import('@/views/Standings.vue')
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('@/views/Profile.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/pit-wall',
    name: 'PitWall',
    component: () => import('@/views/PitWall.vue')
  },
  {
    path: '/the-grid', 
    name: 'TheGrid',
    component: () => import('@/views/TheGrid.vue'),
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const auth = useAuthStore()

  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    return next({ name: 'Login', query: { redirect: to.fullPath } })
  }

  if (to.meta.guestOnly && auth.isLoggedIn) {
    return next({ name: 'Home' })
  }

  next()
})

export default router