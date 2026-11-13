// Tracks in-flight /api requests (fetch and axios) so the cold-start overlay can show
// only while a backend call is actually waiting. Pages that read /data/ never trigger it.
import { ref } from 'vue'
import axios from 'axios'

const SLOW_MS = 1500   // a warm backend answers well inside this; a cold Render box does not

export const apiWaiting = ref(false)   // true while an /api call has been pending > SLOW_MS

let pending = 0
let timer = null

function started() {
  pending++
  if (!timer && !apiWaiting.value) {
    timer = setTimeout(() => {
      timer = null
      if (pending > 0) apiWaiting.value = true
    }, SLOW_MS)
  }
}

function finished() {
  pending = Math.max(0, pending - 1)
  if (pending === 0) {
    clearTimeout(timer)
    timer = null
    apiWaiting.value = false
  }
}

const isApi = url => String(url || '').includes('/api/')

export function installApiPendingTracker() {
  const nativeFetch = window.fetch.bind(window)
  window.fetch = (input, init) => {
    const request = nativeFetch(input, init)
    if (isApi(typeof input === 'string' ? input : input?.url)) {
      started()
      request.then(finished, finished)
    }
    return request
  }

  axios.interceptors.request.use(config => {
    config.trackedApi = isApi(config.url)
    if (config.trackedApi) started()
    return config
  })
  const done = config => { if (config?.trackedApi) finished() }
  axios.interceptors.response.use(
    response => { done(response.config); return response },
    error => { done(error.config); return Promise.reject(error) }
  )
}
