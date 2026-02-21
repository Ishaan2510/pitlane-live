<template>
  <div class="track-container">
    <canvas ref="canvas" @click="handleCanvasClick" />
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
  'Haas F1 Team':    '#B6BABD',
  'Kick Sauber':     '#52E252',
}

export default {
  name: 'TrackCanvas',
  props: {
    drivers:        { type: Array,  default: () => [] },
    circuitData:    { type: Object, default: null },
    selectedDriver: { type: String, default: null }
  },
  emits: ['select-driver'],

  data() {
    return {
      ctx:          null,
      scale:        1,
      offsetX:      0,
      offsetY:      0,
      canvasWidth:  1000,
      canvasHeight: 600,
      scaledCoords: []        // pre-computed canvas-space track points
    }
  },

  mounted() {
    this.setupCanvas()
    window.addEventListener('resize', this.onResize)
    this.draw()
  },

  beforeUnmount() {
    window.removeEventListener('resize', this.onResize)
  },

  watch: {
    drivers:     { handler() { this.draw() }, deep: true },
    circuitData: { handler() { this.draw() } }
  },

  methods: {
    onResize() { this.setupCanvas(); this.draw() },

    setupCanvas() {
      const canvas    = this.$refs.canvas
      const container = canvas.parentElement
      this.canvasWidth  = container.clientWidth  || 800
      this.canvasHeight = container.clientHeight || 500
      canvas.width  = this.canvasWidth
      canvas.height = this.canvasHeight
      this.ctx = canvas.getContext('2d')
    },

    // ── Main render ───────────────────────────────────────────────────────
    draw() {
      if (!this.ctx) return
      this.ctx.clearRect(0, 0, this.canvasWidth, this.canvasHeight)
      this.ctx.fillStyle = '#111'
      this.ctx.fillRect(0, 0, this.canvasWidth, this.canvasHeight)

      if (this.circuitData?.coordinates?.length) {
        this.drawRealTrack()
      } else {
        this.drawGenericTrack()
      }
      this.drawDrivers()
    },

    // ── Real circuit ──────────────────────────────────────────────────────
    drawRealTrack() {
      const coords  = this.circuitData.coordinates
      const padding = 70

      const xs = coords.map(c => c.x)
      const ys = coords.map(c => c.y)
      const minX = Math.min(...xs), maxX = Math.max(...xs)
      const minY = Math.min(...ys), maxY = Math.max(...ys)

      const scaleX = (this.canvasWidth  - padding * 2) / (maxX - minX || 1)
      const scaleY = (this.canvasHeight - padding * 2) / (maxY - minY || 1)
      this.scale   = Math.min(scaleX, scaleY)

      // Centre the circuit
      const trackW = (maxX - minX) * this.scale
      const trackH = (maxY - minY) * this.scale
      this.offsetX = (this.canvasWidth  - trackW) / 2 - minX * this.scale
      this.offsetY = (this.canvasHeight - trackH) / 2 - minY * this.scale

      this.scaledCoords = coords.map(c => ({
        x: c.x * this.scale + this.offsetX,
        y: c.y * this.scale + this.offsetY,
        distance: c.distance
      }))

      // Outer glow
      this.ctx.save()
      this.ctx.strokeStyle = 'rgba(80,80,80,0.12)'
      this.ctx.lineWidth   = 44
      this.ctx.lineCap     = 'round'
      this.ctx.lineJoin    = 'round'
      this._strokePath(this.scaledCoords)
      this.ctx.stroke()
      this.ctx.restore()

      // Main surface
      this.ctx.strokeStyle = '#2d2d2d'
      this.ctx.lineWidth   = 30
      this.ctx.lineCap     = 'round'
      this.ctx.lineJoin    = 'round'
      this._strokePath(this.scaledCoords)
      this.ctx.stroke()

      // Centre dashes
      this.ctx.strokeStyle = 'rgba(255,255,255,0.045)'
      this.ctx.lineWidth   = 1
      this.ctx.setLineDash([10, 12])
      this._strokePath(this.scaledCoords)
      this.ctx.stroke()
      this.ctx.setLineDash([])

      // Start / finish bar
      const s     = this.scaledCoords[0]
      const e     = this.scaledCoords[Math.min(6, this.scaledCoords.length - 1)]
      const angle = Math.atan2(e.y - s.y, e.x - s.x) + Math.PI / 2
      this.ctx.save()
      this.ctx.translate(s.x, s.y)
      this.ctx.rotate(angle)
      this.ctx.fillStyle = '#fff'
      this.ctx.fillRect(-3, -18, 6, 36)
      this.ctx.restore()
    },

    _strokePath(pts) {
      this.ctx.beginPath()
      pts.forEach((p, i) => {
        if (i === 0) this.ctx.moveTo(p.x, p.y)
        else         this.ctx.lineTo(p.x, p.y)
      })
      this.ctx.closePath()
    },

    // ── Generic oval fallback ─────────────────────────────────────────────
    drawGenericTrack() {
      this.scaledCoords = []
      const cx = this.canvasWidth  / 2
      const cy = this.canvasHeight / 2
      const rx = this.canvasWidth  * 0.38
      const ry = this.canvasHeight * 0.30
      this.ctx.strokeStyle = '#2d2d2d'
      this.ctx.lineWidth   = 30
      this.ctx.beginPath()
      this.ctx.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2)
      this.ctx.stroke()
    },

    // ── Drivers ───────────────────────────────────────────────────────────
    drawDrivers() {
      if (!this.drivers?.length) return

      // Draw back-to-front so P1 renders on top
      const sorted = [...this.drivers]
        .filter(d => d.position != null)
        .sort((a, b) => b.position - a.position)

      sorted.forEach(driver => {
        const pos        = this.getDriverPosition(driver)
        if (!pos) return
        const isSelected = this.selectedDriver === driver.driver
        const color      = this.getTeamColor(driver.team)
        // Small visual radius; click hit-box is handled separately (20px)
        const r          = isSelected ? 8 : 5

        // Selection glow ring
        if (isSelected) {
          this.ctx.beginPath()
          this.ctx.arc(pos.x, pos.y, r + 7, 0, Math.PI * 2)
          this.ctx.fillStyle = 'rgba(255,255,255,0.12)'
          this.ctx.fill()
        }

        // Driver dot
        this.ctx.beginPath()
        this.ctx.arc(pos.x, pos.y, r, 0, Math.PI * 2)
        this.ctx.fillStyle   = color
        this.ctx.strokeStyle = isSelected ? '#fff' : 'rgba(0,0,0,0.55)'
        this.ctx.lineWidth   = isSelected ? 2 : 1
        this.ctx.fill()
        this.ctx.stroke()

        // Labels: show only for P1-P5 or the selected driver
        const showLabel = isSelected || (driver.position && driver.position <= 5)
        if (showLabel) {
          const label  = driver.driver
          const fSize  = 10
          this.ctx.font = `bold ${fSize}px monospace`
          const tw     = this.ctx.measureText(label).width
          const lx     = pos.x - tw / 2
          const ly     = pos.y - r - 4

          // Label bg — use fillRect as roundRect fallback
          this.ctx.fillStyle = 'rgba(0,0,0,0.75)'
          this.ctx.beginPath()
          if (this.ctx.roundRect) {
            this.ctx.roundRect(lx - 3, ly - fSize, tw + 6, fSize + 3, 2)
          } else {
            this.ctx.rect(lx - 3, ly - fSize, tw + 6, fSize + 3)
          }
          this.ctx.fill()

          this.ctx.fillStyle    = isSelected ? '#fff' : '#ccc'
          this.ctx.textAlign    = 'left'
          this.ctx.textBaseline = 'alphabetic'
          this.ctx.fillText(label, lx, ly)
        }
      })
    },

    // ── Positioning ───────────────────────────────────────────────────────
    /**
     * Distribute drivers along the real circuit path based on their position.
     * P1 sits at index 0; every subsequent driver is spaced 80% / N further
     * along the path.  Tiny perpendicular jitter prevents perfect dot overlap
     * when many cars are very close together.
     */
    getDriverPosition(driver) {
      const coords = this.scaledCoords.length ? this.scaledCoords : null
      const n      = Math.max(this.drivers.length, 1)
      const pos    = (driver.position ?? 1) - 1   // 0-based

      if (coords) {
        // 80% spread so there's always a visible gap between 1st and last
        const fraction = (pos / n) * 0.80
        const idx      = Math.round(fraction * (coords.length - 1)) % coords.length
        const pt       = coords[idx]

        // Tiny lateral jitter: row within a group of 3 → -4px, 0px, +4px
        const jitter = ((pos % 3) - 1) * 4
        return { x: pt.x + jitter, y: pt.y + jitter }
      }

      // Fallback: oval
      return this.getPositionOnOval(driver)
    },

    getPositionOnOval(driver) {
      const n     = Math.max(this.drivers.length, 1)
      const pos   = (driver.position ?? 1) - 1
      const angle = -(pos / n) * Math.PI * 2
      const cx    = this.canvasWidth  / 2
      const cy    = this.canvasHeight / 2
      return {
        x: cx + Math.cos(angle) * this.canvasWidth  * 0.38,
        y: cy + Math.sin(angle) * this.canvasHeight * 0.30
      }
    },

    getTeamColor(team) {
      return TEAM_COLORS[team] || '#aaa'
    },

    // ── Click detection ───────────────────────────────────────────────────
    handleCanvasClick(event) {
      const rect = this.$refs.canvas.getBoundingClientRect()
      // Scale mouse coords to internal canvas resolution
      const mx = (event.clientX - rect.left)  * (this.canvasWidth  / rect.width)
      const my = (event.clientY - rect.top)   * (this.canvasHeight / rect.height)

      for (const driver of this.drivers) {
        const pos = this.getDriverPosition(driver)
        if (!pos) continue
        // Generous 20px hit-box regardless of visual dot size
        if (Math.hypot(mx - pos.x, my - pos.y) < 20) {
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
  width: 100%;
  height: 100%;
  flex: 1;
  min-height: 0;
  background: #111;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  overflow: hidden;
}
canvas {
  display: block;
  cursor: pointer;
  width: 100%;
  height: 100%;
}
</style>
