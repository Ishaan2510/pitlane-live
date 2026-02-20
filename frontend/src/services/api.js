import axios from 'axios'

const API_BASE = 'http://localhost:5000/api'

class APIService {
  // ── Existing endpoints ──
  async getRaces() {
    const response = await axios.get(`${API_BASE}/races`)
    return response.data
  }

  async getLiveRace(id) {
    const response = await axios.get(`${API_BASE}/races/${id}`)
    return {
      id: response.data.id,
      name: response.data.name,
      circuit: response.data.circuit,
      country: response.data.country,
      status: response.data.status,
      currentLap: response.data.currentLap,
      totalLaps: response.data.laps,
      leaders: response.data.leaders || []
    }
  }

  async getLeaderboard() {
    const response = await axios.get(`${API_BASE}/leaderboard`)
    return response.data
  }

  async submitPrediction(prediction) {
    const response = await axios.post(`${API_BASE}/predictions`, prediction)
    return response.data
  }

  async getRacePredictions(raceId) {
    const response = await axios.get(`${API_BASE}/predictions/race/${raceId}`)
    return response.data
  }

  // ── Race Replay endpoints ──
  async getAvailableReplays(year = 2024) {
    const response = await axios.get(`${API_BASE}/replay/available?year=${year}`)
    return response.data
  }

  async getReplayRaceData(year, round) {
    const response = await axios.get(`${API_BASE}/replay/race/${year}/${round}`)
    return response.data
  }

  async getReplayLapData(year, round, lap) {
    const response = await axios.get(`${API_BASE}/replay/lap/${year}/${round}/${lap}`)
    return response.data
  }

  async getReplaySummary(year, round) {
    const response = await axios.get(`${API_BASE}/replay/summary/${year}/${round}`)
    return response.data
  }

  // ── NEW: Advanced replay endpoints ──
  async getCircuitData(year, round) {
    const response = await axios.get(`${API_BASE}/replay/circuit/${year}/${round}`)
    return response.data
  }

  async getWeatherData(year, round) {
    const response = await axios.get(`${API_BASE}/replay/weather/${year}/${round}`)
    return response.data
  }
}

export default new APIService()
