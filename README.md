# PITLANE LIVE

> F1 companion app built for Indian fans — race replays, driver profiles, live watch guide, predictions, and standings. All in one dark, fast, no-nonsense interface.

**Live:** https://pitlane-live-three.vercel.app

---

## Stack

| Layer | Tech |
|---|---|
| Frontend | Vue 3 (Options API) + Vite |
| Backend | Flask + Gunicorn/Gevent |
| Database | PostgreSQL via SQLAlchemy |
| F1 Data | FastF1 (race data), Jolpica API (standings) |
| Frontend Hosting | Vercel |
| Backend Hosting | Azure VM |

---

## Project Structure

```
pitlane-live/
├── frontend/
│   └── src/
│       ├── router.js
│       ├── stores/
│       │   └── auth.js
│       ├── components/
│       │   └── Navbar.vue
│       └── views/
│           ├── Home.vue
│           ├── WatchLive.vue        # /live
│           ├── Replay.vue           # /replay
│           ├── Standings.vue        # /standings
│           ├── TheGrid.vue          # /the-grid
│           ├── PitWall.vue          # /pit-wall
│           ├── Profile.vue          # /profile
│           └── Schedule.vue         # /schedule
│
└── backend/
    ├── app/
    │   ├── __init__.py
    │   └── routes/
    │       ├── replay.py
    │       ├── schedule.py
    │       ├── scoring.py
    │       └── news.py              # Autosport RSS feed, 10-min cache
    ├── services/
    │   ├── fastf1_service.py
    │   └── scoring_service.py
    ├── fastf1_cache/
    │   └── processed/               # 23 circuit JSON files (R1–R24)
    └── warm_cache.py
```

---

## Pages

### `/live` — Watch Live
Shows where to watch (FanCode, F1 TV). Displays the current race weekend's session schedule with a live countdown, pulled from `/api/schedule`.

### `/replay` — Race Replay
Animated lap-by-lap race replay using pre-processed FastF1 circuit data. Select year and round to replay any race.

### `/standings` — Standings
Driver and constructor standings for the current season via Jolpica API.

### `/the-grid` — The Grid
All 22 drivers for the 2026 season. Filterable by team. Each card shows driver number, nationality, team color, and expandable career stats. News section fetches latest F1 headlines from `/api/news`.

### `/pit-wall` — Pit Wall
How-to-play guide for user predictions. Explains the scoring system, tiebreakers, and deadlines.

### `/schedule` — Calendar
Full 2026 race calendar with sprint weekend badges.

### `/profile` — Profile
User's prediction history and points total.

---

## 2026 Driver Lineup

| Team | Driver 1 | Driver 2 |
|---|---|---|
| Alpine | Gasly #10 | Colapinto #43 |
| Aston Martin | Alonso #14 | Stroll #18 |
| Audi | Hulkenberg #27 | Bortoleto #5 |
| Cadillac | Perez #11 | Bottas #77 |
| Ferrari | Leclerc #16 | Hamilton #44 |
| Haas | Ocon #31 | Bearman #87 |
| McLaren | Norris #4 | Piastri #81 |
| Mercedes | Russell #63 | Antonelli #12 |
| Racing Bulls | Lawson #30 | Lindblad #41 |
| Red Bull | Verstappen #1 | Hadjar #22 |
| Williams | Sainz #55 | Albon #23 |

---

## Deployment

### Frontend (Vercel)
### Backend (Azure VM)
## Post-Race Workflow

Run after each race (30–60 min after the chequered flag):

**Step 1 — Warm the FastF1 cache:**
```bash
python warm_cache.py --year 2026 --round N
```
**Step 2 — Trigger scoring:**

```bash
curl -X POST https://pitlane-live-three.vercel.app/api/scoring/score-race \
     -H "Content-Type: application/json" \
     -H "X-Admin-Key: pitlane-admin-2026" \
     -d '{"year": 2026, "round": N}'

```
Replace `N` with the round number (e.g., `1` for Australia).

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/schedule` | Full 2026 race calendar + next session countdown |
| GET | `/api/news` | Latest F1 headlines (Autosport RSS, 10-min cache) |
| GET | `/api/replay/:year/:round` | Lap-by-lap position data for replay |
| POST | `/api/scoring/score-race` | Admin — trigger post-race scoring (requires `X-Admin-Key`) |

---

## Circuit Data

Pre-processed circuit JSONs live in `backend/fastf1_cache/processed/`:

- `2026_R1_circuit.json` through `2026_R24_circuit.json`
- 23 of 24 files have real track geometry
- R16 (Madrid) uses a generic oval placeholder — update when FastF1 adds the layout

---

## License
Private project. Not affiliated with Formula 1, FOM, or any F1 team.
