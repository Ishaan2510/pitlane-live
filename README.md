<div align="center">

# Pitlane Live

**A full-stack F1 race analytics platform — built, deployed, and maintained end-to-end.**

Live race replays · Driver standings · User predictions · Season schedule

[![Live App](https://img.shields.io/badge/Live_App-pitlane--live-brightgreen?style=for-the-badge&logo=vercel)](https://pitlane-live-three.vercel.app)
[![Vue.js](https://img.shields.io/badge/Vue.js-3-4FC08D?style=flat-square&logo=vuedotjs&logoColor=white)](https://vuejs.org/)
[![Flask](https://img.shields.io/badge/Flask-000000?style=flat-square&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-DC382D?style=flat-square&logo=redis&logoColor=white)](https://redis.io/)
[![Azure](https://img.shields.io/badge/Azure_VM-0078D4?style=flat-square&logo=microsoftazure&logoColor=white)](https://azure.microsoft.com/)

</div>

---

## What This Is

Pitlane Live lets F1 fans replay any race lap-by-lap, track driver and constructor standings for the live season, and submit predictions before race weekends. The platform scores predictions automatically after each race.

This is not a tutorial project. It's a production deployment with a real user-facing frontend, a backend that handles concurrent requests under load, an async post-race data pipeline, and two infrastructure migrations behind it.

**Live:** https://pitlane-live-three.vercel.app

---

## Architecture

```
                    ┌─────────────────────────────┐
                    │   Vue 3 Frontend             │
                    │   (Vercel)                   │
                    │   /live /replay /standings   │
                    │   /the-grid /profile         │
                    └──────────────┬──────────────┘
                                   │  /api/* proxied
                                   ▼
                    ┌─────────────────────────────┐
                    │   Flask Backend              │
                    │   Gunicorn + gthread         │
                    │   (Render)                   │
                    │                             │
                    │   routes/                   │
                    │   ├── replay.py             │
                    │   ├── schedule.py           │
                    │   ├── scoring.py            │
                    │   └── news.py               │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    │                              │
          ┌─────────▼─────────┐     ┌─────────────▼───────┐
          │  Supabase          │     │  Pre-built JSON      │
          │  PostgreSQL        │     │  Race telemetry      │
          │  (users, scores,   │     │  committed to repo   │
          │   predictions)     │     │  (processed locally) │
          └───────────────────┘     └─────────────────────┘
```

**Post-race data flow (manual trigger after chequered flag):**

```
Local machine → warm_cache.py → processed JSON → git push → Render auto-redeploy
                                                          → /api/scoring/score-race
```

Ingestion and serving are independent processes. A stalled pipeline never touches API uptime.

---

## Key Engineering Decisions

### 1. gthread over gevent (and why it matters)

The original Azure deployment used Gunicorn with gevent workers — the standard choice for Flask apps with long-lived connections. When migrating to Render's free tier, gevent broke with recursion errors.

**Root cause:** gevent monkey-patches the standard library, including SSL. On Render's runtime, urllib3 and PyJWT had already imported the unpatched SSL module before monkey-patching ran. The patched and unpatched versions conflicted, causing infinite recursion.

**Fix:** Switch to gthread workers. gthread uses real OS threads — no monkey patching, no SSL conflict. Same concurrency benefit within the 512MB memory constraint.

```
# Azure (gevent — worked fine on VM)
gunicorn --worker-class gevent --workers 2 ...

# Render (gthread — handles SSL imports correctly)
gunicorn --worker-class gthread --workers 1 --threads 4 ...
```

### 2. Pre-built JSONs over on-demand FastF1 processing

FastF1 + pandas needs 1–2GB RAM during race data processing. Render's free tier has 512MB. Attempting on-demand processing would OOM the server.

**Solution:** Process locally after each race, commit the output JSONs to the repo, let Render redeploy with new data. The 24MB total JSON payload is well within GitHub's file limits. The tradeoff is a 2–3 minute update delay after each race — acceptable for a post-race analytics app.

### 3. Atomic JSON write pattern

The race replay endpoint reads from a pre-built JSON file on disk. If a client requests `/api/replay/2026/5` exactly as that file is being written by the pipeline, they'd read a partial file — potentially invalid JSON.

**Fix:** Write to a `.tmp` file first, then do an atomic `os.replace()` to move it into the target path. `os.replace()` is atomic at the OS level — the old file is never partially visible to readers.

```python
tmp_path = output_path + ".tmp"
with open(tmp_path, "w") as f:
    json.dump(data, f)
os.replace(tmp_path, output_path)  # Atomic — no partial reads possible
```

### 4. Supabase Session Pooler for IPv4/IPv6 compatibility

Supabase's free tier resolves to IPv6 on the direct connection string. Render's free tier is IPv4-only. The two are incompatible on the default URL.

**Fix:** Use Supabase's Session Pooler connection string (`pooler.supabase.com:5432`), which handles IPv4 proxying transparently without any code changes.

### 5. Keep-alive cron to prevent cold starts

Render's free tier sleeps the service after 15 minutes of inactivity. A cold start adds ~30 seconds to the first request. A cron-job.org job pings `/api/schedule` every 10 minutes, keeping the service warm at zero cost.

---

## Infrastructure History

### Phase 1 — Azure VM

Deployed on a Microsoft Azure B2s VM (Ubuntu 22.04, 2 vCPUs, 4GB RAM) via an Azure for Students subscription. Flask served via Gunicorn + gevent workers behind Nginx. SQLite on the VM filesystem. FastF1 processing ran directly on the VM.

This was the right environment for learning real production deployment: SSH access, systemd service management, Nginx reverse proxy configuration, and process supervision. All of that knowledge transferred directly.

Migration trigger: Azure student credits exhausted. The VM was also over-provisioned for this workload — 4GB RAM running continuously for an API that serves bursts of traffic around race weekends.

### Phase 2 — Render + Supabase (current)

| Concern | Azure | Render |
|---|---|---|
| Backend | Azure VM (4GB RAM) | Render free tier (512MB RAM) |
| Database | SQLite on VM | Supabase PostgreSQL |
| FastF1 processing | On the VM | Local machine only |
| Race data | Processed on demand | Pre-built JSONs in repo |
| Workers | gevent (2 workers) | gthread (1 worker, 4 threads) |

---

## Post-Race Workflow

Run within 30–60 minutes of the chequered flag:

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

Render auto-redeploys in 2–3 minutes.

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
| GET | `/api/replay/:year/:round` | Lap-by-lap position data for race replay |
| POST | `/api/scoring/score-race` | Admin — trigger post-race scoring (requires `X-Admin-Key`) |

---

## Deployment

### Frontend (Vercel)
Auto-deploys on every push to `main`. `frontend/vercel.json` proxies all `/api/*` requests to the Render backend.

### Backend (Render)
```
Root Directory:  backend
Build Command:   pip install -r requirements.txt
Start Command:   gunicorn --worker-class gthread --workers 1 --threads 4 --bind 0.0.0.0:$PORT run:app
Python Version:  3.11.9 (via backend/.python-version)
```

Environment variables: `DATABASE_URL`, `SECRET_KEY`, `ADMIN_KEY` — set in Render dashboard.

### Database (Supabase)
PostgreSQL on Supabase free tier. Tables created via SQLAlchemy `db.create_all()`. Use the Session Pooler URL, not the direct connection string.

---

## Project Structure

```
pitlane-live/
├── frontend/
│   └── src/
│       ├── router.js
│       ├── stores/auth.js
│       ├── components/Navbar.vue
│       └── views/
│           ├── Home.vue
│           ├── WatchLive.vue        # /live
│           ├── RaceReplay.vue       # /replay
│           ├── Standings.vue        # /standings
│           ├── TheGrid.vue          # /the-grid
│           ├── PitWall.vue          # /pit-wall
│           ├── Profile.vue          # /profile
│           └── Schedule.vue         # /schedule
└── backend/
    ├── app/
    │   ├── __init__.py
    │   └── routes/
    │       ├── replay.py
    │       ├── schedule.py
    │       ├── scoring.py
    │       └── news.py
    ├── services/
    │   ├── fastf1_service.py
    │   └── scoring_service.py
    ├── fastf1_cache/processed/       # Pre-built race JSONs (committed to git)
    ├── .python-version               # Pins Python 3.11.9 for Render
    └── warm_cache.py
```

---

*Built by [Ishaan Goswami](https://github.com/Ishaan2510) — CS undergrad, PDEU + IIT Madras*
