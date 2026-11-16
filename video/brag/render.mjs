// Renders composition.html frame by frame in headless Chrome (listening on port 9555),
// then muxes the frames with the soundtrack.
//
//   node video/brag/render.mjs <landscape|vertical> <out.mp4> [--stills 1.5,4,7.2] [--seconds 20]
//
// --stills: only write PNG stills at those times (to check layout), no video.
import { mkdirSync, writeFileSync, rmSync } from 'node:fs'
import { execFileSync } from 'node:child_process'
import { dirname, resolve } from 'node:path'
import { pathToFileURL } from 'node:url'

const [format, out, ...rest] = process.argv.slice(2)
const opt = k => { const i = rest.indexOf('--' + k); return i >= 0 ? rest[i + 1] : null }
const SECONDS = parseFloat(opt('seconds') || '20')
const FPS = 30
const W = format === 'vertical' ? 1080 : 1920, H = format === 'vertical' ? 1920 : 1080
const here = dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Z]:)/, '$1'))
const page = pathToFileURL(resolve(here, 'composition.html')).href + '?format=' + format
const music = resolve(here, '../music/lights-out.wav')

function connect(url) {
  return new Promise((resolveConn, reject) => {
    const ws = new WebSocket(url)
    let id = 0
    const pending = new Map()
    ws.onmessage = e => { const m = JSON.parse(e.data); if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); m.error ? p.reject(new Error(m.error.message)) : p.resolve(m.result) } }
    ws.onopen = () => resolveConn({ send: (method, params = {}) => new Promise((res, rej) => { pending.set(++id, { resolve: res, reject: rej }); ws.send(JSON.stringify({ id, method, params })) }), close: () => ws.close() })
    ws.onerror = reject
  })
}

const target = await (await fetch('http://127.0.0.1:9555/json/new?about:blank', { method: 'PUT' })).json()
const cdp = await connect(target.webSocketDebuggerUrl)
await cdp.send('Page.enable'); await cdp.send('Runtime.enable')
await cdp.send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 1, mobile: false })
await cdp.send('Page.navigate', { url: page })
await new Promise(r => setTimeout(r, 2500))
await cdp.send('Runtime.evaluate', { expression: 'window.ready', awaitPromise: true })

async function frameAt(t) {
  const r = await cdp.send('Runtime.evaluate', { expression: `window.setTime(${t})`, awaitPromise: true })
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text)
  await cdp.send('Runtime.evaluate', { expression: 'new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))', awaitPromise: true })
  return (await cdp.send('Page.captureScreenshot', { format: 'png' })).data
}

const stills = opt('stills')
if (stills) {
  mkdirSync(dirname(out), { recursive: true })
  for (const t of stills.split(',').map(Number)) {
    writeFileSync(out.replace(/\.png$/, '') + `-${format}-${t.toFixed(2)}.png`, Buffer.from(await frameAt(t), 'base64'))
  }
} else {
  const dir = resolve(dirname(out), 'work', 'frames-' + format)
  rmSync(dir, { recursive: true, force: true }); mkdirSync(dir, { recursive: true })
  const total = Math.round(SECONDS * FPS)
  const started = Date.now()
  for (let k = 0; k < total; k++) {
    writeFileSync(`${dir}/f${String(k).padStart(5, '0')}.png`, Buffer.from(await frameAt(k / FPS), 'base64'))
    if (k % 60 === 0) console.log(`frame ${k}/${total} (${((Date.now() - started) / 1000).toFixed(0)} s)`)
  }
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-framerate', String(FPS), '-i', `${dir}/f%05d.png`, '-i', music,
    '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-pix_fmt', 'yuv420p', '-r', String(FPS),
    '-c:a', 'aac', '-b:a', '256k', '-t', String(SECONDS), '-movflags', '+faststart', out])
  console.log('wrote', out)
}
cdp.close()
await fetch(`http://127.0.0.1:9555/json/close/${target.id}`).catch(() => {})
