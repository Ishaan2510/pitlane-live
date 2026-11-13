// The soundtrack player: one YouTube IFrame player for the whole app, kept here so it
// survives route changes. SoundToggle (navbar) and SoundDock (the visible player) both
// read `sound` and call the functions below.
//
// Rules this file keeps: nothing loads from YouTube before the first click, playback
// only ever starts from a click, and the UI state comes from the player's own events.
import { reactive } from 'vue'
import { tracks } from '@/config/soundtrack'

const OPENED_KEY  = 'pitlane-sound-opened'   // localStorage: user has opened the player before
const OFF_KEY     = 'pitlane-sound-off'      // sessionStorage: track list that failed this session
const LOAD_TIMEOUT_MS = 8000
const START_VOLUME    = 35
const SKIP_ERRORS     = [2, 5, 100, 101, 150]   // bad id, HTML5 error, removed, embedding disabled

const ids = tracks.map(t => t.videoId).join(',')

function read(storage, key) {
  try { return window[storage].getItem(key) } catch (e) { return null }
}
function write(storage, key, value) {
  try { window[storage].setItem(key, value) } catch (e) { /* storage blocked: carry on */ }
}

export const sound = reactive({
  available: tracks.length > 0 && read('sessionStorage', OFF_KEY) !== ids,
  openedBefore: read('localStorage', OPENED_KEY) === '1',
  open: false,
  minimised: false,
  status: 'idle',   // idle | loading | buffering | playing | paused
  muted: false,
  index: 0,
  hasNext: tracks.length > 1,
})

export const currentTrack = () => tracks[sound.index]

let host = null        // element in SoundDock the iframe goes into
let player = null
let loadTimer = null
const failed = new Set()

export function setHost(el) { host = el }

let apiRequested = false
function loadApi() {
  if (apiRequested) return
  apiRequested = true
  const previous = window.onYouTubeIframeAPIReady
  window.onYouTubeIframeAPIReady = () => { previous?.(); createPlayer() }
  const script = document.createElement('script')
  script.src = 'https://www.youtube.com/iframe_api'
  script.onerror = () => giveUp('the YouTube player script was blocked')
  document.head.appendChild(script)
}

function createPlayer() {
  if (player || !sound.open || !host) return
  const slot = document.createElement('div')
  host.appendChild(slot)
  player = new window.YT.Player(slot, {
    width: 200,
    height: 200,
    host: 'https://www.youtube-nocookie.com',
    videoId: currentTrack().videoId,
    playerVars: { playsinline: 1, controls: 1, rel: 0, modestbranding: 1, origin: window.location.origin, start: currentTrack().start || 0 },
    events: { onReady, onStateChange, onError },
  })
}

function onReady() {
  clearTimeout(loadTimer)
  player.setVolume(START_VOLUME)
  sound.status = 'paused'              // until the player itself reports otherwise
  if (sound.open) player.playVideo()   // still inside the flow the user's click started
}

function onStateChange({ data }) {
  const S = window.YT.PlayerState
  if (data === S.PLAYING)        sound.status = 'playing'
  else if (data === S.BUFFERING) sound.status = 'buffering'
  else if (data === S.PAUSED || data === S.CUED) sound.status = 'paused'
  else if (data === S.ENDED)     next()
  sound.muted = player.isMuted()
}

function onError({ data }) {
  if (!SKIP_ERRORS.includes(data)) return
  failed.add(sound.index)
  if (failed.size >= tracks.length) giveUp('no track could be embedded')
  else next()
}

// Next playable entry, wrapping round. With one track this replays it.
export function next() {
  if (!player) return
  for (let step = 1; step <= tracks.length; step++) {
    const i = (sound.index + step) % tracks.length
    if (!failed.has(i)) {
      sound.index = i
      player.loadVideoById({ videoId: tracks[i].videoId, startSeconds: tracks[i].start || 0 })
      return
    }
  }
}

function giveUp(reason) {
  clearTimeout(loadTimer)
  console.warn(`[soundtrack] Player hidden for this session: ${reason}. Video IDs tried: ${ids}`)
  try { player?.destroy() } catch (e) { /* half-built player */ }
  player = null
  sound.open = false
  sound.status = 'idle'
  sound.available = false
  write('sessionStorage', OFF_KEY, ids)
}

// Navbar button: the first click opens the dock and starts playback, later ones toggle.
export function toggle() {
  if (!sound.open) return open()
  // ?.() because the methods only exist once the player is ready
  if (sound.status === 'playing' || sound.status === 'buffering') player?.pauseVideo?.()
  else player?.playVideo?.()
}

function open() {
  sound.open = true
  sound.openedBefore = true
  write('localStorage', OPENED_KEY, '1')
  if (player) return player.playVideo?.()

  sound.status = 'loading'
  loadTimer = setTimeout(() => giveUp('YouTube did not load within 8 seconds'), LOAD_TIMEOUT_MS)
  if (window.YT?.Player) createPlayer()
  else loadApi()
}

export function close() {
  player?.stopVideo?.()
  sound.open = false
  if (sound.status === 'loading') {   // closed before YouTube arrived: not a failure
    clearTimeout(loadTimer)
    sound.status = 'idle'
  }
}

export function toggleMute() {
  if (!player?.isMuted) return
  sound.muted = !player.isMuted()
  sound.muted ? player.mute() : player.unMute()
}
