import { createRouter, createWebHistory } from 'vue-router'
import Home from './views/Home.vue'
import LiveRace from './views/LiveRace.vue'
import Leaderboard from './views/Leaderboard.vue'
import RaceReplay from './views/RaceReplay.vue'

const routes = [
  { path: '/', name: 'Home', component: Home },
  { path: '/race/:id', name: 'LiveRace', component: LiveRace },
  { path: '/leaderboard', name: 'Leaderboard', component: Leaderboard },
  { path: '/replay', name: 'RaceReplay', component: RaceReplay }
]

export default createRouter({ history: createWebHistory(), routes })
