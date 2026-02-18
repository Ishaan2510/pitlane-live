import axios from 'axios'

const API_BASE = 'http://localhost:5000/api'

class APIService {
  async getRaces() {
    const response = await axios.get(`${API_BASE}/races`)
    return response.data
  }

  async getLiveRace(id) {
    const response = await axios.get(`${API_BASE}/races/${id}`)
    // Transform to match frontend expectations
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
}

export default new APIService()
