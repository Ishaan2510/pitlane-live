# PITLANE LIVE

> F1 companion app built for Indian fans — race replays, driver profiles, live watch guide, predictions, and standings. All in one dark, fast, no-nonsense interface.

**Live:** https://pitlane-live-three.vercel.app

---

## Stack

| Layer | Tech |
|---|---|
| Frontend | Vue 3 (Options API) + Vite |
| Backend | Flask + Gunicorn/gthread |
| Database | PostgreSQL via SQLAlchemy |
| F1 Data | FastF1 (race data), Jolpica API (standings) |
| Frontend Hosting | Vercel |
| Backend Hosting | Render (free tier) |
| Database Hosting | Supabase (free tier) |

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
│           ├── RaceReplay.vue       # /replay
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
    │   └── processed/               # Pre-built race JSONs (committed to git)
    ├── .python-version              # Pins Python 3.11.9 for Render
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
| Red Bull | Verstappen #1 | Hadjar #6 |
| Williams | Sainz #55 | Albon #23 |

---

## Infrastructure & Deployment History

### Phase 1 — Azure VM (initial deployment)

The backend was originally hosted on a **Microsoft Azure B2s VM** (Ubuntu 22.04, 2 vCPUs, 4GB RAM) via an Azure for Students subscription.

**Azure setup:**
- Flask served via Gunicorn + gevent workers behind an Nginx reverse proxy
- SQLite database on the VM filesystem
- FastF1 race processing ran directly on the VM (1–2GB RAM during processing)
- systemd service kept Gunicorn alive across reboots
- SSH access via `.pem` key for deployments

**Why Azure first:** The student subscription provided free credits and a real Linux environment for learning cloud deployment, SSH, systemd, and process management — all standard production skills.

**Why migrated away:** Azure student credits exhausted. The VM was also over-provisioned for this workload — FastF1 processing only needs to run once per race weekend, not continuously.

---

### Phase 2 — Render + Supabase (current)

Migrated to a fully free, permanent-tier architecture when Azure credits ran out.

**Key architectural changes made during migration:**

| Concern | Azure | Render |
|---|---|---|
| Backend hosting | Azure VM (7.7GB RAM) | Render free tier (512MB RAM) |
| Database | SQLite on VM | Supabase PostgreSQL |
| FastF1 processing | On the VM | Local machine only |
| Race data serving | Processed on demand | Pre-built JSONs committed to GitHub |
| Workers | Gunicorn + gevent (2 workers) | Gunicorn + gthread (1 worker, 4 threads) |
| Python version | System default | Pinned to 3.11.9 via `.python-version` |

**Why gthread over gevent:** gevent monkey-patches SSL after urllib3 and PyJWT have already imported it, causing recursion errors on Render's runtime. gthread uses real OS threads — no monkey patching, no SSL conflicts, same concurrency benefit within the 512MB constraint.

**Why processed JSONs in GitHub:** Render's free tier has 512MB RAM. FastF1 + pandas during race processing needs 1–2GB. Separating the heavy processing (local machine) from the serving (Render) keeps the deployed service lean. The processed JSONs are 24MB total — well within GitHub's limits.

**Database connection:** Supabase's free tier resolves to IPv6 on the direct connection string. Render's free tier is IPv4-only. The Session Pooler URL (`pooler.supabase.com:5432`) handles the IPv4 proxying transparently.

**Keep-alive:** Render free tier sleeps after 15 minutes of inactivity. A cron-job.org job pings `/api/schedule` every 10 minutes to prevent cold starts.

---

## Deployment

### Frontend (Vercel)
Auto-deploys on every push to `main`. The `frontend/vercel.json` proxies all `/api/*` requests to the Render backend.

### Backend (Render)
Auto-deploys on every push to `main`.

```
Root Directory:  backend
Build Command:   pip install -r requirements.txt
Start Command:   gunicorn --worker-class gthread --workers 1 --threads 4 --bind 0.0.0.0:$PORT run:app
Python Version:  3.11.9 (via backend/.python-version)
```

Environment variables set in Render dashboard: `DATABASE_URL`, `SECRET_KEY`, `ADMIN_KEY`.

### Database (Supabase)
PostgreSQL on Supabase free tier. Tables created via SQLAlchemy `db.create_all()`. Connection uses the Session Pooler URL for IPv4 compatibility with Render.

---

## Post-Race Workflow

Run after each race (30–60 min after the chequered flag):

**Step 1 — Process FastF1 data locally:**
```bash
python warm_cache.py --year 2026 --round N
```

**Step 2 — Commit and push processed JSONs:**
```bash
git add backend/fastf1_cache/processed/
git commit -m "Add 2026 R[N] processed data"
git push origin main
```
Render auto-redeploys with the new data in 2–3 minutes.

**Step 3 — Trigger scoring:**
```bash
curl -X POST https://pitlane-live-three.vercel.app/api/scoring/score-race \
     -H "Content-Type: application/json" \
     -H "X-Admin-Key: [ADMIN_KEY]" \
     -d '{"year": 2026, "round": N}'
```

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
- R16 (Madrid) uses a generic oval placeholder — update after the September 2026 race

---

## License
Private project. Not affiliated with Formula 1, FOM, or any F1 team.