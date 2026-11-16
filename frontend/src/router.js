import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { getRaces } from '@/services/data'

const SITE = 'Pitlane Live'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home.vue')   // no meta.title: the home page is just the site name
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { guestOnly: true, title: 'Sign in' }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/Register.vue'),
    meta: { guestOnly: true, title: 'Join the grid' }
  },
  {
    path: '/live',
    name: 'WatchLive',
    component: () => import('@/views/WatchLive.vue'),
    meta: { title: 'Race Weekend' }
  },
  {
    // The old live-timing simulation: now the Race Room of the newest built race
    path: '/live/timing',
    component: () => import('@/views/RaceLibrary.vue'),   // never rendered: the guard always redirects
    beforeEnter: () => getRaces()
      .then(races => (races[0] ? `/race/${races[0].year}/${races[0].round}` : '/replay'))
      .catch(() => '/replay')
  },
  {
    path: '/replay',
    name: 'Replay',
    component: () => import('@/views/RaceLibrary.vue'),
    meta: { title: 'Race Library' }
  },
  {
    path: '/replay/:year/:round',
    redirect: to => `/race/${to.params.year}/${to.params.round}`
  },
  {
    path: '/race/:year(\\d+)/:round(\\d+)/:tab?',
    name: 'RaceRoom',
    component: () => import('@/views/RaceRoom.vue'),
    meta: {
      // "São Paulo Grand Prix 2026"; falls back to the bare site name if the race is unknown
      title: to => getRaces().then(races => {
        const race = races.find(r => r.year === +to.params.year && r.round === +to.params.round)
        return race ? `${race.name} ${race.year}` : null
      })
    }
  },
  {
    path: '/about/strategy-model',
    name: 'StrategyModel',
    component: () => import('@/views/StrategyModel.vue'),
    meta: { title: 'How the Strategy tab works' }
  },
  {
    path: '/standings',
    name: 'Standings',
    component: () => import('@/views/Standings.vue'),
    meta: { title: 'Standings' }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('@/views/Profile.vue'),
    meta: { requiresAuth: true, title: 'Profile' }
  },
  {
    path: '/pit-wall',
    name: 'PitWall',
    component: () => import('@/views/PitWall.vue'),
    meta: { title: 'Pit Wall' }
  },
  {
    path: '/the-grid', 
    name: 'TheGrid',
    component: () => import('@/views/TheGrid.vue'),
    meta: { title: 'The Grid' }
  },
  {
    path: '/predict/:year/:round',
    name: 'PredictRace',
    component: () => import('@/views/PredictRace.vue'),
    meta: { requiresAuth: true, title: 'Predict the race' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  // Top of the page on navigation; back and forward restore where you were.
  // 'instant' because globals.css sets smooth scrolling on <html>.
  // Resolved after the 200 ms page fade-out, so the old page does not jump first.
  scrollBehavior(to, from, savedPosition) {
    // Same page, new query (the Strategy tab writes its scenario to the URL as you edit,
    // the replay its lap): stay where the reader is.
    if (to.path === from.path && !savedPosition) return false
    const position = { ...(savedPosition || { top: 0 }), behavior: 'instant' }
    return new Promise(resolve => setTimeout(() => resolve(position), 200))
  }
})

// Where to go after login/register: only same-site paths, never "//evil.com"
export function safeRedirect(value) {
  return typeof value === 'string' && value.startsWith('/') && !value.startsWith('//') ? value : '/'
}

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

// <title> per route: "Race Library · Pitlane Live". meta.title is a string or a
// function of the route that returns (a promise of) one.
router.afterEach(async to => {
  let title = to.meta.title
  if (typeof title === 'function') title = await Promise.resolve(title(to)).catch(() => null)
  if (router.currentRoute.value.fullPath !== to.fullPath) return   // navigated on meanwhile
  document.title = title ? `${title} · ${SITE}` : SITE
})

export default router