import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './assets/globals.css'
import './assets/theme.css'
import './assets/motion.css'
import reveal from './directives/reveal'
import { createPinia } from 'pinia'
import { useAuthStore } from './stores/auth'
import { installApiPendingTracker } from './services/apiPending'

installApiPendingTracker()   // before the first request, so the cold-start overlay sees it

const app = createApp(App)
app.use(router)
app.use(createPinia())
app.directive('reveal', reveal)
// Drop stale/expired tokens on startup so the UI doesn't look logged in while every request 401s
useAuthStore().fetchMe()
app.mount('#app')
