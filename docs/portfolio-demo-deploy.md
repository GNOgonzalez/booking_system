# Portfolio demo deployment (Render + Supabase)

Deploy **API + React** on Render with **PostgreSQL on Supabase**. Link the **frontend** URL on your portfolio (`PUBLIC_BOOKING_DEMO_URL`).

**Do not** use the API URL (`…/accounts/login/`) as the demo — that is legacy Django HTML.

---

## Architecture

```text
booking-frontend   Render Static Site
booking-api        Render Web Service (Docker)
PostgreSQL         Supabase (replaces Render free Postgres)
```

Render’s free Postgres is deprecated; Supabase free tier (~500 MB) is enough for a portfolio demo.

---

## Part 1 — Supabase database

1. [supabase.com](https://supabase.com) → **New project** (region close to Render — e.g. US West if API is Oregon).
2. Save the database password.
3. **Project Settings → Database → Connection string → URI**
   - For Render (long-lived gunicorn): **Session pooler** (`:6543`) or **Direct** (`:5432`).
   - Append `?sslmode=require` if not already in the URI.

Example shape (yours will differ):

```text
postgresql://postgres.[project-ref]:[PASSWORD]@aws-0-us-west-1.pooler.supabase.com:6543/postgres?sslmode=require
```

4. Verify locally (optional):

```bash
DATABASE_URL='postgresql://...' python manage.py migrate
DATABASE_URL='postgresql://...' python manage.py bootstrap_sandbox --demo --showcase
```

**Do not** commit real `DATABASE_URL` to git — set only in Render dashboard.

---

## Part 2 — Render deploy

### Fresh deploy (Blueprint)

1. **New** → **Blueprint** → connect `booking_system` repo.
2. Apply (creates `booking-api` + `booking-frontend`; no Render Postgres).
3. On **booking-api** → **Environment** → paste Supabase `DATABASE_URL`.
4. Set `ALLOWED_HOSTS` to your API hostname (e.g. `booking-api-xxxx.onrender.com`).
5. On **booking-frontend** → set `VITE_API_BASE` to `https://YOUR-API.onrender.com` (no trailing slash) → redeploy.
6. On **booking-api** → set `CORS_ALLOWED_ORIGINS` to the **booking-frontend** URL (exact match) → redeploy.

### If you already have the API (`booking-system-xxxx.onrender.com`)

#### 1. Create the React static site

1. [Render Dashboard](https://dashboard.render.com) → **New +** → **Static Site**
2. Connect repo **`GNOgonzalez/booking_system`**
3. Settings:

   | Field | Value |
   |-------|--------|
   | **Name** | `booking-frontend` |
   | **Root Directory** | `frontend` |
   | **Build Command** | `npm ci && npm run build` |
   | **Publish Directory** | `dist` |

4. **Environment variable** (required — baked in at build time):

   | Key | Value |
   |-----|--------|
   | `VITE_API_BASE` | `https://booking-system-eh39.onrender.com` (your API URL, no trailing slash) |

5. **Redirects/Rewrites** — add:

   | Source | Destination |
   |--------|-------------|
   | `/*` | `/index.html` |

6. **Create Static Site** → wait for build (~2 min).

7. Copy the static site URL, e.g. `https://booking-frontend-xxxx.onrender.com`.

#### 2. Wire CORS + Supabase on the API

Open your **Web Service** (API) → **Environment**:

| Key | Value |
|-----|--------|
| `DATABASE_URL` | Supabase URI from Part 1 |
| `CORS_ALLOWED_ORIGINS` | `https://booking-frontend-xxxx.onrender.com` (exact match) |
| `SEED_DEMO` | `true` |
| `SEED_SHOWCASE` | `true` (demo_student has membership + next lesson) |
| `DEMO_RESET_ON_START` | `false` (stable showcase; use `true` only to wipe on cold start) |

Save → redeploy. First deploy runs `migrate` + seed on Supabase.

#### 3. Delete old Render Postgres (optional)

Once Supabase works, delete the old **booking-db** service on Render.

---

## API environment (reference)

| Variable | Value |
|----------|--------|
| `DATABASE_URL` | Supabase URI (`?sslmode=require`) |
| `DEBUG` | `False` |
| `SECRET_KEY` | Generate in Render |
| `ALLOWED_HOSTS` | API hostname |
| `ALLOW_MOCK_PAYMENTS` | `true` |
| `SEED_DEMO` | `true` |
| `SEED_SHOWCASE` | `true` |
| `DEMO_RESET_ON_START` | `false` |
| `CORS_ALLOWED_ORIGINS` | Static site URL |
| `SECURE_SSL_REDIRECT` | `false` (Render terminates TLS) |

---

## Smoke test (live URL)

1. `https://YOUR-API.onrender.com/api/branding/` → JSON
2. Open **frontend** URL → login `demo_student` / `demo1234`
3. Home shows membership + next lesson (with `SEED_SHOWCASE=true`)
4. Sessions page shows open slots; bookings page has Upcoming tab
5. If 401: check `SEED_DEMO=true` and redeploy API
6. If CORS: fix `CORS_ALLOWED_ORIGINS` exact match

First API call after idle may take ~50s (free tier cold start).

---

## Demo accounts

| Role | Login | Password | Notes |
|------|--------|----------|--------|
| Student | `demo_student` | `demo1234` | Showcase student (with `--showcase`) |
| Teacher | `demo_teacher` | `demo1234` | |
| Staff | `demo_staff` | `demo1234` | Avoid `/admin/` on public URL |

---

## Portfolio site

On **portfolio_site** (Vercel), set:

| Variable | Value |
|----------|--------|
| `PUBLIC_BOOKING_DEMO_URL` | Static site URL |

Redeploy portfolio → **Launch demo** on `/projects/booking-scheduling`.

---

## Re-seed showcase data

From your laptop against Supabase:

```bash
DATABASE_URL='...' python manage.py bootstrap_sandbox --demo --reset --showcase
```

Or set `DEMO_RESET_ON_START=true` temporarily on API redeploy (wipes demo users on container start only; Supabase data persists until reset runs).

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Django login page | You opened the **API** URL — use **booking-frontend** static URL |
| CORS error | `CORS_ALLOWED_ORIGINS` must match static site URL exactly |
| Blank page / 404 on refresh | Add rewrite `/*` → `/index.html` on static site |
| API calls wrong host | Rebuild static site after fixing `VITE_API_BASE` |
| 502 / slow first load | API cold start on free tier — wait ~50s |
| Login fails | Confirm `SEED_DEMO=true` on API; trigger manual redeploy |
| DB connection error | Check Supabase URI, `sslmode=require`, project not paused |
| Empty student home | Set `SEED_SHOWCASE=true` and redeploy, or run `--showcase` seed |

---

## Optional: Vercel instead of Render static

See `frontend/vercel.json`. Same `VITE_API_BASE` + `CORS_ALLOWED_ORIGINS` pattern.

---

## Costs (showcase tier)

| Service | Cost |
|---------|------|
| Supabase | Free (~500 MB; may pause when idle) |
| Render API | Free (cold starts ~50s) |
| Render static | Free |
| **Total** | **$0/mo** for demo |

See [`simplybook-cost-comparison.md`](simplybook-cost-comparison.md) for studio SaaS comparison.
