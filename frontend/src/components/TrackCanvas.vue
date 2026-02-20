<template>
  <div class="track-container">
    <canvas
      ref="canvas"
      @click="handleCanvasClick"
    ></canvas>
  </div>
</template>

<script>
export default {
  name: 'TrackCanvas',
  props: {
    drivers: { type: Array, default: () => [] },
    circuitData: { type: Object, default: null },
    selectedDriver: { type: String, default: null }
  },
  emits: ['select-driver'],

  data() {
    return {
      ctx: null,
      scale: 1,
      offsetX: 0,
      offsetY: 0,
      canvasWidth: 1000,
      canvasHeight: 600
    }
  },

  mounted() {
    this.setupCanvas()
    this.draw()
  },

  watch: {
    drivers: {
      handler() {
        this.draw()
      },
      deep: true
    },
    circuitData() {
      this.draw()
    }
  },

  methods: {
    setupCanvas() {
      const canvas = this.$refs.canvas
      const container = canvas.parentElement
      
      this.canvasWidth = container.clientWidth
      this.canvasHeight = container.clientHeight
      
      canvas.width = this.canvasWidth
      canvas.height = this.canvasHeight
      
      this.ctx = canvas.getContext('2d')
    },

    draw() {
      if (!this.ctx) return
      
      // Clear
      this.ctx.fillStyle = '#0a0a0a'
      this.ctx.fillRect(0, 0, this.canvasWidth, this.canvasHeight)
      
      if (this.circuitData && this.circuitData.coordinates) {
        this.drawRealTrack()
      } else {
        this.drawGenericTrack()
      }
      
      this.drawDrivers()
    },

    drawRealTrack() {
      const coords = this.circuitData.coordinates
      if (coords.length === 0) return
      
      // Calculate bounds
      const xCoords = coords.map(c => c.x)
      const yCoords = coords.map(c => c.y)
      const minX = Math.min(...xCoords)
      const maxX = Math.max(...xCoords)
      const minY = Math.min(...yCoords)
      const maxY = Math.max(...yCoords)
      
      // Calculate scale to fit canvas
      const padding = 50
      const scaleX = (this.canvasWidth - 2 * padding) / (maxX - minX)
      const scaleY = (this.canvasHeight - 2 * padding) / (maxY - minY)
      this.scale = Math.min(scaleX, scaleY)
      
      this.offsetX = padding - minX * this.scale
      this.offsetY = padding - minY * this.scale
      
      // Draw track
      this.ctx.strokeStyle = '#333'
      this.ctx.lineWidth = 30
      this.ctx.lineCap = 'round'
      this.ctx.lineJoin = 'round'
      
      this.ctx.beginPath()
      coords.forEach((coord, i) => {
        const x = coord.x * this.scale + this.offsetX
        const y = coord.y * this.scale + this.offsetY
        
        if (i === 0) {
          this.ctx.moveTo(x, y)
        } else {
          this.ctx.lineTo(x, y)
        }
      })
      this.ctx.closePath()
      this.ctx.stroke()
      
      // Draw start/finish line
      const start = coords[0]
      const startX = start.x * this.scale + this.offsetX
      const startY = start.y * this.scale + this.offsetY
      
      this.ctx.fillStyle = '#fff'
      this.ctx.fillRect(startX - 3, startY - 20, 6, 40)
    },

    drawGenericTrack() {
      // Fallback generic track
      const centerX = this.canvasWidth / 2
      const centerY = this.canvasHeight / 2
      const radiusX = 350
      const radiusY = 200
      
      this.ctx.strokeStyle = '#333'
      this.ctx.lineWidth = 40
      this.ctx.beginPath()
      
      for (let i = 0; i <= 100; i++) {
        const angle = (i / 100) * Math.PI * 2
        const x = centerX + Math.cos(angle) * radiusX
        const y = centerY + Math.sin(angle) * radiusY
        
        if (i === 0) this.ctx.moveTo(x, y)
        else this.ctx.lineTo(x, y)
      }
      
      this.ctx.closePath()
      this.ctx.stroke()
    },

    drawDrivers() {
      if (!this.drivers || this.drivers.length === 0) return
      
      this.drivers.forEach(driver => {
        const position = this.getDriverPosition(driver)
        if (!position) return
        
        const isSelected = this.selectedDriver === driver.driver
        
        // Draw driver dot
        this.ctx.beginPath()
        this.ctx.arc(position.x, position.y, isSelected ? 10 : 7, 0, Math.PI * 2)
        this.ctx.fillStyle = this.getTeamColor(driver.team)
        this.ctx.fill()
        
        if (isSelected) {
          this.ctx.strokeStyle = '#fff'
          this.ctx.lineWidth = 3
          this.ctx.stroke()
        }
        
        // Draw driver code
        this.ctx.fillStyle = '#fff'
        this.ctx.font = 'bold 11px monospace'
        this.ctx.textAlign = 'center'
        this.ctx.fillText(driver.driver, position.x, position.y - 15)
      })
    },

    getDriverPosition(driver) {
      if (this.circuitData && this.circuitData.coordinates) {
        // Use real lap distance
        const coords = this.circuitData.coordinates
        const totalDistance = this.circuitData.total_distance
        
        if (!driver.distance || totalDistance === 0) {
          return this.getPositionFromOrder(driver)
        }
        
        // Find closest point on track based on distance
        const targetDistance = driver.distance % totalDistance
        let closestCoord = coords[0]
        let minDiff = Math.abs(coords[0].distance - targetDistance)
        
        for (const coord of coords) {
          const diff = Math.abs(coord.distance - targetDistance)
          if (diff < minDiff) {
            minDiff = diff
            closestCoord = coord
          }
        }
        
        return {
          x: closestCoord.x * this.scale + this.offsetX,
          y: closestCoord.y * this.scale + this.offsetY
        }
      }
      
      return this.getPositionFromOrder(driver)
    },

    getPositionFromOrder(driver) {
      // Fallback: spread drivers based on position
      const angle = (driver.position / 20) * Math.PI * 2
      const centerX = this.canvasWidth / 2
      const centerY = this.canvasHeight / 2
      const radiusX = 350
      const radiusY = 200
      
      return {
        x: centerX + Math.cos(angle) * radiusX,
        y: centerY + Math.sin(angle) * radiusY
      }
    },

    getTeamColor(team) {
      const colors = {
        'Red Bull Racing': '#3671C6',
        'Ferrari': '#E8002D',
        'Mercedes': '#27F4D2',
        'McLaren': '#FF8000',
        'Aston Martin': '#229971',
        'Alpine': '#FF87BC',
        'Williams': '#64C4FF',
        'RB': '#6692FF',
        'Kick Sauber': '#52E252',
        'Haas F1 Team': '#B6BABD'
      }
      return colors[team] || '#fff'
    },

    handleCanvasClick(event) {
      const rect = this.$refs.canvas.getBoundingClientRect()
      const x = event.clientX - rect.left
      const y = event.clientY - rect.top
      
      for (const driver of this.drivers) {
        const pos = this.getDriverPosition(driver)
        if (!pos) continue
        
        const distance = Math.sqrt(
          Math.pow(x - pos.x, 2) + Math.pow(y - pos.y, 2)
        )
        
        if (distance < 20) {
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
  background: #0a0a0a;
  border: 1px solid var(--color-border);
  overflow: hidden;
}

canvas {
  display: block;
  cursor: pointer;
  width: 100%;
  height: 100%;
}
</style>
