// Records the real site in use, frame by frame, over the Chrome DevTools protocol
// (a headless Chrome must be listening on --remote-debugging-port=9555).
//
//   node video/footage/record.mjs <clip name> <landscape|vertical> <out dir>
//
// Writes <out dir>/<clip>-<format>/f00000.jpg ... at a constant 30 fps (1920x1080 or 1080x1920).
import { mkdirSync, writeFileSync, rmSync } from 'node:fs'
import { execFileSync } from 'node:child_process'

// Headless Chrome screencasts in CSS pixels, so the page is laid out at (close to) the
// output size with no device scaling: 1920x1080, and a 720x1280 phone layout scaled 1.5x.
const PORT = +(process.env.PORT || 9555)
const SITE = process.env.SITE || 'https://pitlane-live-f1.vercel.app'
const FPS = 30
const FORMATS = {
  landscape: { width: 1920, height: 1080, dpr: 1, mobile: false },   // 1920x1080 frames
  vertical:  { width: 720,  height: 1280, dpr: 1, mobile: true },    // phone layout, scaled to 1080x1920
}

// In-page helpers every clip's script can use: a visible cursor, smooth pointer moves,
// clicks, drags and smooth scrolling. Pointer events are dispatched on the element under
// the point, like a real mouse.
const HELPERS = `
  const sleep = ms => new Promise(r => setTimeout(r, ms))
  const cursor = document.createElement('div')
  cursor.innerHTML = '<svg width="30" height="30" viewBox="0 0 24 24"><path d="M4 2l15 9-6.5 1.6L9.6 19z" fill="#fff" stroke="#000" stroke-width="1.4" stroke-linejoin="round"/></svg>'
  Object.assign(cursor.style, { position: 'fixed', left: '0', top: '0', zIndex: 99999, pointerEvents: 'none', transform: 'translate(-3px,-2px)', transition: 'scale 120ms', filter: 'drop-shadow(0 2px 3px rgba(0,0,0,.5))' })
  document.body.appendChild(cursor)
  let px = innerWidth * 0.6, py = innerHeight * 0.55
  const place = (x, y) => { px = x; py = y; cursor.style.left = x + 'px'; cursor.style.top = y + 'px' }
  place(px, py)
  const ease = t => t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2
  const fire = (type, x, y, target) => (target || document.elementFromPoint(x, y))?.dispatchEvent(new PointerEvent(type, { pointerId: 1, pointerType: 'mouse', clientX: x, clientY: y, bubbles: true, cancelable: true, buttons: type === 'pointerup' ? 0 : 1 }))
  async function moveTo(x, y, ms = 600, onStep) {
    const x0 = px, y0 = py, t0 = performance.now()
    while (true) {
      const k = Math.min(1, (performance.now() - t0) / ms), e = ease(k)
      place(x0 + (x - x0) * e, y0 + (y - y0) * e)
      onStep?.(px, py)
      if (k >= 1) break
      await sleep(16)
    }
  }
  const center = el => { const r = el.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2] }
  async function click(el, ms = 500) {
    const [x, y] = center(el)
    await moveTo(x, y, ms)
    cursor.style.scale = '0.85'; await sleep(90); cursor.style.scale = '1'
    el.click()
  }
  async function drag(el, dx, dy, ms = 1200) {
    const [x, y] = center(el)
    await moveTo(x, y, 500)
    cursor.style.scale = '0.85'
    fire('pointerdown', x, y, el)
    await moveTo(x + dx, y + dy, ms, (cx, cy) => fire('pointermove', cx, cy, el))
    fire('pointerup', px, py, el)
    cursor.style.scale = '1'
  }
  async function scrollBy(dy, ms = 1500) {
    const y0 = scrollY, t0 = performance.now()
    while (true) {
      const k = Math.min(1, (performance.now() - t0) / ms)
      window.scrollTo(0, y0 + dy * ease(k))
      if (k >= 1) break
      await sleep(16)
    }
  }
  const $ = s => document.querySelector(s), $$ = s => [...document.querySelectorAll(s)]
  const byText = (sel, text) => $$(sel).find(e => e.textContent.trim().toUpperCase().includes(text.toUpperCase()))
`

// Each clip: the page, how long to record (s), and what to do while recording.
const CLIPS = {
  // A race playing on the map: Monaco 2025 from lap 30, at 2 s per lap
  replay: {
    path: '/race/2025/8?lap=30', seconds: 9,
    script: `
      await sleep(400)
      const fast = $$('.rr-wrap button, button').find(b => b.textContent.trim() === '2')
      if (fast) await click(fast, 500)
      const play = $('.control-btn.primary')
      if (play) await click(play, 600)
      await moveTo(innerWidth * 0.5, innerHeight * 0.45, 900)
      await sleep(5500)`,
  },
  // Piastri at Monza 2024: drag the second stop off the bar, the verdict flips to P1
  strategy: {
    path: '/race/2024/16/strategy?d=PIA&s=M-16-H-38-H&seed=1', seconds: 10,
    script: `
      await sleep(600)
      const editor = $('.editor')
      window.scrollTo(0, editor.getBoundingClientRect().top + scrollY - (innerWidth < 800 ? 60 : 90))
      await sleep(900)
      const markers = $$('.ed-marker')
      await drag(markers[markers.length - 1], 0, -150, 1300)
      await sleep(1200)
      const verdict = $('.verdict')
      if (innerWidth < 800) await scrollBy(verdict.getBoundingClientRect().top - 120, 1100)
      else await scrollBy(verdict.getBoundingClientRect().top - 220, 1100)
      await moveTo(...center($('.v-line')), 800)
      await sleep(3000)`,
  },
  // Then the model's fastest preset and the charts
  strategyCharts: {
    path: '/race/2024/16/strategy?d=PIA&s=M-16-H&seed=1', seconds: 8,
    script: `
      await sleep(500)
      const charts = $('.charts')
      await scrollBy(charts.getBoundingClientRect().top - 80, 2200)
      await sleep(700)
      await moveTo(innerWidth * 0.55, innerHeight * 0.45, 900)
      await sleep(600)
      await scrollBy(innerHeight * 0.9, 2000)
      await sleep(900)`,
  },
  // The debrief: cards, then charts, highlighting a driver
  debrief: {
    path: '/race/2026/19/debrief', seconds: 9,
    script: `
      await sleep(700)
      await scrollBy(innerWidth < 800 ? 900 : 430, 1800)
      await sleep(400)
      const chip = $$('.chip').find(c => c.textContent.trim() === 'HAM')
      if (chip) {
        const label = $$('.driver-label').find(t => t.textContent.trim() === 'HAM')
        if (label) { await moveTo(...center(label), 800); label.dispatchEvent(new MouseEvent('click', { bubbles: true })) }
      }
      await sleep(1200)
      await scrollBy(innerWidth < 800 ? 1100 : 520, 1800)
      await sleep(1500)`,
  },
  // Tyre degradation chart
  degradation: {
    path: '/race/2024/16/debrief', seconds: 6,
    script: `
      await sleep(600)
      const t = $$('.cf-title').find(e => e.textContent.includes('Tyre degradation'))
      await scrollBy(t.getBoundingClientRect().top - 90, 2200)
      await moveTo(innerWidth * 0.62, innerHeight * 0.5, 1000)
      await sleep(2000)`,
  },
  // The race library, scrolling
  library: {
    path: '/replay', seconds: 5,
    script: `
      await sleep(500)
      await scrollBy(innerWidth < 800 ? 1300 : 700, 3000)
      await sleep(800)`,
  },
}

function connect(url) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(url)
    let id = 0
    const pending = new Map(), handlers = []
    ws.onmessage = e => {
      const m = JSON.parse(e.data)
      if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); m.error ? p.reject(new Error(m.error.message)) : p.resolve(m.result) }
      else if (m.method) handlers.forEach(h => h(m))
    }
    ws.onopen = () => resolve({
      send: (method, params = {}) => new Promise((res, rej) => { pending.set(++id, { resolve: res, reject: rej }); ws.send(JSON.stringify({ id, method, params })) }),
      on: h => handlers.push(h), close: () => ws.close(),
    })
    ws.onerror = reject
  })
}

const [clipName, formatName, outDir] = process.argv.slice(2)
const clip = CLIPS[clipName], fmt = FORMATS[formatName]
if (!clip || !fmt) throw new Error(`usage: record.mjs <${Object.keys(CLIPS).join('|')}> <landscape|vertical> <out dir>`)
const dir = `${outDir}/${clipName}-${formatName}`
rmSync(dir, { recursive: true, force: true })
mkdirSync(dir, { recursive: true })

const target = await (await fetch(`http://127.0.0.1:${PORT}/json/new?about:blank`, { method: 'PUT' })).json()
const cdp = await connect(target.webSocketDebuggerUrl)
await cdp.send('Page.enable'); await cdp.send('Runtime.enable')
await cdp.send('Emulation.setDeviceMetricsOverride', { width: fmt.width, height: fmt.height, deviceScaleFactor: fmt.dpr, mobile: fmt.mobile })
await cdp.send('Page.addScriptToEvaluateOnNewDocument', { source: `try { localStorage.setItem('pitlane-theme', 'dark'); sessionStorage.setItem('pitlane-intro-seen', '1'); localStorage.setItem('pitlane-sound-show', '0') } catch {}` })
await cdp.send('Page.navigate', { url: SITE + clip.path })
await new Promise(r => setTimeout(r, 7000))          // data, fonts, worker
await cdp.send('Runtime.evaluate', { expression: `document.documentElement.style.scrollBehavior = 'auto'; document.body.style.cursor = 'none'` })

const frames = []
cdp.on(m => {
  if (m.method !== 'Page.screencastFrame') return
  frames.push({ t: m.params.metadata.timestamp, data: m.params.data })
  cdp.send('Page.screencastFrameAck', { sessionId: m.params.sessionId })
})
await cdp.send('Page.startScreencast', { format: 'jpeg', quality: 92, maxWidth: 4000, maxHeight: 4000, everyNthFrame: 1 })
const started = Date.now() / 1000
const run = cdp.send('Runtime.evaluate', { expression: `(async () => { ${HELPERS}\n${clip.script} })()`, awaitPromise: true })
await new Promise(r => setTimeout(r, clip.seconds * 1000))
await cdp.send('Page.stopScreencast')
const result = await run
if (result.exceptionDetails) console.error('script error:', result.exceptionDetails.exception?.description)
cdp.close()
await fetch(`http://127.0.0.1:${PORT}/json/close/${target.id}`).catch(() => {})

// Constant 30 fps: frame k shows the newest screencast frame painted at or before k / 30 s
const t0 = Math.max(frames[0]?.t ?? started, started)
const total = Math.round(clip.seconds * FPS)
let j = 0
for (let k = 0; k < total; k++) {
  while (j + 1 < frames.length && frames[j + 1].t - t0 <= k / FPS) j++
  writeFileSync(`${dir}/s${String(k).padStart(5, '0')}.jpg`, Buffer.from(frames[j].data, 'base64'))
}
// Exactly 1920x1080 / 1080x1920 (the screencast can be a pixel larger)
const size = formatName === 'vertical' ? '1080:1920' : '1920:1080'
execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', `${dir}/s%05d.jpg`, '-vf', `scale=${size}:flags=lanczos`, '-q:v', '2', `${dir}/f%05d.jpg`])
for (let k = 0; k < total; k++) rmSync(`${dir}/s${String(k).padStart(5, '0')}.jpg`)
console.log(`${dir}: ${total} frames from ${frames.length} screencast frames`)

