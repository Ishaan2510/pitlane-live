// Reading race/tyre_model.json (pipeline/model/MODEL.md). The model's lap time is
//   driver_base + fuel * lap + tyreEffect(compound, tyre age)
// and this file is the one place the tyre part is evaluated.

/**
 * Seconds a compound costs at a tyre age, against a new set of the reference compound:
 *   offset + deg * age + quad * age^2
 * `c` is an entry of tyre_model.json `compounds`. Past the oldest tyre seen in the race
 * a curved compound carries on in a straight line at the slope it had there (never less
 * than its linear rate), so an extrapolated stint cannot run away or bend back down.
 */
export function tyreEffect(c, age) {
  const q = c.quad_s_per_lap2 || 0
  const max = c.max_life_seen
  if (!q || age <= max) return c.offset_s + c.deg_s_per_lap * age + q * age * age
  const slope = Math.max(c.deg_s_per_lap + 2 * q * max, c.deg_s_per_lap)
  return c.offset_s + c.deg_s_per_lap * max + q * max * max + slope * (age - max)
}

// Why a race cannot be simulated, or null when it can. A race with wet running is
// refused even when its dry laps were fitted: the switch to slicks decides those races.
export function notSimulable(model) {
  if (!model) return 'No tyre model has been built for this race yet.'
  if (!model.modelled) return `There is no tyre model for this race: ${model.reason}.`
  if (model.wet_running) {
    return `Intermediate or wet tyres were used on ${Math.round(model.wet_share * 100)}% of the laps. When to switch to slicks decides a race like this, and the model knows nothing about a drying track.`
  }
  return null
}

const LEVELS = ['low', 'medium', 'high']

// The lowest of some confidence levels ('high' when there are none)
export function lowestConfidence(levels) {
  return LEVELS[Math.min(2, ...levels.map(l => LEVELS.indexOf(l)))] || 'low'
}
