// Decides once per page load whether the lights-out intro plays, and tells Home how its
// hero should enter: 'hold' (hidden behind the intro), 'run' (staggered entrance) or
// 'none' (intro skipped, or reduced motion: show it at once).
import { ref } from 'vue'

const FLAG = 'pitlane-intro-seen'

function firstLoadOfSession() {
  try {
    const seen = sessionStorage.getItem(FLAG)
    sessionStorage.setItem(FLAG, '1')
    return !seen
  } catch (e) {
    return false   // storage blocked: never risk replaying the intro on every load
  }
}

const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
const first = firstLoadOfSession()

export const introPlays = first && !reducedMotion && window.location.pathname === '/'
export const heroEntrance = ref(introPlays ? 'hold' : reducedMotion ? 'none' : 'run')

export function introFinished(skipped) {
  heroEntrance.value = skipped ? 'none' : 'run'
}
