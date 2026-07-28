# Portfolio demo deployment (Render + Vercel)

Deploy the **API on Render** and the **React SPA on Vercel**. The portfolio site only needs the frontend URL.

**Prerequisite:** `render.yaml`, `Dockerfile`, and `frontend/vercel.json` must be on GitHub (`main`).

---

## 1. Push deploy files to GitHub

From the repo root:

```bash
git add render.yaml Dockerfile docs/portfolio-demo-deploy.md frontend/vercel.json
git commit -m "Add Render blueprint and portfolio demo deploy config"
git push origin main
```

---

## 2. Backend — Render (Blueprint)

1. [Render Dashboard](https://dashboard.render.com) → **New** → **Blueprint**.
2. Connect **GitHub** → repo `GNOgonzalez/booking_system` (or your fork).
3. Render reads `render.yaml` and proposes:
   - **booking-db** — PostgreSQL (free tier; expires after 90 days on free — upgrade or export before then)
   - **booking-api** — Docker web service
   - **booking-demo-reset** — nightly cron (may require a paid plan; skip if Blueprint fails — see §5)
4. Click **Apply**.
5. Wait for **booking-api** deploy (first Docker build ~5–10 min).
6. Copy the API URL, e.g. `https://booking-api-xxxx.onrender.com`.

### Env vars on **booking-api**

| Variable | Value |
|----------|--------|
| `CORS_ALLOWED_ORIGINS` | Your Vercel frontend URL, e.g. `https://booking-scheduling.vercel.app` (set after step 3; no trailing slash) |
| `ALLOWED_HOSTS` | Optional — Render hostname is added automatically via `RENDER_EXTERNAL_HOSTNAME` |

`SECRET_KEY`, database vars, `DEBUG=False`, and `ALLOW_MOCK_PAYMENTS=true` come from the blueprint.

### Seed demo data (once)

**booking-api** → **Shell**:

```bash
python manage.py bootstrap_sandbox --demo
```

Log in with `demo_student` / `demo1234` (also `demo_teacher`, `demo_staff`).

### Smoke test

```bash
curl -sS "https://booking-api-xxxx.onrender.com/api/branding/"
```

Should return JSON. First request after idle may take ~50s (free tier spin-down).

---

## 3. Frontend — Vercel

1. [Vercel](https://vercel.com) → **Add New Project** → import the same GitHub repo.
2. **Root Directory:** `frontend`
3. **Environment variable:**

   | Name | Value |
   |------|--------|
   | `VITE_API_BASE` | `https://booking-api-xxxx.onrender.com` (no trailing slash) |

4. Deploy. Copy the Vercel URL (e.g. `https://booking-scheduling.vercel.app`).
5. Back on Render **booking-api** → **Environment** → set `CORS_ALLOWED_ORIGINS` to that Vercel URL → **Save** (redeploys).

Open the Vercel URL → sign in as `demo_student` / `demo1234`.

---

## 4. Portfolio site

On your **portfolio** Vercel project, set:

| Variable | Value |
|----------|--------|
| `PUBLIC_BOOKING_DEMO_URL` | Vercel booking frontend URL from step 3 |

The **Launch demo** button appears on `/projects/booking-scheduling`.

---

## 5. Nightly demo reset (optional)

`render.yaml` includes cron: `python manage.py bootstrap_sandbox --demo --reset` at 05:00 UTC.

- If Blueprint rejects the cron job on free tier, delete **booking-demo-reset** in Render or remove the cron block from `render.yaml` and redeploy.
- Fallback: enable [`.github/workflows/demo-reset.yml`](../.github/workflows/demo-reset.yml) with repo secrets + `USE_GITHUB_DEMO_RESET=true`.

---

## Demo accounts

| Role | Login | Password |
|------|--------|----------|
| Student | `demo_student` | `demo1234` |
| Teacher | `demo_teacher` | `demo1234` |
| Staff | `demo_staff` | `demo1234` |

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Health check failed | Ensure latest `Dockerfile` uses `${PORT}` and health path is `/api/branding/` |
| CORS error in browser | `CORS_ALLOWED_ORIGINS` must exactly match Vercel URL (https, no trailing slash) |
| 502 / slow first load | Free tier cold start — wait ~50s and retry |
| Login works locally, not prod | Re-run `bootstrap_sandbox --demo` in Render Shell |
| Homework uploads vanish | Render disk is ephemeral — expected for demo; use S3 for real prod |
