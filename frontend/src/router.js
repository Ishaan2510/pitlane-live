import { createRouter, createWebHistory } from 'vue-router'
import Home from './views/Home.vue'
import LiveRace from './views/LiveRace.vue'
import Leaderboard from './views/Leaderboard.vue'

const routes = [
  { path: '/', name: 'Home', component: Home },
  { path: '/race/:id', name: 'LiveRace', component: LiveRace },
  { path: '/leaderboard', name: 'Leaderboard', component: Leaderboard }
]

export default createRouter({ history: createWebHistory(), routes })
