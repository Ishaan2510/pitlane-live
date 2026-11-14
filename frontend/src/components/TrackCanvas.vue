<template>
  <div class="track-container" ref="container">
    <canvas
      ref="canvas"
      role="img"
      aria-label="Track map with the cars at their current positions"
      @click="handleCanvasClick"
      @wheel.prevent="handleWheel"
    ></canvas>

    <!-- Zoom controls overlay -->
    <div class="zoom-controls">
      <button class="zoom-btn" type="button" @click="zoomIn" aria-label="Zoom in">
        <svg viewBox="0 0 12 12" aria-hidden="true"><path d="M6 2v8M2 6h8" /></svg>
      </button>
      <button class="zoom-btn" type="button" @click="zoomOut" aria-label="Zoom out">
        <svg viewBox="0 0 12 12" aria-hidden="true"><path d="M2 6h8" /></svg>
      </button>
      <button class="zoom-btn" type="button" @click="resetZoom" aria-label="Reset zoom">
        <svg viewBox="0 0 12 12" aria-hidden="true"><circle cx="6" cy="6" r="3.5" /><path d="M6 1v2M6 9v2M1 6h2M9 6h2" /></svg>
      </button>
      <span class="zoom-label">{{ Math.round(zoomLevel * 100) }}%</span>
    </div>
  </div>
</template>

<script>
// Draws the circuit and the cars. It does not decide where the cars are: the parent
// passes raceClock.stateAt() to setCars() every frame, and a car sits at
// fraction * total_distance along circuit.json's outline (one point every 10 m).

const MIN_ZOOM = 0.4
const MAX_ZOOM = 4.0
const ZOOM_STEP = 0.1
const FADE_S = 120        // race seconds a stopped car takes to fade out
const MAX_DPR = 2

export default {
  name: 'TrackCanvas',

  props: {
    circuitData:    { type: Object, default: null },
    selectedDriver: { type: String, default: null },
    pinnedDriver:   { type: String, default: null },
  },

  emits: ['select-driver'],
  expose: ['setCars'],

  data() {
    return {
      zoomLevel:    1.0,
      canvasWidth:  800,
      canvasHeight: 600,
    }
  },

  created() {
    // Not reactive on purpose: these change every frame
    this.ctx = null
    this.cars = []
    this.baseScale = 1
    this.scale = 1          // baseScale * zoom, and the offsets that keep the track centred
    this.offsetX = 0
    this.offsetY = 0
    this.bounds = { minX: 0, maxX: 0, minY: 0, maxY: 0 }
    this.resizeObserver = null
  },

  mounted() {
    this.setupCanvas()
    this.draw()
    this.resizeObserver = new ResizeObserver(() => {
      this.setupCanvas()
      this.draw()
    })
    this.resizeObserver.observe(this.$refs.container)
  },

  beforeUnmount() {
    this.resizeObserver?.disconnect()
  },

  watch: {
    circuitData()    { this.computeBaseTransform(); this.draw() },
    zoomLevel()      { this.draw() },
    selectedDriver() { this.draw() },
    pinnedDriver()   { this.draw() },
  },

  methods: {
    // Called by the parent with raceClock.stateAt(t), every animation frame
    setCars(cars) {
      this.cars = cars || []
      this.draw()
    },

    // ── Canvas setup ──────────────────────────────────────────────────────────
    setupCanvas() {
      const container = this.$refs.container
      const canvas    = this.$refs.canvas
      if (!container || !canvas) return

      this.canvasWidth  = container.clientWidth  || 800
      this.canvasHeight = container.clientHeight || 600

      const dpr = Math.min(window.devicePixelRatio || 1, MAX_DPR)
      canvas.width  = Math.round(this.canvasWidth * dpr)
      canvas.height = Math.round(this.canvasHeight * dpr)

      this.ctx = canvas.getContext('2d')
      this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      this.computeBaseTransform()
    },

    computeBaseTransform() {
      const coords = this.circuitData?.points
      if (!coords?.length) return
      let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity
      for (const c of coords) {
        if (c.x < minX) minX = c.x
        if (c.x > maxX) maxX = c.x
        if (c.y < minY) minY = c.y
        if (c.y > maxY) maxY = c.y
      }
      this.bounds = { minX, maxX, minY, maxY }
      const padding = Math.min(60, this.canvasWidth * 0.1)
      const scaleX  = (this.canvasWidth  - 2 * padding) / (maxX - minX)
      const scaleY  = (this.canvasHeight - 2 * padding) / (maxY - minY)
      this.baseScale = Math.min(scaleX, scaleY)
    },

    updateTransform() {
      this.scale   = this.baseScale * this.zoomLevel
      this.offsetX = this.canvasWidth  / 2 - (this.bounds.minX + this.bounds.maxX) / 2 * this.scale
      this.offsetY = this.canvasHeight / 2 - (this.bounds.minY + this.bounds.maxY) / 2 * this.scale
    },

    // ── Draw ─────────────────────────────────────────────────────────────────
    draw() {
      const ctx = this.ctx
      if (!ctx) return
      this.updateTransform()

      ctx.fillStyle = '#0a0a0a'
      ctx.fillRect(0, 0, this.canvasWidth, this.canvasHeight)

      if (this.circuitData?.points?.length) this.drawRealTrack()
      else this.drawGenericTrack()

      this.drawCars()
    },

    tracePath() {
      const coords = this.circuitData.points
      const sc = this.scale, ox = this.offsetX, oy = this.offsetY
      this.ctx.beginPath()
      for (let i = 0; i < coords.length; i++) {
        const x = coords[i].x * sc + ox
        const y = coords[i].y * sc + oy
        i === 0 ? this.ctx.moveTo(x, y) : this.ctx.lineTo(x, y)
      }
    },

    drawRealTrack() {
      const ctx = this.ctx
      const coords = this.circuitData.points
      const sc = this.scale, ox = this.offsetX, oy = this.offsetY
      const z = this.zoomLevel

      ctx.lineCap  = 'round'
      ctx.lineJoin = 'round'

      // Track edge highlight
      ctx.strokeStyle = '#3d3d3d'
      ctx.lineWidth   = Math.max(18, 30 * z)
      this.tracePath(); ctx.closePath(); ctx.stroke()

      // Track surface
      ctx.strokeStyle = '#1e1e1e'
      ctx.lineWidth   = Math.max(14, 24 * z)
      this.tracePath(); ctx.closePath(); ctx.stroke()

      // Centre line
      ctx.strokeStyle = 'rgba(255,255,255,0.045)'
      ctx.lineWidth   = Math.max(1, 1.5 * z)
      ctx.setLineDash([8 * z, 16 * z])
      this.tracePath(); ctx.stroke()
      ctx.setLineDash([])

      // Start / Finish line
      if (coords.length >= 2) {
        const x1 = coords[0].x * sc + ox, y1 = coords[0].y * sc + oy
        const x2 = coords[1].x * sc + ox, y2 = coords[1].y * sc + oy
        const dx = x2 - x1, dy = y2 - y1
        const len = Math.hypot(dx, dy) || 1
        const nx = -dy / len, ny = dx / len
        const halfW = Math.max(10, 16 * z)

        ctx.strokeStyle = '#ffffff'
        ctx.lineWidth   = Math.max(2, 3 * z)
        ctx.lineCap     = 'butt'
        ctx.beginPath()
        ctx.moveTo(x1 + nx * halfW, y1 + ny * halfW)
        ctx.lineTo(x1 - nx * halfW, y1 - ny * halfW)
        ctx.stroke()

        ctx.strokeStyle = '#e10600'
        ctx.beginPath()
        ctx.moveTo(x1, y1)
        ctx.lineTo(x1 - nx * halfW, y1 - ny * halfW)
        ctx.stroke()
      }
    },

    drawGenericTrack() {
      const ctx = this.ctx
      const cx = this.canvasWidth / 2, cy = this.canvasHeight / 2
      const rx = Math.max(20, this.canvasWidth  / 2 - 60) * this.zoomLevel
      const ry = Math.max(20, this.canvasHeight / 2 - 60) * this.zoomLevel
      ctx.strokeStyle = '#2a2a2a'
      ctx.lineWidth   = 30 * this.zoomLevel
      ctx.beginPath()
      ctx.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2)
      ctx.stroke()
    },

    // Canvas position of a car, or null when there is nothing to draw
    carPos(car) {
      const coords = this.circuitData?.points
      if (!coords?.length) {
        // no circuit file: the same fraction round a plain oval
        const angle = car.fraction * Math.PI * 2 - Math.PI / 2
        return {
          x: this.canvasWidth  / 2 + Math.cos(angle) * Math.max(20, this.canvasWidth  / 2 - 60) * this.zoomLevel,
          y: this.canvasHeight / 2 + Math.sin(angle) * Math.max(20, this.canvasHeight / 2 - 60) * this.zoomLevel,
          nx: 0, ny: 0,
        }
      }
      const total = coords.length
      const idx = (car.fraction % 1) * total
      const i0 = Math.floor(idx) % total
      const i1 = (i0 + 1) % total
      const f  = idx - Math.floor(idx)
      const c0 = coords[i0], c1 = coords[i1]
      const dx = c1.x - c0.x, dy = c1.y - c0.y
      const len = Math.hypot(dx, dy) || 1
      return {
        x: (c0.x + dx * f) * this.scale + this.offsetX,
        y: (c0.y + dy * f) * this.scale + this.offsetY,
        nx: -dy / len, ny: dx / len,     // unit normal, to set pit-lane cars beside the track
      }
    },

    carAlpha(car) {
      if (car.retired)  return Math.max(0, 1 - car.stoppedFor / FADE_S)
      if (car.finished) return Math.max(0.35, 1 - car.stoppedFor / FADE_S)
      return 1
    },

    drawCars() {
      const ctx = this.ctx
      if (!this.cars.length) return

      const z          = this.zoomLevel
      const dotR       = Math.max(5, 7 * Math.sqrt(z))
      const selR       = dotR + 3
      const pitOffset  = Math.max(14, 20 * z)
      const showLabels = z >= 0.65

      // Leader last, so it is drawn on top
      for (let i = this.cars.length - 1; i >= 0; i--) {
        const car = this.cars[i]
        const alpha = this.carAlpha(car)
        if (alpha <= 0) continue
        const pos = this.carPos(car)
        if (!pos) continue

        let { x, y } = pos
        if (car.inPit) { x += pos.nx * pitOffset; y += pos.ny * pitOffset }

        const isSel = this.selectedDriver === car.driver
        const isPin = this.pinnedDriver === car.driver
        const r = isSel || isPin ? selR : dotR

        ctx.globalAlpha = alpha
        ctx.beginPath()
        ctx.arc(x, y, r, 0, Math.PI * 2)
        if (car.inPit) {
          // in the pit lane: a hollow ring beside the track
          ctx.fillStyle = '#0a0a0a'
          ctx.fill()
          ctx.strokeStyle = car.color
          ctx.lineWidth = 2
          ctx.stroke()
        } else {
          ctx.fillStyle = car.color
          ctx.fill()
        }
        if (isSel || isPin) {
          ctx.strokeStyle = '#ffffff'
          ctx.lineWidth   = 2
          if (isPin && !isSel) ctx.setLineDash([3, 3])
          ctx.beginPath()
          ctx.arc(x, y, r + 2, 0, Math.PI * 2)
          ctx.stroke()
          ctx.setLineDash([])
        }

        const showLabel = isSel || isPin || car.position <= 3 || z >= 1.5
        if (showLabel && showLabels) {
          const fs   = Math.max(9, 10 * Math.sqrt(z))
          const yOff = r + 6
          const text = car.inPit ? `${car.driver} PIT` : car.driver
          ctx.font      = `bold ${fs}px monospace`
          ctx.textAlign = 'center'
          ctx.fillStyle = 'rgba(0,0,0,0.85)'
          ctx.fillText(text, x + 1, y - yOff + 1)
          ctx.fillStyle = isSel || isPin ? '#ffffff' : car.position <= 3 ? '#ffd700' : '#cccccc'
          ctx.fillText(text, x, y - yOff)
        }
      }
      ctx.globalAlpha = 1
    },

    // ── Zoom ─────────────────────────────────────────────────────────────────
    zoomIn()    { this.zoomLevel = Math.min(MAX_ZOOM, +(this.zoomLevel + ZOOM_STEP).toFixed(2)) },
    zoomOut()   { this.zoomLevel = Math.max(MIN_ZOOM, +(this.zoomLevel - ZOOM_STEP).toFixed(2)) },
    resetZoom() { this.zoomLevel = 1.0 },

    handleWheel(e) {
      const delta = e.deltaY < 0 ? ZOOM_STEP : -ZOOM_STEP
      this.zoomLevel = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, +(this.zoomLevel + delta).toFixed(2)))
    },

    // ── Click: select the nearest car (shift-click pins it for comparison) ──────
    handleCanvasClick(e) {
      const rect = this.$refs.canvas.getBoundingClientRect()
      const x    = e.clientX - rect.left
      const y    = e.clientY - rect.top
      const hitR = Math.max(16, 20 * Math.sqrt(this.zoomLevel))
      const pitOffset = Math.max(14, 20 * this.zoomLevel)

      let best = null, bestDist = hitR
      for (const car of this.cars) {
        if (this.carAlpha(car) <= 0) continue
        const pos = this.carPos(car)
        const cx = pos.x + (car.inPit ? pos.nx * pitOffset : 0)
        const cy = pos.y + (car.inPit ? pos.ny * pitOffset : 0)
        const dist = Math.hypot(x - cx, y - cy)
        if (dist < bestDist) { best = car.driver; bestDist = dist }
      }
      this.$emit('select-driver', best, { pin: e.shiftKey })
    },
  },
}
</script>

<style scoped>
.track-container {
  position: relative;
  width: 100%;
  height: 100%;
  background: #0a0a0a;
  overflow: hidden;
}

canvas {
  display: block;
  width: 100%;
  height: 100%;
  cursor: crosshair;
}

/* ── Zoom controls ── */
.zoom-controls {
  position: absolute;
  top: 10px;
  right: 10px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  z-index: 10;
}

.zoom-btn {
  width: 30px;
  height: 30px;
  background: rgba(20, 20, 20, 0.9);
  border: 1px solid #333;
  color: #bbb;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: border-color var(--dur-fast) var(--ease), color var(--dur-fast) var(--ease), scale var(--dur-fast) var(--ease);
  padding: 0;
}
.zoom-btn svg { width: 12px; height: 12px; fill: none; stroke: currentColor; stroke-width: 1.4; stroke-linecap: round; }

.zoom-btn:hover {
  border-color: #666;
  color: #fff;
}

.zoom-label {
  font-size: 0.65rem;
  color: #777;
  font-family: monospace;
  margin-top: 2px;
}
</style>
