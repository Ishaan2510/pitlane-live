<template>
  <div class="how-to-play">

    <!-- ── Hero ── -->
    <div class="hero">
      <div class="hero-tag">Strategy HQ</div>
      <h1 class="hero-title">How to<br><span class="red">Compete</span></h1>
      <p class="hero-sub">PitLane Live is a real-time prediction contest. Every decision you make during a live race earns — or costs — you points on the global leaderboard.</p>
      <div class="hero-rule"></div>
    </div>

    <!-- ── Sections ── -->
    <div class="sections">

      <!-- THE BASICS -->
      <section class="block">
        <div class="block-num">01</div>
        <div class="block-content">
          <h2 class="block-title">The Basics</h2>
          <p class="block-desc">During a live race, you watch the timing tower, pick a driver, and predict what they'll do next — pit or stay out, and on which compound. The closer your prediction is to what actually happens, the more points you earn.</p>
          <div class="callout">
            <span class="callout-icon">🏁</span>
            <span>Think of it like placing a strategic call before your team principal does. Every lap counts.</span>
          </div>
        </div>
      </section>

      <!-- MAKING A PREDICTION -->
      <section class="block">
        <div class="block-num">02</div>
        <div class="block-content">
          <h2 class="block-title">Making a Prediction</h2>
          <div class="steps">
            <div class="step">
              <div class="step-dot"></div>
              <div class="step-body">
                <div class="step-title">Select a Driver</div>
                <div class="step-desc">Click any driver on the timing tower or the track map. Their card appears on the right — gap to leader, current tyre compound, and tyre age.</div>
              </div>
            </div>
            <div class="step">
              <div class="step-dot"></div>
              <div class="step-body">
                <div class="step-title">Choose an Action</div>
                <div class="step-desc">Four options: <span class="tag soft">PIT → SOFT</span> <span class="tag medium">PIT → MEDIUM</span> <span class="tag hard">PIT → HARD</span> <span class="tag stay">STAY OUT</span>. Pick what you think the team will do.</div>
              </div>
            </div>
            <div class="step">
              <div class="step-dot"></div>
              <div class="step-body">
                <div class="step-title">Set Your Lap Window</div>
                <div class="step-desc">Use the lap slider to predict <em>when</em> the action happens. Your prediction scores if the event occurs within <strong>±2 laps</strong> of your chosen lap — so a prediction on lap 28 covers laps 26–30.</div>
              </div>
            </div>
            <div class="step">
              <div class="step-dot"></div>
              <div class="step-body">
                <div class="step-title">Set Your Confidence</div>
                <div class="step-desc">Slide from 10% to 100%. Higher confidence = higher points if correct, higher penalty if wrong. Back yourself only when you're sure.</div>
              </div>
            </div>
            <div class="step last">
              <div class="step-dot red-dot"></div>
              <div class="step-body">
                <div class="step-title">Lock It In</div>
                <div class="step-desc">Hit <strong>Lock In Prediction</strong>. You can make multiple predictions across different drivers throughout the race.</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- LAP SLIDER EXPLAINED -->
      <section class="block">
        <div class="block-num">03</div>
        <div class="block-content">
          <h2 class="block-title">The Lap Slider</h2>
          <p class="block-desc">This is your timing call. Drag it to the lap you think the pit stop (or stay-out) happens on.</p>
          <div class="slider-demo">
            <div class="slider-track">
              <div class="slider-fill"></div>
              <div class="slider-thumb"></div>
            </div>
            <div class="slider-labels">
              <span>Lap 1</span>
              <span class="slider-current">Lap 28 ← your call</span>
              <span>Lap 57</span>
            </div>
          </div>
          <div class="window-explainer">
            <div class="window-row">
              <div class="window-cell miss">Lap 25</div>
              <div class="window-cell miss">Lap 26</div>
              <div class="window-cell hit">Lap 27</div>
              <div class="window-cell hit selected-lap">Lap 28 ★</div>
              <div class="window-cell hit">Lap 29</div>
              <div class="window-cell hit">Lap 30</div>
              <div class="window-cell miss">Lap 31</div>
            </div>
            <div class="window-legend">
              <span class="legend-hit">■ Scores (±2 window)</span>
              <span class="legend-miss">■ Miss</span>
            </div>
          </div>
        </div>
      </section>

      <!-- SCORING -->
      <section class="block">
        <div class="block-num">04</div>
        <div class="block-content">
          <h2 class="block-title">Scoring</h2>
          <p class="block-desc">Points are calculated after the race using the final lap data. Results appear on the leaderboard approximately <strong>1 hour after the chequered flag</strong> — FastF1 needs time to process the session data.</p>

          <div class="scoring-grid">
            <div class="score-card green">
              <div class="score-label">Correct action + within window</div>
              <div class="score-value">+ Points × Confidence</div>
              <div class="score-example">e.g. 100% confidence = maximum points</div>
            </div>
            <div class="score-card red">
              <div class="score-label">Wrong action or outside window</div>
              <div class="score-value">− Penalty × Confidence</div>
              <div class="score-example">e.g. 100% confidence = maximum penalty</div>
            </div>
            <div class="score-card neutral">
              <div class="score-label">No prediction made</div>
              <div class="score-value">0 Points</div>
              <div class="score-example">Safe, but you won't climb the leaderboard</div>
            </div>
          </div>

          <div class="callout yellow">
            <span class="callout-icon">⚠</span>
            <span>Results are <strong>not instant</strong>. After the race ends, scores update within ~1 hour. Check the Standings page after that.</span>
          </div>
        </div>
      </section>

      <!-- READING THE TIMING TOWER -->
      <section class="block">
        <div class="block-num">05</div>
        <div class="block-content">
          <h2 class="block-title">Reading the Timing Tower</h2>
          <div class="tower-demo">
            <div class="tower-header-demo">
              <span>P</span><span>DRIVER</span><span>GAP</span><span>TYRE</span>
            </div>
            <div class="tower-row-demo gold">
              <span>1</span>
              <div class="driver-cell"><span class="code">VER</span><span class="team" style="color:#3671C6">RBR</span></div>
              <span class="mono">—</span>
              <div class="tyre-cell"><span class="dot soft-dot"></span><span class="mono grey">3</span></div>
            </div>
            <div class="tower-row-demo silver">
              <span>2</span>
              <div class="driver-cell"><span class="code">NOR</span><span class="team" style="color:#FF8000">MCL</span></div>
              <span class="mono">+1.204</span>
              <div class="tyre-cell"><span class="dot medium-dot"></span><span class="mono grey">12</span></div>
            </div>
            <div class="tower-row-demo">
              <span>3</span>
              <div class="driver-cell"><span class="code">LEC</span><span class="team" style="color:#E8002D">FER</span></div>
              <span class="mono">+3.891</span>
              <div class="tyre-cell"><span class="dot hard-dot"></span><span class="mono grey">24</span></div>
            </div>
          </div>
          <div class="legend-list">
            <div class="legend-item"><span class="legend-key">P</span><span class="legend-val">Current race position</span></div>
            <div class="legend-item"><span class="legend-key">GAP</span><span class="legend-val">Time gap to the race leader</span></div>
            <div class="legend-item"><span class="legend-key tyre-legend"><span class="dot soft-dot"></span></span><span class="legend-val">Tyre compound — red=Soft, yellow=Medium, white=Hard</span></div>
            <div class="legend-item"><span class="legend-key mono">24</span><span class="legend-val">Tyre age in laps — higher = older, more likely to pit soon</span></div>
          </div>
        </div>
      </section>

      <!-- PRO TIPS -->
      <div class="tips">
        <div class="tip">
          <span class="tip-icon">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <circle cx="9" cy="9" r="7" stroke="#e10600" stroke-width="1.5"/>
              <path d="M9 5v4l2.5 2.5" stroke="#e10600" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
          </span>
          <div>
            <div class="tip-title">Watch tyre age</div>
            <div class="tip-desc">A soft tyre past lap 20 is almost always pitting soon. Use that number aggressively.</div>
          </div>
        </div>

        <div class="tip">
          <span class="tip-icon">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <rect x="2" y="10" width="3" height="6" rx="1" fill="#e10600"/>
              <rect x="7" y="6" width="3" height="10" rx="1" fill="#e10600" opacity="0.6"/>
              <rect x="12" y="2" width="3" height="14" rx="1" fill="#e10600" opacity="0.3"/>
            </svg>
          </span>
          <div>
            <div class="tip-title">Confidence is a lever</div>
            <div class="tip-desc">If you're 90% sure, go 90%. If you're guessing, go 30%. Don't bleed points on uncertain calls.</div>
          </div>
        </div>

        <div class="tip">
          <span class="tip-icon">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M2 9h3l2-5 3 9 2-4h4" stroke="#e10600" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </span>
          <div>
            <div class="tip-title">Volume beats perfection</div>
            <div class="tip-desc">More predictions across more drivers = more scoring opportunities per race.</div>
          </div>
        </div>

        <div class="tip">
          <span class="tip-icon">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M9 2L9 5M9 13L9 16M2 9L5 9M13 9L16 9" stroke="#e10600" stroke-width="1.5" stroke-linecap="round"/>
              <circle cx="9" cy="9" r="3" stroke="#e10600" stroke-width="1.5"/>
              <circle cx="9" cy="9" r="6" stroke="#e10600" stroke-width="1" opacity="0.3" stroke-dasharray="2 2"/>
            </svg>
          </span>
          <div>
            <div class="tip-title">Safety car changes everything</div>
            <div class="tip-desc">When the yellow banner appears, expect a wave of pit stops. Predict fast.</div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Bottom CTA ── -->
    <div class="cta-bar">
      <div class="cta-inner">
        <div class="cta-text">
          <div class="cta-title">Ready to race?</div>
          <div class="cta-sub">The live feed activates automatically on race day.</div>
        </div>
        <router-link to="/live" class="cta-btn">GO TO LIVE RACE →</router-link>
      </div>
    </div>

  </div>
</template>

<script>
export default {
  name: 'PitWall'
}
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Work+Sans:wght@400;500;600;700&display=swap');

.how-to-play {
  background: #080808;
  min-height: 100vh;
  color: #ccc;
  font-family: 'Work Sans', sans-serif;
}

/* ── Hero ── */
.hero {
  max-width: 720px;
  margin: 0 auto;
  padding: 4rem 2rem 3rem;
}
.hero-tag {
  font-size: 0.65rem;
  letter-spacing: 0.2em;
  color: #e10600;
  font-weight: 700;
  margin-bottom: 1rem;
}
.hero-title {
  font-family: 'Bebas Neue', sans-serif;
  font-size: clamp(3.5rem, 8vw, 6rem);
  line-height: 0.9;
  color: #fff;
  letter-spacing: 0.02em;
  margin: 0 0 1.5rem;
}
.hero-title .red { color: #e10600; }
.hero-sub {
  font-size: 1rem;
  color: #555;
  line-height: 1.75;
  max-width: 560px;
}
.hero-rule {
  width: 48px;
  height: 2px;
  background: #e10600;
  margin-top: 2.5rem;
}

/* ── Sections ── */
.sections {
  max-width: 720px;
  margin: 0 auto;
  padding: 0 2rem 4rem;
}
.block {
  display: grid;
  grid-template-columns: 48px 1fr;
  gap: 0 2rem;
  padding: 3rem 0;
  border-bottom: 1px solid #111;
}
.block-num {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 0.9rem;
  color: #1e1e1e;
  letter-spacing: 0.1em;
  padding-top: 0.4rem;
}
.block-title {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 1.8rem;
  color: #fff;
  letter-spacing: 0.05em;
  margin: 0 0 1rem;
}
.block-desc {
  font-size: 0.88rem;
  color: #555;
  line-height: 1.8;
  margin-bottom: 1.5rem;
}

.tip-icon {
  width: 36px;
  height: 36px;
  background: rgba(225,6,0,0.08);
  border: 1px solid rgba(225,6,0,0.15);
  border-radius: 2px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}


/* callout */
.callout {
  display: flex;
  gap: 0.75rem;
  align-items: flex-start;
  background: rgba(225,6,0,0.06);
  border: 1px solid rgba(225,6,0,0.15);
  border-left: 3px solid #e10600;
  padding: 0.85rem 1rem;
  font-size: 0.82rem;
  color: #666;
  line-height: 1.6;
  border-radius: 1px;
}
.callout.yellow {
  background: rgba(200,170,0,0.06);
  border-color: rgba(200,170,0,0.15);
  border-left-color: #ccaa00;
}
.callout-icon { font-size: 1rem; flex-shrink: 0; margin-top: 0.05rem; }

/* steps */
.steps { display: flex; flex-direction: column; gap: 0; }
.step {
  display: flex;
  gap: 1rem;
  padding-bottom: 1.5rem;
  position: relative;
}
.step:not(.last)::before {
  content: '';
  position: absolute;
  left: 5px;
  top: 14px;
  bottom: 0;
  width: 1px;
  background: #1a1a1a;
}
.step-dot {
  width: 11px; height: 11px;
  border-radius: 50%;
  background: #1e1e1e;
  border: 1px solid #333;
  flex-shrink: 0;
  margin-top: 0.3rem;
  position: relative;
  z-index: 1;
}
.red-dot { background: #e10600; border-color: #e10600; }
.step-title {
  font-size: 0.82rem;
  font-weight: 700;
  color: #ddd;
  margin-bottom: 0.3rem;
  letter-spacing: 0.02em;
}
.step-desc { font-size: 0.8rem; color: #555; line-height: 1.7; }

/* compound tags */
.tag {
  display: inline-block;
  padding: 0.1rem 0.45rem;
  border-radius: 2px;
  font-size: 0.7rem;
  font-weight: 700;
  margin: 0 2px;
  font-family: monospace;
}
.soft   { background: rgba(200,0,0,0.2);   color: #ff9999; }
.medium { background: rgba(200,200,0,0.2); color: #ffff88; }
.hard   { background: rgba(200,200,200,0.15); color: #ccc; }
.stay   { background: rgba(0,100,220,0.2); color: #88aaff; }

/* slider demo */
.slider-demo { margin: 1rem 0; }
.slider-track {
  position: relative;
  height: 3px;
  background: #1a1a1a;
  border-radius: 2px;
  margin-bottom: 0.5rem;
}
.slider-fill {
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 48%;
  background: linear-gradient(90deg, #e10600, #ff4422);
  border-radius: 2px;
}
.slider-thumb {
  position: absolute;
  left: 48%;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 14px; height: 14px;
  background: #e10600;
  border-radius: 50%;
  box-shadow: 0 0 8px rgba(225,6,0,0.4);
}
.slider-labels {
  display: flex;
  justify-content: space-between;
  font-size: 0.65rem;
  color: #333;
  font-family: monospace;
}
.slider-current { color: #e10600; }

/* window explainer */
.window-explainer { margin-top: 1.5rem; }
.window-row {
  display: flex;
  gap: 4px;
  margin-bottom: 0.5rem;
}
.window-cell {
  flex: 1;
  padding: 0.4rem 0;
  text-align: center;
  font-family: monospace;
  font-size: 0.65rem;
  border-radius: 2px;
}
.window-cell.hit { background: rgba(0,180,60,0.15); color: #66dd88; border: 1px solid rgba(0,180,60,0.2); }
.window-cell.miss { background: #0d0d0d; color: #2a2a2a; border: 1px solid #141414; }
.window-cell.selected-lap { background: rgba(0,180,60,0.3); color: #aaffcc; font-weight: 700; border-color: rgba(0,180,60,0.5); }
.window-legend { display: flex; gap: 1.5rem; font-size: 0.65rem; }
.legend-hit { color: #66dd88; }
.legend-miss { color: #333; }

/* scoring grid */
.scoring-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 0.75rem;
  margin-bottom: 1.25rem;
}
.score-card {
  padding: 0.9rem;
  border-radius: 2px;
  border: 1px solid;
}
.score-card.green { background: rgba(0,160,60,0.08); border-color: rgba(0,160,60,0.2); }
.score-card.red   { background: rgba(225,6,0,0.08);  border-color: rgba(225,6,0,0.2); }
.score-card.neutral { background: #0d0d0d; border-color: #1a1a1a; }
.score-label { font-size: 0.65rem; color: #555; margin-bottom: 0.4rem; line-height: 1.4; }
.score-value { font-family: 'Bebas Neue', sans-serif; font-size: 1rem; letter-spacing: 0.04em; margin-bottom: 0.25rem; }
.score-card.green .score-value { color: #66dd88; }
.score-card.red   .score-value { color: #ff7766; }
.score-card.neutral .score-value { color: #444; }
.score-example { font-size: 0.6rem; color: #333; line-height: 1.4; }

/* timing tower demo */
.tower-demo {
  background: #0a0a0a;
  border: 1px solid #141414;
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: 1.5rem;
}
.tower-header-demo {
  display: grid;
  grid-template-columns: 28px 1fr 72px 60px;
  padding: 0.4rem 0.75rem;
  border-bottom: 1px solid #141414;
}
.tower-header-demo span { font-size: 0.58rem; letter-spacing: 0.1em; color: #2a2a2a; font-weight: 700; }
.tower-header-demo span:nth-child(3) { text-align: right; }
.tower-row-demo {
  display: grid;
  grid-template-columns: 28px 1fr 72px 60px;
  align-items: center;
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid rgba(255,255,255,0.025);
}
.tower-row-demo.gold span:first-child { color: #ffd700; font-family: 'Bebas Neue', sans-serif; font-size: 1rem; }
.tower-row-demo.silver span:first-child { color: #c0c0c0; font-family: 'Bebas Neue', sans-serif; font-size: 1rem; }
.tower-row-demo span:first-child { color: #444; font-family: 'Bebas Neue', sans-serif; font-size: 1rem; }
.driver-cell { display: flex; flex-direction: column; gap: 2px; padding-left: 0.25rem; }
.code { font-family: monospace; font-size: 0.82rem; font-weight: 800; color: #ddd; }
.team { font-size: 0.58rem; font-weight: 600; letter-spacing: 0.04em; }
.mono { font-family: monospace; font-size: 0.75rem; color: #555; text-align: right; }
.grey { color: #333; }
.tyre-cell { display: flex; align-items: center; gap: 6px; padding-left: 0.25rem; }
.dot { width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0; }
.soft-dot   { background: #cc2222; }
.medium-dot { background: #cccc00; }
.hard-dot   { background: #cccccc; }

/* legend list */
.legend-list { display: flex; flex-direction: column; gap: 0.6rem; }
.legend-item { display: flex; align-items: center; gap: 1rem; }
.legend-key {
  font-size: 0.65rem;
  font-weight: 700;
  color: #555;
  letter-spacing: 0.08em;
  min-width: 48px;
  font-family: monospace;
}
.tyre-legend { display: flex; align-items: center; }
.legend-val { font-size: 0.78rem; color: #444; }

/* tips */
.tips { display: flex; flex-direction: column; gap: 1rem; }
.tip {
  display: flex;
  gap: 1rem;
  align-items: flex-start;
  padding: 0.85rem;
  background: #0d0d0d;
  border: 1px solid #141414;
  border-radius: 2px;
}
.tip-icon { font-size: 1.1rem; flex-shrink: 0; }
.tip-title { font-size: 0.82rem; font-weight: 700; color: #ccc; margin-bottom: 0.2rem; }
.tip-desc { font-size: 0.78rem; color: #444; line-height: 1.6; }

/* CTA */
.cta-bar {
  border-top: 1px solid #111;
  background: #0a0a0a;
}
.cta-inner {
  max-width: 720px;
  margin: 0 auto;
  padding: 2rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 2rem;
}
.cta-title {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 1.4rem;
  color: #fff;
  letter-spacing: 0.05em;
}
.cta-sub { font-size: 0.78rem; color: #333; margin-top: 0.2rem; }
.cta-btn {
  display: inline-block;
  padding: 0.65rem 1.5rem;
  background: rgba(225,6,0,0.15);
  border: 1px solid rgba(225,6,0,0.4);
  color: #e10600;
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-decoration: none;
  border-radius: 2px;
  transition: all 0.15s;
  white-space: nowrap;
  flex-shrink: 0;
}
.cta-btn:hover { background: rgba(225,6,0,0.3); border-color: #e10600; }

@media (max-width: 600px) {
  .block { grid-template-columns: 1fr; gap: 0.5rem; }
  .block-num { display: none; }
  .scoring-grid { grid-template-columns: 1fr; }
  .cta-inner { flex-direction: column; text-align: center; }
  .cta-btn { width: 100%; text-align: center; }
  .window-cell { font-size: 0.55rem; padding: 0.3rem 0; }
}
</style>