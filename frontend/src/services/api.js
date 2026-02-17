// Mock data — will be replaced with real API calls

export const mockRaces = [
  {
    id: 1, name: 'Bahrain Grand Prix',
    circuit: 'Bahrain International Circuit',
    date: '2025-03-15', status: 'upcoming', country: '🇧🇭', laps: 57
  },
  {
    id: 2, name: 'Saudi Arabian Grand Prix',
    circuit: 'Jeddah Corniche Circuit',
    date: '2025-03-22', status: 'upcoming', country: '🇸🇦', laps: 50
  },
  {
    id: 3, name: 'Australian Grand Prix',
    circuit: 'Albert Park Circuit',
    date: '2025-04-06', status: 'live', country: '🇦🇺', laps: 58, currentLap: 23
  }
]

export const mockLiveRaceData = {
  id: 3, name: 'Australian Grand Prix',
  circuit: 'Albert Park Circuit', status: 'live',
  currentLap: 23, totalLaps: 58,
  leaders: [
    { position: 1, driver: 'Max Verstappen', team: 'Red Bull Racing',
      gap: 'LEADER', tireAge: 12, tireCompound: 'MEDIUM', lastPitLap: 11 },
    { position: 2, driver: 'Charles Leclerc', team: 'Ferrari',
      gap: '+3.2s', tireAge: 15, tireCompound: 'HARD', lastPitLap: 8 },
    { position: 3, driver: 'Lewis Hamilton', team: 'Mercedes',
      gap: '+5.8s', tireAge: 10, tireCompound: 'MEDIUM', lastPitLap: 13 }
  ]
}

export const mockLeaderboard = [
  { rank: 1, username: 'StrategyKing',   totalPoints: 4520, accuracy: 87.3, predictionsCount: 142 },
  { rank: 2, username: 'F1Prophet',      totalPoints: 4385, accuracy: 84.1, predictionsCount: 156 },
  { rank: 3, username: 'PitStopMaster',  totalPoints: 4210, accuracy: 82.5, predictionsCount: 138 },
  { rank: 4, username: 'TireWhisperer', totalPoints: 3995, accuracy: 79.8, predictionsCount: 145 },
  { rank: 5, username: 'RaceStrategist', totalPoints: 3870, accuracy: 78.2, predictionsCount: 129 }
]

class APIService {
  async getRaces()               { await delay(500);  return mockRaces }
  async getLiveRace(id)          { await delay(300);  return mockLiveRaceData }
  async getLeaderboard()         { await delay(400);  return mockLeaderboard }
  async submitPrediction(pred)   {
    await delay(200)
    console.log('Prediction submitted:', pred)
    return { success: true, points: Math.floor(Math.random() * 100) + 50 }
  }
}

function delay(ms) { return new Promise(r => setTimeout(r, ms)) }
export default new APIService()
