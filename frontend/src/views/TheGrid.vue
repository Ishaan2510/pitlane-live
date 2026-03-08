<template>
  <div class="the-grid">

    <!-- ── Header ── -->
    <div class="page-header">
      <div class="header-tag">2026 SEASON</div>
      <h1 class="page-title">THE GRID</h1>
      <p class="page-sub">All 22 drivers. 11 teams. One championship.</p>
    </div>

    <!-- ── Team filter ── -->
    <div class="filter-bar">
      <button
        v-for="f in filters"
        :key="f"
        class="filter-btn"
        :class="{ active: activeFilter === f }"
        @click="activeFilter = f"
      >{{ f }}</button>
    </div>

    <!-- ── Driver grid ── -->
    <div class="drivers-grid">
      <div
        v-for="driver in filteredDrivers"
        :key="driver.code"
        class="driver-card"
        :class="{ expanded: expandedDriver === driver.code }"
        @click="toggleDriver(driver.code)"
      >
        <div class="card-top">
          <div class="driver-number" :style="{ color: driver.teamColor }">{{ driver.number }}</div>
          <div class="driver-info">
            <div class="driver-name">{{ driver.firstName }}<br><span class="driver-surname">{{ driver.lastName }}</span></div>
            <div class="driver-team" :style="{ color: driver.teamColor }">{{ driver.team }}</div>
          </div>
          <div class="driver-flag">{{ driver.flag }}</div>
        </div>

        <div class="card-stats">
          <div class="stat">
            <div class="stat-val">{{ driver.championships }}</div>
            <div class="stat-label">WDC</div>
          </div>
          <div class="stat">
            <div class="stat-val">{{ driver.wins }}</div>
            <div class="stat-label">WINS</div>
          </div>
          <div class="stat">
            <div class="stat-val">{{ driver.podiums }}</div>
            <div class="stat-label">PODIUMS</div>
          </div>
          <div class="stat">
            <div class="stat-val">{{ driver.poles }}</div>
            <div class="stat-label">POLES</div>
          </div>
        </div>

        <!-- Expanded detail -->
        <div class="card-detail" v-if="expandedDriver === driver.code">
          <div class="detail-row">
            <span class="detail-label">NATIONALITY</span>
            <span class="detail-val">{{ driver.nationality }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">DATE OF BIRTH</span>
            <span class="detail-val">{{ driver.dob }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">SEASONS IN F1</span>
            <span class="detail-val">{{ driver.seasons }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">POINTS SCORED</span>
            <span class="detail-val">{{ driver.points.toLocaleString() }}</span>
          </div>
          <div class="driver-bio">{{ driver.bio }}</div>
        </div>

        <div class="card-expand-hint">{{ expandedDriver === driver.code ? '▲ LESS' : '▼ MORE' }}</div>
      </div>
    </div>

    <!-- ── News section ── -->
    <div class="news-section">
      <div class="news-header">
        <div class="news-title-block">
          <div class="section-tag">LATEST</div>
          <h2 class="news-heading">F1 NEWS</h2>
        </div>
        <div class="news-source">via Autosport</div>
      </div>

      <div v-if="newsLoading" class="news-loading">
        <div class="news-pip"></div>
        <span>Loading news…</span>
      </div>

      <div v-else-if="newsError" class="news-error">
        Could not load news feed. <a href="https://www.autosport.com/f1" target="_blank">Visit Autosport →</a>
      </div>

      <div v-else class="news-list">
        <a
          v-for="(item, i) in news"
          :key="i"
          :href="item.link"
          target="_blank"
          class="news-item"
          :class="{ featured: i === 0 }"
        >
          <div class="news-item-inner">
            <div class="news-meta">
              <span class="news-category">{{ item.category }}</span>
              <span class="news-time">{{ item.time }}</span>
            </div>
            <div class="news-headline">{{ item.title }}</div>
            <div class="news-summary" v-if="item.summary">{{ item.summary }}</div>
            <div class="news-read">READ MORE →</div>
          </div>
        </a>
      </div>
    </div>

  </div>
</template>

<script>
const TEAM_COLORS = {
  'Alpine':          '#FF87BC',
  'Aston Martin':    '#229971',
  'Audi':            '#ffffff',
  'Cadillac':        '#CC0000',
  'Ferrari':         '#E8002D',
  'Haas':            '#B6BABD',
  'McLaren':         '#FF8000',
  'Mercedes':        '#27F4D2',
  'Racing Bulls':    '#6692FF',
  'Red Bull Racing': '#3671C6',
  'Williams':        '#64C4FF',
}

const DRIVERS = [
  // Alpine
  { code:'GAS', number:10, firstName:'Pierre',    lastName:'Gasly',      team:'Alpine',          flag:'🇫🇷', nationality:'French',      dob:'7 Feb 1996',  seasons:9,  championships:0, wins:1,  podiums:3,  poles:1,  points:374,  bio:'Gasly took his maiden F1 victory at Monza 2021 in one of the sport\'s great upsets. A consistent performer who earned his Alpine seat after years at the sharp end of the midfield.' },
  { code:'COL', number:43, firstName:'Franco',    lastName:'Colapinto',  team:'Alpine',          flag:'🇦🇷', nationality:'Argentine',   dob:'27 May 2003', seasons:2,  championships:0, wins:0,  podiums:0,  poles:0,  points:5,    bio:'The Argentine rookie announced himself with strong performances after mid-season promotion in 2024. Now with a full season at Alpine, he is one of the most exciting young talents on the grid.' },
  // Aston Martin
  { code:'ALO', number:14, firstName:'Fernando',  lastName:'Alonso',     team:'Aston Martin',    flag:'🇪🇸', nationality:'Spanish',     dob:'29 Jul 1981', seasons:22, championships:2, wins:32, podiums:106,poles:22, points:2267, bio:'A two-time world champion and widely considered one of the greatest drivers of all time. Still competing at the highest level into his mid-40s, Alonso\'s racecraft and tire management remain peerless.' },
  { code:'STR', number:18, firstName:'Lance',     lastName:'Stroll',     team:'Aston Martin',    flag:'🇨🇦', nationality:'Canadian',    dob:'29 Oct 1998', seasons:8,  championships:0, wins:0,  podiums:3,  poles:1,  points:260,  bio:'The Canadian has developed steadily over his F1 career. A pole position at Istanbul in 2020 and several podiums demonstrate that on his day, Stroll can mix it at the front.' },
  // Audi
  { code:'HUL', number:27, firstName:'Nico',      lastName:'Hulkenberg',  team:'Audi',           flag:'🇩🇪', nationality:'German',      dob:'19 Aug 1987', seasons:14, championships:0, wins:0,  podiums:0,  poles:1,  points:530,  bio:'The man with the most starts without a podium in F1 history — yet Hulkenberg\'s pace and consistency earned him a coveted seat at the rebranded Audi works team for the new era.' },
  { code:'BOR', number:5,  firstName:'Gabriel',   lastName:'Bortoleto',  team:'Audi',            flag:'🇧🇷', nationality:'Brazilian',   dob:'14 Oct 2004', seasons:1,  championships:0, wins:0,  podiums:0,  poles:0,  points:0,    bio:'The reigning F2 champion and protégé of Fernando Alonso. Bortoleto arrives in F1 with enormous expectations after dominating the junior categories.' },
  // Cadillac
  { code:'PER', number:11, firstName:'Sergio',    lastName:'Perez',      team:'Cadillac',        flag:'🇲🇽', nationality:'Mexican',     dob:'26 Jan 1990', seasons:14, championships:0, wins:8,  podiums:39, poles:3,  points:1356, bio:'Checo\'s 2022 season showed the world what he is capable of. Now at the new Cadillac outfit, the Mexican is tasked with helping build an American team from the ground up.' },
  { code:'BOT', number:77, firstName:'Valtteri',  lastName:'Bottas',     team:'Cadillac',        flag:'🇫🇮', nationality:'Finnish',     dob:'28 Aug 1989', seasons:13, championships:0, wins:10, podiums:67, poles:20, points:1797, bio:'Ten race victories and over 20 pole positions tell the story of a driver who was consistently brilliant. Bottas brings enormous experience and development ability to the new Cadillac project.' },
  // Ferrari
  { code:'LEC', number:16, firstName:'Charles',   lastName:'Leclerc',    team:'Ferrari',         flag:'🇲🇨', nationality:'Monégasque',  dob:'16 Oct 1997', seasons:7,  championships:0, wins:8,  podiums:37, poles:26, points:1073, bio:'The fastest qualifier of his generation. Leclerc has been the heartbeat of Ferrari\'s revival, and with Hamilton alongside him, 2026 represents arguably the strongest Ferrari lineup in decades.' },
  { code:'HAM', number:44, firstName:'Lewis',     lastName:'Hamilton',   team:'Ferrari',         flag:'🇬🇧', nationality:'British',     dob:'7 Jan 1985',  seasons:18, championships:7, wins:104,podiums:197,poles:104,points:4839, bio:'The most decorated driver in F1 history. Seven championships, 104 wins, 104 poles. Hamilton\'s move to Ferrari in 2026 is the most seismic driver transfer in decades.' },
  // Haas
  { code:'OCO', number:31, firstName:'Esteban',   lastName:'Ocon',       team:'Haas',            flag:'🇫🇷', nationality:'French',      dob:'17 Sep 1996', seasons:8,  championships:0, wins:1,  podiums:3,  poles:0,  points:366,  bio:'A race winner at Hungary 2021 who brings race-winning pedigree to Haas. Known for his tenacious defending and ability to extract the maximum from the machinery.' },
  { code:'BEA', number:87, firstName:'Oliver',    lastName:'Bearman',    team:'Haas',            flag:'🇬🇧', nationality:'British',     dob:'8 May 2005',  seasons:2,  championships:0, wins:0,  podiums:0,  poles:0,  points:7,    bio:'Made his debut as a teenager standing in for Ferrari at Saudi Arabia 2024 and immediately impressed. Bearman is one of the brightest British talents since Hamilton himself.' },
  // McLaren
  { code:'NOR', number:4,  firstName:'Lando',     lastName:'Norris',     team:'McLaren',         flag:'🇬🇧', nationality:'British',     dob:'13 Nov 1999', seasons:6,  championships:0, wins:4,  podiums:24, poles:5,  points:789,  bio:'The 2024 title challenger who pushed Verstappen all the way to the final race. Norris has developed into a complete driver and is widely tipped as a future champion.' },
  { code:'PIA', number:81, firstName:'Oscar',     lastName:'Piastri',    team:'McLaren',         flag:'🇦🇺', nationality:'Australian',  dob:'6 Apr 2001',  seasons:3,  championships:0, wins:3,  podiums:12, poles:2,  points:292,  bio:'The reigning F3 and F2 champion who backed it up in F1 immediately. Piastri\'s cool head under pressure and natural pace make him a generational talent.' },
  // Mercedes
  { code:'RUS', number:63, firstName:'George',    lastName:'Russell',    team:'Mercedes',        flag:'🇬🇧', nationality:'British',     dob:'15 Feb 1998', seasons:6,  championships:0, wins:2,  podiums:16, poles:3,  points:576,  bio:'The meticulous technician. Russell never wastes a point, extracts everything from the car and is now leading Mercedes\' charge for a return to the top as their new lead driver.' },
  { code:'ANT', number:12, firstName:'Kimi',      lastName:'Antonelli',  team:'Mercedes',        flag:'🇮🇹', nationality:'Italian',     dob:'25 Aug 2006', seasons:1,  championships:0, wins:0,  podiums:0,  poles:0,  points:0,    bio:'The youngest driver on the 2026 grid. Antonelli is Mercedes\' most prized prospect in years — promoted directly to replace Hamilton after a meteoric rise through junior formulae.' },
  // Racing Bulls
  { code:'LAW', number:30, firstName:'Liam',      lastName:'Lawson',     team:'Racing Bulls',    flag:'🇳🇿', nationality:'New Zealander',dob:'11 Feb 2002', seasons:2,  championships:0, wins:0,  podiums:0,  poles:0,  points:6,    bio:'The New Zealander earned his place through sheer speed and composure as a substitute driver. Now with a full season at Racing Bulls, Lawson is ready to prove himself consistently.' },
  { code:'LIN', number:44, firstName:'Arvid',     lastName:'Lindblad',   team:'Racing Bulls',    flag:'🇬🇧', nationality:'British',     dob:'12 Jun 2007', seasons:1,  championships:0, wins:0,  podiums:0,  poles:0,  points:0,    bio:'The youngest British driver to reach F1. Lindblad\'s rapid ascent through the Red Bull junior programme signals the team\'s belief that he is the real deal.' },
  // Red Bull Racing
  { code:'VER', number:1,  firstName:'Max',       lastName:'Verstappen', team:'Red Bull Racing', flag:'🇳🇱', nationality:'Dutch',       dob:'30 Sep 1997', seasons:10, championships:4, wins:63, podiums:112,poles:40, points:2862, bio:'Four consecutive world championships. Verstappen has rewritten the record books and is widely regarded as the dominant force of his generation. Ruthless, fast and relentless.' },
  { code:'HAD', number:22, firstName:'Isack',     lastName:'Hadjar',     team:'Red Bull Racing', flag:'🇫🇷', nationality:'French',      dob:'28 Feb 2004', seasons:1,  championships:0, wins:0,  podiums:0,  poles:0,  points:0,    bio:'The 2024 F2 runner-up who earned the coveted second Red Bull seat. Hadjar has the speed — now the question is whether he can handle the pressure of being Verstappen\'s teammate.' },
  // Williams
  { code:'SAI', number:55, firstName:'Carlos',    lastName:'Sainz',      team:'Williams',        flag:'🇪🇸', nationality:'Spanish',     dob:'1 Sep 1994',  seasons:10, championships:0, wins:3,  podiums:26, poles:5,  points:1021, bio:'A race winner and consistent points scorer who left Ferrari after Hamilton\'s arrival. Sainz brings championship-level experience to Williams as they target a return to the front.' },
  { code:'ALB', number:23, firstName:'Alexander', lastName:'Albon',      team:'Williams',        flag:'🇹🇭', nationality:'Thai',        dob:'23 Mar 1996', seasons:5,  championships:0, wins:0,  podiums:2,  poles:0,  points:260,  bio:'The Williams cornerstone. Albon has been instrumental in the team\'s revival and is one of the most well-liked figures in the paddock. Consistent, intelligent and relentlessly positive.' },
]

export default {
  name: 'TheGrid',

  data() {
    return {
      drivers:        DRIVERS,
      activeFilter:   'ALL',
      expandedDriver: null,
      news:           [],
      newsLoading:    true,
      newsError:      false,
    }
  },

  computed: {
    filters() {
      return ['ALL', ...Object.keys(TEAM_COLORS)]
    },
    filteredDrivers() {
      if (this.activeFilter === 'ALL') return this.drivers
      return this.drivers.filter(d => d.team === this.activeFilter)
    },
  },

  async mounted() {
    DRIVERS.forEach(d => { d.teamColor = TEAM_COLORS[d.team] || '#888' })
    await this.loadNews()
  },

  methods: {
    toggleDriver(code) {
      this.expandedDriver = this.expandedDriver === code ? null : code
    },

    async loadNews() {
      this.newsLoading = true
      this.newsError   = false
      try {
        const res  = await fetch('/api/news')
        const data = await res.json()
        if (data.error) throw new Error(data.error)
        this.news = data
      } catch {
        this.newsError = true
      } finally {
        this.newsLoading = false
      }
    }
  }
}
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Mono:wght@400;500&family=Work+Sans:wght@400;500;600;700&display=swap');

.the-grid {
  min-height: calc(100vh - 56px);
  background: #080808;
  font-family: 'Work Sans', sans-serif;
  color: #ccc;
}

/* ── Header ── */
.page-header {
  padding: 3rem 3rem 2rem;
  border-bottom: 1px solid #111;
}
.header-tag {
  font-size: 0.62rem;
  letter-spacing: 0.2em;
  color: #e10600;
  font-family: 'DM Mono', monospace;
  font-weight: 500;
  margin-bottom: 0.75rem;
}
.page-title {
  font-family: 'Bebas Neue', sans-serif;
  font-size: clamp(3rem, 7vw, 5.5rem);
  color: #fff;
  letter-spacing: 0.04em;
  line-height: 1;
  margin: 0 0 0.5rem;
}
.page-sub {
  font-size: 0.85rem;
  color: #333;
  font-family: 'DM Mono', monospace;
}

/* ── Filter bar ── */
.filter-bar {
  display: flex;
  gap: 0.4rem;
  padding: 1rem 3rem;
  flex-wrap: wrap;
  border-bottom: 1px solid #111;
  background: #0a0a0a;
}
.filter-btn {
  background: transparent;
  border: 1px solid #1a1a1a;
  color: #333;
  padding: 0.3rem 0.75rem;
  font-family: 'DM Mono', monospace;
  font-size: 0.62rem;
  letter-spacing: 0.08em;
  cursor: pointer;
  border-radius: 2px;
  transition: all 0.15s;
  white-space: nowrap;
}
.filter-btn:hover { border-color: #333; color: #888; }
.filter-btn.active { border-color: #e10600; color: #e10600; background: rgba(225,6,0,0.08); }

/* ── Driver grid ── */
.drivers-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1px;
  background: #111;
  padding: 0;
}
.driver-card {
  background: #080808;
  padding: 1.25rem;
  cursor: pointer;
  transition: background 0.15s;
  position: relative;
}
.driver-card:hover { background: #0d0d0d; }
.driver-card.expanded { background: #0d0d0d; }
.driver-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 1px;
  background: var(--team-color, transparent);
  opacity: 0;
  transition: opacity 0.2s;
}
.driver-card:hover::before,
.driver-card.expanded::before { opacity: 1; }

.card-top {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  margin-bottom: 1rem;
}
.driver-number {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 2rem;
  line-height: 1;
  min-width: 48px;
  opacity: 0.8;
}
.driver-name {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 1rem;
  color: #888;
  letter-spacing: 0.04em;
  line-height: 1.1;
}
.driver-surname {
  font-size: 1.3rem;
  color: #fff;
}
.driver-team {
  font-size: 0.6rem;
  letter-spacing: 0.1em;
  font-family: 'DM Mono', monospace;
  margin-top: 0.3rem;
  font-weight: 500;
}
.driver-flag {
  margin-left: auto;
  font-size: 1.4rem;
  flex-shrink: 0;
}

.card-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.25rem;
}
.stat {
  background: #0d0d0d;
  border: 1px solid #111;
  padding: 0.4rem 0.25rem;
  text-align: center;
  border-radius: 1px;
}
.stat-val {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 1.1rem;
  color: #ddd;
  letter-spacing: 0.03em;
  line-height: 1;
}
.stat-label {
  font-size: 0.52rem;
  color: #333;
  letter-spacing: 0.1em;
  font-family: 'DM Mono', monospace;
  margin-top: 0.15rem;
}

/* Expanded detail */
.card-detail {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #141414;
}
.detail-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.35rem 0;
  border-bottom: 1px solid #0f0f0f;
}
.detail-label {
  font-size: 0.6rem;
  color: #2a2a2a;
  letter-spacing: 0.1em;
  font-family: 'DM Mono', monospace;
}
.detail-val {
  font-size: 0.75rem;
  color: #666;
  font-family: 'DM Mono', monospace;
}
.driver-bio {
  margin-top: 0.85rem;
  font-size: 0.75rem;
  color: #3a3a3a;
  line-height: 1.7;
}
.card-expand-hint {
  margin-top: 0.85rem;
  font-size: 0.55rem;
  color: #1e1e1e;
  letter-spacing: 0.12em;
  font-family: 'DM Mono', monospace;
  text-align: right;
}
.driver-card:hover .card-expand-hint { color: #333; }

/* ── News section ── */
.news-section {
  padding: 3rem;
  border-top: 1px solid #111;
}
.news-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: 2rem;
}
.section-tag {
  font-size: 0.62rem;
  letter-spacing: 0.2em;
  color: #e10600;
  font-family: 'DM Mono', monospace;
  margin-bottom: 0.5rem;
}
.news-heading {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 2.5rem;
  color: #fff;
  letter-spacing: 0.04em;
  margin: 0;
  line-height: 1;
}
.news-source {
  font-size: 0.62rem;
  color: #222;
  font-family: 'DM Mono', monospace;
  letter-spacing: 0.08em;
}
.news-loading {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  color: #333;
  font-size: 0.8rem;
  font-family: 'DM Mono', monospace;
}
.news-pip {
  width: 8px; height: 8px;
  background: #e10600;
  border-radius: 50%;
  animation: pip 1s ease-in-out infinite;
}
@keyframes pip { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.3;transform:scale(1.5)} }
.news-error {
  font-size: 0.8rem;
  color: #333;
  font-family: 'DM Mono', monospace;
}
.news-error a { color: #e10600; text-decoration: none; }

.news-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1px;
  background: #111;
}
.news-item {
  background: #080808;
  text-decoration: none;
  display: block;
  transition: background 0.15s;
}
.news-item:hover { background: #0d0d0d; }
.news-item.featured { grid-column: span 2; }
.news-item-inner { padding: 1.25rem; }
.news-meta {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.6rem;
}
.news-category {
  font-size: 0.58rem;
  letter-spacing: 0.14em;
  color: #e10600;
  font-family: 'DM Mono', monospace;
  background: rgba(225,6,0,0.08);
  border: 1px solid rgba(225,6,0,0.15);
  padding: 0.15rem 0.5rem;
  border-radius: 1px;
}
.news-time {
  font-size: 0.6rem;
  color: #2a2a2a;
  font-family: 'DM Mono', monospace;
}
.news-headline {
  font-size: 0.92rem;
  font-weight: 700;
  color: #ccc;
  line-height: 1.4;
  margin-bottom: 0.5rem;
}
.news-item.featured .news-headline { font-size: 1.1rem; }
.news-summary {
  font-size: 0.75rem;
  color: #3a3a3a;
  line-height: 1.65;
  margin-bottom: 0.75rem;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.news-read {
  font-size: 0.62rem;
  color: #222;
  letter-spacing: 0.1em;
  font-family: 'DM Mono', monospace;
  transition: color 0.15s;
}
.news-item:hover .news-read { color: #e10600; }

@media (max-width: 768px) {
  .page-header, .filter-bar, .news-section { padding: 1.5rem; }
  .drivers-grid { grid-template-columns: 1fr 1fr; }
  .news-item.featured { grid-column: span 1; }
  .filter-bar { gap: 0.3rem; }
}
@media (max-width: 480px) {
  .drivers-grid { grid-template-columns: 1fr; }
}
</style>