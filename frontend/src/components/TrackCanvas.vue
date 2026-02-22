<template>
  <div class="track-container" ref="container">
    <canvas
      ref="canvas"
      @click="handleCanvasClick"
      @wheel.prevent="handleWheel"
    ></canvas>

    <!-- Zoom controls overlay -->
    <div class="zoom-controls">
      <button class="zoom-btn" @click="zoomIn"  title="Zoom in">＋</button>
      <button class="zoom-btn" @click="zoomOut" title="Zoom out">－</button>
      <button class="zoom-btn reset" @click="resetZoom" title="Reset zoom">⊙</button>
      <span class="zoom-label">{{ Math.round(zoomLevel * 100) }}%</span>
    </div>
  </div>
</template>

<script>
const TEAM_COLORS = {
  'Red Bull Racing': '#3671C6',
  'Ferrari':         '#E8002D',
  'Mercedes':        '#27F4D2',
  'McLaren':         '#FF8000',
  'Aston Martin':    '#229971',
  'Alpine':          '#FF87BC',
  'Williams':        '#64C4FF',
  'RB':              '#6692FF',
  'Kick Sauber':     '#52E252',
  'Haas F1 Team':    '#B6BABD'
}

const MIN_ZOOM = 0.4
const MAX_ZOOM = 4.0
const ZOOM_STEP = 0.1

const DEFAULT_ANIM_MS = 800

export default {
  name: 'TrackCanvas',

  name: 'TrackCanvas',

  props: {
    drivers:        { type: Array,  default: () => [] },
    circuitData:    { type: Object, default: null },
    selectedDriver: { type: String, default: null },
    lapDuration:    { type: Number, default: 1000 }
  },

  emits: ['select-driver'],

  data() {
    return {
      ctx:          null,
      // base transform (fit-to-container, no zoom)
      baseScale:    1,
      baseOffsetX:  0,
      baseOffsetY:  0,
      // zoom state
      zoomLevel:    1.0,
      // canvas pixel size
      canvasWidth:  800,
      canvasHeight: 600,
      // track bounds (raw coords)
      trackMinX: 0, trackMaxX: 0,
      trackMinY: 0, trackMaxY: 0,
      resizeObserver: null,
      currentIndices:   {},
      targetIndices:    {},
      animStartIndices: {},
      animFrameId:      null,
      animStartTime:    null,
      animDuration:     DEFAULT_ANIM_MS
    }
  },

  computed: {
    // current effective scale & offsets after zoom
    scale()   { return this.baseScale   * this.zoomLevel },
    offsetX() {
      // keep track centered when zooming
      const trackCenterX = (this.trackMinX + this.trackMaxX) / 2
      return this.canvasWidth  / 2 - trackCenterX * this.scale
    },
    offsetY() {
      const trackCenterY = (this.trackMinY + this.trackMaxY) / 2
      return this.canvasHeight / 2 - trackCenterY * this.scale
    }
  },

  mounted() {
    this.setupCanvas()
    this.draw()

    // watch container resize
    this.resizeObserver = new ResizeObserver(() => {
      this.setupCanvas()
      this.draw()
    })
    this.resizeObserver.observe(this.$refs.container)
  },

  beforeUnmount() {
    this.resizeObserver?.disconnect()
    if (this.animFrameId) cancelAnimationFrame(this.animFrameId)
  },

  watch: {
    circuitData() {
      this.computeBaseTransform()
      this.currentIndices   = {}
      this.targetIndices    = {}
      this.animStartIndices = {}
      this.draw()
    },
    
    drivers: {
      deep: true,
      handler(newDrivers) {
        if (!this.circuitData?.coordinates?.length) {
          this.draw()
          return
        }

        const newTargets = {}
        newDrivers.forEach(d => {
          newTargets[d.driver] = this.computeTargetIndex(d)
        })

        newDrivers.forEach(d => {
          if (this.currentIndices[d.driver] == null) {
            this.currentIndices[d.driver]   = newTargets[d.driver]
            this.animStartIndices[d.driver] = newTargets[d.driver]
          }
        })

        this.targetIndices    = newTargets
        this.animStartIndices = { ...this.currentIndices }
        this.animDuration     = Math.min(DEFAULT_ANIM_MS, this.lapDuration * 0.8)

        if (this.animFrameId) cancelAnimationFrame(this.animFrameId)
        this.animStartTime = null
        this.animFrameId   = requestAnimationFrame(this.animStep)
      }
    },

    zoomLevel:   { handler() { this.draw() } }
  },

  methods: {
    // ── Canvas setup ──────────────────────────────────────────────────────────
    setupCanvas() {
      const container = this.$refs.container
      const canvas    = this.$refs.canvas

      this.canvasWidth  = container.clientWidth  || 800
      this.canvasHeight = container.clientHeight || 600

      canvas.width  = this.canvasWidth
      canvas.height = this.canvasHeight

      this.ctx = canvas.getContext('2d')
      this.computeBaseTransform()
    },

    computeBaseTransform() {
      if (!this.circuitData?.coordinates?.length) return

      const coords = this.circuitData.coordinates
      const xs = coords.map(c => c.x)
      const ys = coords.map(c => c.y)

      this.trackMinX = Math.min(...xs)
      this.trackMaxX = Math.max(...xs)
      this.trackMinY = Math.min(...ys)
      this.trackMaxY = Math.max(...ys)

      const padding = 60
      const scaleX  = (this.canvasWidth  - 2 * padding) / (this.trackMaxX - this.trackMinX)
      const scaleY  = (this.canvasHeight - 2 * padding) / (this.trackMaxY - this.trackMinY)
      this.baseScale = Math.min(scaleX, scaleY)
    },

    animStep(timestamp) {
      if (!this.animStartTime) this.animStartTime = timestamp

      const elapsed = timestamp - this.animStartTime
      const t       = Math.min(elapsed / this.animDuration, 1)

      const eased = t < 0.5
        ? 4 * t * t * t
        : 1 - Math.pow(-2 * t + 2, 3) / 2

      const coords = this.circuitData?.coordinates
      if (coords?.length) {
        const total = coords.length
        Object.keys(this.targetIndices).forEach(code => {
          const from  = this.animStartIndices[code] ?? this.targetIndices[code]
          const to    = this.targetIndices[code]
          let delta   = to - from
          if (delta < -(total / 2)) delta += total
          if (delta >   total / 2)  delta -= total
          this.currentIndices[code] = ((from + delta * eased) % total + total) % total
        })
      }

      this.draw()

      if (t < 1) {
        this.animFrameId = requestAnimationFrame(this.animStep)
      } else {
        Object.keys(this.targetIndices).forEach(code => {
          this.currentIndices[code] = this.targetIndices[code]
        })
        this.animFrameId = null
        this.draw()
      }
    },

    // ── Draw ─────────────────────────────────────────────────────────────────
    draw() {
      if (!this.ctx) return

      this.ctx.clearRect(0, 0, this.canvasWidth, this.canvasHeight)
      this.ctx.fillStyle = '#0a0a0a'
      this.ctx.fillRect(0, 0, this.canvasWidth, this.canvasHeight)

      if (this.circuitData?.coordinates?.length) {
        this.drawRealTrack()
      } else {
        this.drawGenericTrack()
      }

      this.drawDrivers()
    },

    drawRealTrack() {
      const coords = this.circuitData.coordinates
      const sc     = this.scale
      const ox     = this.offsetX
      const oy     = this.offsetY

      // Shadow / glow under track
      this.ctx.shadowColor = 'rgba(255,255,255,0.04)'
      this.ctx.shadowBlur  = 12

      // Track fill (dark asphalt)
      this.ctx.strokeStyle = '#2a2a2a'
      this.ctx.lineWidth   = Math.max(16, 28 * this.zoomLevel)
      this.ctx.lineCap     = 'round'
      this.ctx.lineJoin    = 'round'

      this.ctx.beginPath()
      coords.forEach((c, i) => {
        const x = c.x * sc + ox
        const y = c.y * sc + oy
        i === 0 ? this.ctx.moveTo(x, y) : this.ctx.lineTo(x, y)
      })
      this.ctx.closePath()
      this.ctx.stroke()

      // Track edge highlight
      this.ctx.shadowBlur  = 0
      this.ctx.strokeStyle = '#3d3d3d'
      this.ctx.lineWidth   = Math.max(18, 30 * this.zoomLevel)

      this.ctx.beginPath()
      coords.forEach((c, i) => {
        const x = c.x * sc + ox
        const y = c.y * sc + oy
        i === 0 ? this.ctx.moveTo(x, y) : this.ctx.lineTo(x, y)
      })
      this.ctx.closePath()
      this.ctx.stroke()

      // Track surface
      this.ctx.strokeStyle = '#1e1e1e'
      this.ctx.lineWidth   = Math.max(14, 24 * this.zoomLevel)

      this.ctx.beginPath()
      coords.forEach((c, i) => {
        const x = c.x * sc + ox
        const y = c.y * sc + oy
        i === 0 ? this.ctx.moveTo(x, y) : this.ctx.lineTo(x, y)
      })
      this.ctx.closePath()
      this.ctx.stroke()

      this.ctx.strokeStyle = 'rgba(255,255,255,0.045)'
      this.ctx.lineWidth   = Math.max(1, 1.5 * this.zoomLevel)
      this.ctx.setLineDash([8 * this.zoomLevel, 16 * this.zoomLevel])
      this.ctx.beginPath()
      coords.forEach((c, i) => {
        const x = c.x * sc + ox
        const y = c.y * sc + oy
        i === 0 ? this.ctx.moveTo(x, y) : this.ctx.lineTo(x, y)
      })
      this.ctx.stroke()
      this.ctx.setLineDash([])

      // Start / Finish line
      if (coords.length >= 2) {
        const s1 = coords[0]
        const s2 = coords[1]
        const x1 = s1.x * sc + ox
        const y1 = s1.y * sc + oy
        const x2 = s2.x * sc + ox
        const y2 = s2.y * sc + oy

        const dx  = x2 - x1
        const dy  = y2 - y1
        const len = Math.sqrt(dx * dx + dy * dy) || 1

        const nx = -dy / len
        const ny =  dx / len

        const halfW = Math.max(10, 16 * this.zoomLevel)

        this.ctx.shadowBlur  = 0
        this.ctx.strokeStyle = '#ffffff'
        this.ctx.lineWidth   = Math.max(2, 3 * this.zoomLevel)
        this.ctx.lineCap     = 'butt'
        this.ctx.beginPath()
        this.ctx.moveTo(x1 + nx * halfW, y1 + ny * halfW)
        this.ctx.lineTo(x1 - nx * halfW, y1 - ny * halfW)
        this.ctx.stroke()

        this.ctx.strokeStyle = '#e10600'
        this.ctx.beginPath()
        this.ctx.moveTo(x1, y1)
        this.ctx.lineTo(x1 - nx * halfW, y1 - ny * halfW)
        this.ctx.stroke()
      }
    },

    drawGenericTrack() {
      const cx = this.canvasWidth  / 2
      const cy = this.canvasHeight / 2
      const rx = (this.canvasWidth  / 2 - 60) * this.zoomLevel
      const ry = (this.canvasHeight / 2 - 60) * this.zoomLevel

      this.ctx.strokeStyle = '#2a2a2a'
      this.ctx.lineWidth   = 30 * this.zoomLevel
      this.ctx.beginPath()
      for (let i = 0; i <= 100; i++) {
        const angle = (i / 100) * Math.PI * 2
        const x = cx + Math.cos(angle) * rx
        const y = cy + Math.sin(angle) * ry
        i === 0 ? this.ctx.moveTo(x, y) : this.ctx.lineTo(x, y)
      }
      this.ctx.closePath()
      this.ctx.stroke()
    },

    drawDrivers() {
      if (!this.drivers?.length) return

      const dotR       = Math.max(6, 7 * Math.sqrt(this.zoomLevel))
      const selR       = dotR + 3
      const showLabels = this.zoomLevel >= 0.65   // CHANGE: was 0.7

      this.drivers.forEach(driver => {
        const pos = this.getDriverCanvasPos(driver)   
        if (!pos) return

        const isSel  = this.selectedDriver === driver.driver
        const isTop3 = driver.position <= 3
        const color  = this.getTeamColor(driver.team)

        if (isSel) {
          this.ctx.shadowColor = color
          this.ctx.shadowBlur  = 16   // CHANGE: was 14
        }

        this.ctx.beginPath()
        this.ctx.arc(pos.x, pos.y, isSel ? selR : dotR, 0, Math.PI * 2)
        this.ctx.fillStyle = color
        this.ctx.fill()

        if (isSel) {
          this.ctx.strokeStyle = '#ffffff'
          this.ctx.lineWidth   = 2.5
          this.ctx.stroke()
        }

        this.ctx.shadowBlur = 0   // CHANGE: moved outside the if block

        const showLabel = isSel || isTop3 || this.zoomLevel >= 1.5
        if (showLabel && showLabels) {
          const fs   = Math.max(9, 10 * Math.sqrt(this.zoomLevel))
          const yOff = (isSel ? selR : dotR) + 5   // CHANGE: dynamic based on dot size

          this.ctx.font      = `bold ${fs}px monospace`
          this.ctx.textAlign = 'center'

          this.ctx.fillStyle = 'rgba(0,0,0,0.85)'
          this.ctx.fillText(driver.driver, pos.x + 1, pos.y - yOff + 1)

          this.ctx.fillStyle = isSel ? '#ffffff' : (isTop3 ? '#ffd700' : '#cccccc')
          this.ctx.fillText(driver.driver, pos.x, pos.y - yOff)
        }
      })

      this.ctx.shadowBlur = 0
    },

    // REPLACE getDriverPosition with getDriverCanvasPos (new name + interpolation):
    getDriverCanvasPos(driver) {
      const coords = this.circuitData?.coordinates
      if (coords?.length) {
        const idx = this.currentIndices[driver.driver]
        if (idx == null) return null

        const total = coords.length
        const i0    = Math.floor(idx) % total
        const i1    = (i0 + 1) % total
        const frac  = idx - Math.floor(idx)
        const c0    = coords[i0]
        const c1    = coords[i1]
        return {
          x: (c0.x + (c1.x - c0.x) * frac) * this.scale + this.offsetX,
          y: (c0.y + (c1.y - c0.y) * frac) * this.scale + this.offsetY
        }
      }
      return this.getPositionFromOrder(driver)
    },

    // ADD new computeTargetIndex method:
    computeTargetIndex(driver) {
      const coords = this.circuitData?.coordinates
      if (!coords?.length) return 0
      const total       = coords.length
      const spacing     = Math.max(1, Math.floor(total * 0.025))
      const leaderStart = Math.floor(total * 0.10)
      const pos         = (driver.position ?? 1) - 1
      return (leaderStart + pos * spacing) % total
    },

    // REPLACE getPositionFromOrder — remove the circuit branch (handled above now):
    getPositionFromOrder(driver) {
      const angle = (((driver.position ?? 1) - 1) / 20) * Math.PI * 2
      const cx    = this.canvasWidth  / 2
      const cy    = this.canvasHeight / 2
      return {
        x: cx + Math.cos(angle) * (this.canvasWidth  / 2 - 80),
        y: cy + Math.sin(angle) * (this.canvasHeight / 2 - 80)
      }
    },

    getTeamColor(team) { return TEAM_COLORS[team] || '#aaa' },

    // ── Zoom ─────────────────────────────────────────────────────────────────
    zoomIn()    { this.zoomLevel = Math.min(MAX_ZOOM, +(this.zoomLevel + ZOOM_STEP).toFixed(2)) },
    zoomOut()   { this.zoomLevel = Math.max(MIN_ZOOM, +(this.zoomLevel - ZOOM_STEP).toFixed(2)) },
    resetZoom() { this.zoomLevel = 1.0 },

    handleWheel(e) {
      const delta = e.deltaY < 0 ? ZOOM_STEP : -ZOOM_STEP
      this.zoomLevel = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, +(this.zoomLevel + delta).toFixed(2)))
    },

    // ── Click ────────────────────────────────────────────────────────────────
    handleCanvasClick(e) {
      const rect = this.$refs.canvas.getBoundingClientRect()
      const x    = e.clientX - rect.left
      const y    = e.clientY - rect.top
      const hitR = Math.max(16, 20 * Math.sqrt(this.zoomLevel))

      for (const driver of this.drivers) {
        const pos = this.getDriverCanvasPos(driver)
        if (!pos) continue
        const dist = Math.hypot(x - pos.x, y - pos.y)
        if (dist < hitR) {
          this.$emit('select-driver', driver.driver)
          return
        }
      }

      this.$emit('select-driver', null)
    }
  }
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
  font-size: 1rem;
  line-height: 1;
  cursor: pointer;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
  padding: 0;
}

.zoom-btn:hover {
  background: rgba(40, 40, 40, 0.95);
  border-color: #666;
  color: #fff;
}

.zoom-btn.reset {
  font-size: 0.85rem;
}

.zoom-label {
  font-size: 0.65rem;
  color: #555;
  font-family: monospace;
  margin-top: 2px;
}
</style>