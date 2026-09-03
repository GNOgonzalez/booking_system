# Operations guide

**Last updated:** 2026-08-27  
**Audience:** Engineers and operators deploying or maintaining the app

Install, configure, deploy, and run the booking & scheduling stack. For system design see [`architecture-and-roadmap.md`](./architecture-and-roadmap.md). For a plain-English code tour see [`learn-the-app.md`](./learn-the-app.md).

Companion docs:

| Doc | Use for |
|-----|---------|
| [`architecture-and-roadmap.md`](./architecture-and-roadmap.md) | Models, API, product flows |
| [`client-handover.md`](./client-handover.md) | Client discovery, delivery checklist, credential transfer |
| [`portfolio-demo-deploy.md`](./portfolio-demo-deploy.md) | Public demo on Render (free tier) |
| [`security.md`](./security.md) | Auth, CSP, homework file privacy |
| [`.env.example`](../.env.example) | Environment variable template |
| [`README.md`](../README.md) | Dev quickstart |

---

## 1. What you are operating

### Product shape

- **One deployment = one studio.** Each customer gets their own Postgres database, environment file, and domain(s). This is **not** multi-tenant SaaS (many studios on one shared database) unless you build that separately — see [`future-features.md`](./future-features.md) §10.
- **Primary UI:** React single-page app (students, teachers, staff).
- **Secondary UI:** Django HTML templates at the same backend URL (legacy; still works).
- **Backend:** Django 5.2 + Django REST Framework + JWT auth for the React app.

### Main user roles

| Role | Access |
|------|--------|
| **Student** | Book sessions, membership, homework, progress, class requests |
| **Teacher** | Sessions, availability, class requests, feedback, homework (permissions vary) |
| **Staff** | Studio admin: users, plans, branding, glossary, class roadmap, reports |
| **Django superuser** | Break-glass access to `/admin/` — use sparingly |

Teacher capabilities (create sessions, write reports, use AI, etc.) are controlled per teacher by staff.

### External services (optional but typical in production)

| Service | Purpose |
|---------|---------|
| **PostgreSQL** | Primary database (required) |
| **SMTP / transactional email** | Booking and class-request notifications |
| **Stripe** | Student membership and ticket-pack purchases |
| **Google OAuth** | Real Google Meet links and Calendar events (optional) |

Without credentials, the app still runs: emails go to the server console, payments use mock mode in development only, Meet links are placeholders.

---

## 2. Architecture (one page)

```text
┌─────────────────┐     JWT (HTTPS)      ┌──────────────────────────────┐
│  React SPA      │ ───────────────────► │  Django + DRF (:8000)        │
│  (static host   │                      │  gunicorn in production      │
│   or CDN)       │                      └──────────────┬───────────────┘
└─────────────────┘                                     │
                                                        ▼
                                              ┌─────────────────┐
                                              │  PostgreSQL 16  │
                                              └─────────────────┘
                                                        │
                                              ┌─────────────────┐
                                              │  media/ volume  │
                                              │  (homework,     │
                                              │   blog, logo)   │
                                              └─────────────────┘
```

**Business logic lives in Python services**, not in React:

```text
React  →  /api/...  →  scheduling/api/ or progress/api  →  services/  →  models  →  Postgres
```

When changing booking rules, membership logic, or emails, edit `scheduling/services/` (or `progress/`), then update tests.

---

## 3. Requirements

### Software

| Component | Version (tested) |
|-----------|------------------|
| Python | 3.12+ (project targets 3.14; CI uses 3.12) |
| PostgreSQL | 16 |
| Node.js | 22+ (frontend build; CI uses 22) |
| Docker + Compose | Optional but recommended for first production deploy |

### Hardware (small studio)

For tens of teachers and hundreds of students:

- **App server:** 1 vCPU, 1–2 GB RAM minimum (2 vCPU / 4 GB comfortable)
- **Postgres:** managed service preferred (RDS, Cloud SQL, Supabase, etc.)
- **Disk:** persistent volume for `media/` — homework uploads; size depends on usage

### Domains

Typical setup:

| Host | Serves |
|------|--------|
| `app.studio.example.com` | React static files (or same origin as API) |
| `api.studio.example.com` | Django/gunicorn (if split) |

Single-origin (API + static on one domain) is simpler for CORS. Split-origin requires correct `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS`.

---

## 4. Initial setup (development)

Use this to verify the stack before production.

```bash
cd booking_scheduling_app
cp .env.example .env          # edit DB credentials
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt   # optional: ruff, etc.

# PostgreSQL must be running locally (or use docker compose up db)
python manage.py migrate
python manage.py bootstrap_sandbox --demo   # demo users — dev only

python manage.py runserver                  # http://127.0.0.1:8000
```

**Frontend (second terminal):**

```bash
cd frontend
npm install
npm run dev                                   # http://127.0.0.1:5173
```

**Demo logins** (after `--demo`): `demo_student`, `demo_teacher`, `demo_staff` — password `demo1234`.

**Verify:**

```bash
python manage.py test                       # SQLite test DB; no Postgres perms needed
cd frontend && npm run build
```

---

## 5. Production deployment

### Option A — Docker Compose (simplest)

```bash
cp .env.example .env
# Set DEBUG=False, SECRET_KEY, ALLOWED_HOSTS, DB_*, production URLs

docker compose up --build -d
```

`docker-compose.yml` runs:

- **db** — Postgres 16 with named volume `pgdata`
- **web** — builds `Dockerfile`, runs migrate + gunicorn on port 8000

The Docker image does **not** include the React build or a reverse proxy. You still need to:

1. Build the frontend (§6) and host static files.
2. Put nginx (or a platform load balancer) in front for TLS.
3. Mount or attach persistent storage for `media/`.

### Option B — Platform with Procfile (Heroku, Railway, Fly.io, etc.)

```text
release: python manage.py migrate --noinput
web: gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000}
```

- Attach a **Postgres** add-on.
- Set all env vars from §7.
- Add a **persistent volume** or object storage for `media/` if the platform’s filesystem is ephemeral.

### Reverse proxy (nginx example)

TLS termination and routing (adjust paths for your layout):

```nginx
# API
server {
    listen 443 ssl;
    server_name api.studio.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $remote_addr;
    }

    # Public media only — NEVER expose homework
    location /media/blog/     { alias /app/media/blog/; }
    location /media/branding/ { alias /app/media/branding/; }
}

# React static site
server {
    listen 443 ssl;
    server_name app.studio.example.com;

    root /var/www/booking-app/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

**Homework files** (`media/homework/`) must **not** be mapped publicly. Downloads go through the authenticated API: `/api/progress/homework/entries/<id>/download/`.

---

## 6. Frontend production build

The React app is built separately from Django.

```bash
cd frontend

# Point at production API (required when API is on another host)
echo 'VITE_API_BASE=https://api.studio.example.com' > .env.production

npm ci
npm run build
```

Output: `frontend/dist/` — deploy to static hosting, nginx, S3+CloudFront, Netlify, etc.

| Variable | When |
|----------|------|
| `VITE_API_BASE` | Set when the API is **not** same-origin. Omit if React and API share one domain. |

After deploy, confirm in the browser:

- Login works (JWT issued).
- API calls hit the correct host (Network tab).
- No CORS errors (fix `CORS_ALLOWED_ORIGINS` on backend).

---

## 7. Environment variables

Copy [`.env.example`](../.env.example). **Never commit `.env`.**

### Required for production

| Variable | Example | Notes |
|----------|---------|-------|
| `SECRET_KEY` | long random string | Generate: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `DEBUG` | `False` | Must be false in production |
| `ALLOWED_HOSTS` | `api.studio.example.com` | Comma-separated |
| `DB_NAME` | `booking_prod` | |
| `DB_USER` | | |
| `DB_PASSWORD` | | |
| `DB_HOST` | | Managed Postgres hostname |
| `DB_PORT` | `5432` | |
| `CORS_ALLOWED_ORIGINS` | `https://app.studio.example.com` | React app origin(s) |
| `CSRF_TRUSTED_ORIGINS` | `https://app.studio.example.com,https://api.studio.example.com` | Include API if using session/cookies on HTML views |

### Recommended for production

| Variable | Purpose |
|----------|---------|
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | Real notification emails |
| `DEFAULT_FROM_EMAIL` | From address students see |
| `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET` | Paid memberships |
| `SECURE_SSL_REDIRECT` | `True` (default when not DEBUG) |
| `SECURE_HSTS_SECONDS` | e.g. `3600` |

### Optional integrations

| Variable | Purpose |
|----------|---------|
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` | Meet + Calendar |
| `ZOOM_*` | Zoom links (scaffold) |
| `STUDIO_LLM_API_KEY` | AI-assisted session notes (or staff stores key in DB) |
| `JWT_ACCESS_MINUTES`, `JWT_REFRESH_DAYS` | Token lifetimes (default refresh 1 day in prod) |
| `CSP_POLICY` | Override Content-Security-Policy header |

### Development only

| Variable | Notes |
|----------|-------|
| `DEBUG=True` | Enables Django debug, serves `/media/` directly |
| Mock payments | Work when `DEBUG=True` and Stripe unset. **Blocked when `DEBUG=False`** unless `ALLOW_MOCK_PAYMENTS=true` (testing only — do not use for real customers) |

**Restart the Django process after any `.env` change.**

---

## 8. First-run checklist (new studio)

Run once per deployment. **Do not use `--demo` for a live customer.**

### 8.1 Infrastructure

- [ ] Postgres created and reachable
- [ ] `.env` filled (§7)
- [ ] `python manage.py migrate`
- [ ] `python manage.py bootstrap_sandbox` (creates `student`, `teacher`, `staff` groups only)
- [ ] `python manage.py createsuperuser` (break-glass admin)
- [ ] Frontend built and deployed (§6)
- [ ] TLS certificates valid
- [ ] Persistent `media/` storage attached

### 8.2 Integrations

- [ ] SMTP sending test email (book a session or use Django shell)
- [ ] Stripe test mode: checkout + webhook (§9)
- [ ] Google OAuth (if using Meet) — redirect URI matches production URL exactly

### 8.3 Studio configuration (staff user in the app)

Log in as staff (create via superuser + add to `staff` group, or promote in Django admin).

| Task | App location |
|------|----------------|
| Studio name and logo | Staff → Branding |
| Terminology (student → client, etc.) | Staff → Glossary |
| Class roadmap (subject / level / focus / topics) | Staff → Class roadmap |
| Membership plans and pricing | Staff → Memberships |
| Create teacher accounts | Staff → Teachers |
| Set teacher permissions | Staff → Teachers → Permissions |
| Create student accounts (or enable self-registration at `/register`) | Staff → Students |

### 8.4 Teacher setup

Each teacher (or staff on their behalf):

- [ ] **Classes** — offerings linked to catalog
- [ ] **Availability** — weekly blocks (drives scheduling slots and class requests)
- [ ] **Sessions** — publish open sessions for students to book
- [ ] **Google Calendar** (optional) — Profile → Connect for real Meet links

### 8.5 Go-live smoke test

1. Student registers or is created → purchases membership (Stripe live when ready).
2. Student books an open session → receives confirmation email.
3. Student submits a class request → teacher receives email → approves → student receives booking email.
4. Teacher assigns homework → student uploads file → download works.
5. Staff can view schedule and reports.

---

## 9. Integration setup (detailed)

### 9.1 Email (SMTP)

Without `EMAIL_HOST`, emails print to the server log only.

**Gmail (small pilots):**

1. Enable 2-Step Verification on the Google account.
2. Create an **App password** (Google Account → Security → App passwords).
3. In `.env`:

```bash
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=you@gmail.com
EMAIL_HOST_PASSWORD=xxxx xxxx xxxx xxxx   # spaces are stripped automatically
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=Studio Name <you@gmail.com>
```

**Production recommendation:** Use a transactional provider (SendGrid, Postmark, Amazon SES) with SPF/DKIM on the studio’s domain.

### 9.2 Stripe (student payments)

Payments go to the **studio’s** Stripe account, not the platform vendor’s.

1. [Stripe Dashboard](https://dashboard.stripe.com) → API keys (test first, then live).
2. Add to `.env`:

```bash
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
```

3. **Webhook** — Stripe Dashboard → Developers → Webhooks → Add endpoint:

   `https://api.studio.example.com/api/payments/stripe/webhook/`

   Events: at minimum `checkout.session.completed` (and any others your deployment documents).

4. Copy signing secret → `STRIPE_WEBHOOK_SECRET=whsec_...`

**Local testing with Stripe CLI:**

```bash
stripe listen --forward-to http://127.0.0.1:8000/api/payments/stripe/webhook/
```

Test card: `4242 4242 4242 4242`, any future expiry, any CVC.

### 9.3 Google (Meet + Calendar)

1. [Google Cloud Console](https://console.cloud.google.com) → create project → enable Calendar API.
2. OAuth consent screen (External → publish when ready for non-test users).
3. Credentials → OAuth client (Web application).
4. Authorized redirect URI must **exactly** match:

```bash
GOOGLE_REDIRECT_URI=https://api.studio.example.com/integrations/google/callback/
```

Use `127.0.0.1`, not `192.168.x.x` — Google blocks private LAN IPs for OAuth.

5. Teachers/staff connect via **Profile → Connect Google Calendar** in the app.

Without Google credentials, sessions still get placeholder Meet URLs.

---

## 10. Ongoing maintenance

### 10.1 Regular schedule

| Task | Command / action | Frequency |
|------|------------------|-----------|
| Database backup | `./scripts/backup_db.sh` or provider snapshots | Daily |
| Purge expired homework files | Container start (`scripts/start.sh`) + lazy purge on homework list | On boot (Render Free); cron once you have a paid instance |
| OS / dependency security updates | `pip`, `npm`, base image | Monthly |
| Review Stripe webhook logs | Stripe Dashboard | After payment issues |
| Disk usage on `media/` | Monitor volume | Monthly |

**Render Free:** there is no cron. `scripts/start.sh` runs `purge_expired_homework` after migrate. Free instances spin down on idle and restart on the next request, so this fires regularly. Keep the lazy purge on homework list/download as the in-session backstop.

Do **not** run the purge from GitHub Actions against the production database: it would clear the file pointers in Postgres while `MEDIA_ROOT` is the runner's empty directory, leaving orphaned files on Render.

**Paid instance cron** (once you have a persistent disk):

```cron
0 3 * * * cd /app && /app/.venv/bin/python manage.py purge_expired_homework >> /var/log/booking-purge.log 2>&1
```

### 10.2 Deploying a new release

```bash
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt

python manage.py migrate --noinput
python manage.py collectstatic --noinput   # if serving Django admin/static

cd frontend && npm ci && npm run build     # deploy dist/ to static host

# Restart gunicorn / Docker container
docker compose up --build -d web           # if using Compose
```

**Pre-deploy checks (match CI):**

```bash
python manage.py test
ruff check scheduling progress integrations config
cd frontend && npm run build
```

### 10.3 Backups and recovery

**Supabase Free has no managed backups.** Pro ($25/mo) keeps 7 days of daily snapshots in the dashboard (Database → Backups). Until you upgrade, take your own off-site dumps.

**Logical dump (works on Free or Pro):**

```bash
# pg_dump must be ≥ Supabase's Postgres major version (currently 17).
# macOS: brew upgrade libpq && brew link --force libpq

# From the repo root — reads DATABASE_URL from .env
./scripts/backup_db.sh              # writes backups/YYYY-MM-DD_HHMMSS_host.dump
./scripts/backup_db.sh --keep 14    # also delete dumps older than 14 days
```

`backups/` is gitignored (dumps contain student PII). Copy a recent dump somewhere off your laptop too (encrypted drive, object storage).

**Daily cron on your Mac** (optional):

```cron
0 3 * * * cd /Users/YOU/repos/booking_scheduling_app && ./scripts/backup_db.sh --keep 14 >> /tmp/booking-backup.log 2>&1
```

**Restore Postgres** (practise on a staging DB first — this drops objects in the target):

```bash
./scripts/restore_db.sh backups/YYYY-MM-DD_HHMMSS_host.dump
# prompts you to type the target hostname before continuing
```

**Media files** are separate from the database. On Render’s ephemeral disk they do not survive a redeploy — attach a persistent disk (or S3) first, then:

```bash
tar czf backups/media_$(date +%F).tar.gz media/
```

Restore `media/` to the same path configured as `MEDIA_ROOT`.

### 10.4 Free-plan operations (Render + Supabase)

What this stack does today without a paid instance:

| Piece | How it works on free |
|-------|----------------------|
| Health check | Render probes `GET /healthz` — process only, no database. `/readyz` checks Postgres separately; do not point Render at it, or a paused Supabase project becomes a restart loop. |
| Homework purge | `scripts/start.sh` after migrate. Files live on the ephemeral disk. |
| Gunicorn | `WEB_CONCURRENCY=2` (512 MB). Raise later without a code change. |
| Logging | stdout, `LOG_LEVEL` (default `INFO`). |
| Sentry | Set `SENTRY_DSN` when you want it; unset keeps it inert. |
| Backups | `./scripts/backup_db.sh` — Supabase Free has no managed snapshots. |

What changes when you upgrade: a persistent disk (or S3) for media, a Render cron instead of on-boot purge, a paid instance to remove ~50s cold starts, and Supabase Pro for dashboard restores.

### 10.5 User administration

| Need | How |
|------|-----|
| Reset student password | Staff → Students, or Django admin |
| Deactivate user | Set `is_active=False` in admin — blocks login immediately |
| Break-glass | Django superuser → `/admin/` |
| Re-seed demo data | **Dev only:** `python manage.py bootstrap_sandbox --demo --reset` |

---

## 11. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| 502 / app not responding | gunicorn down, bad deploy | Check container/process logs; restart |
| `DisallowedHost` | Missing `ALLOWED_HOSTS` | Add domain to env; restart |
| CORS error in browser | Wrong `CORS_ALLOWED_ORIGINS` | Must match React URL exactly (scheme + host) |
| Login works locally, not prod | `VITE_API_BASE` wrong or missing | Rebuild frontend with correct API URL |
| “Pay with Stripe” hidden | `STRIPE_SECRET_KEY` unset | Add keys; restart Django |
| Payment OK, membership inactive | Webhook not received | Check `STRIPE_WEBHOOK_SECRET`, endpoint URL, Stripe event log |
| No emails | `EMAIL_HOST` blank or SMTP auth failure | Set SMTP; check logs; test with small send |
| Meet link is fake/placeholder | Google not connected | Complete OAuth; teacher connects in Profile |
| Teacher cannot create sessions | Missing permission | Staff → teacher → enable `manage_schedule` |
| Student cannot book | No membership/tickets/plan mismatch | Check `/api/membership/`; plan class access |
| Homework download 403 | Not a participant, or file expired | 7-day TTL; re-upload if expired |
| Migration error on deploy | Skipped migrate | Run `python manage.py migrate`; never skip release step |

**Logs:**

- Docker: `docker compose logs -f web`
- gunicorn: platform log stream or `/var/log/...`
- Email: Django logs “Skipping email … empty recipient” when user has no email address

---

## 12. Security handoff (for IT)

Read [`security.md`](./security.md) in full. Summary for operations:

| Topic | Current behavior |
|-------|------------------|
| **React auth** | JWT access + refresh tokens in **sessionStorage** (per browser tab) |
| **XSS** | User content rendered as plain text; no unsanitized HTML |
| **CSP** | Enabled on Django responses when `DEBUG=False` |
| **Homework files** | Private — API download only; do not expose `/media/homework/` |
| **HTTPS** | Required in production (`SECURE_SSL_REDIRECT`) |
| **Inactive users** | Blocked at JWT and API permission layers |
| **Mock payments** | Disabled when `DEBUG=False` unless explicitly overridden |

**Planned hardening (not required to operate today):** httpOnly cookie auth — see [`future-features.md`](./future-features.md) §9.

**Stripe PCI:** Card data never touches your server; Stripe Checkout handles payments.

---

## 13. What is not visible in the UI

Operators and new engineers need the repo — not just the React app:

| Area | Location |
|------|----------|
| All business rules | `scheduling/services/`, `progress/services.py`, `progress/homework_services.py` |
| API routes | `scheduling/api/urls.py`, `progress/api_urls.py` |
| Models / schema | `scheduling/models.py`, `progress/models.py`, migrations |
| Tests (behavior spec) | `scheduling/tests.py`, `progress/tests.py` |
| CI pipeline | `.github/workflows/ci.yml` |

Changing booking or billing behavior without reading services will cause UI/backend drift.

---

## 14. Responsibility split (typical deploy)

| Concern | Owner |
|---------|--------|
| Server, Postgres, TLS, backups, `.env` | Operator / platform |
| `migrate`, release deploy, `collectstatic` | Operator (commands in §10.2) |
| Studio config (plans, teachers, branding) | Staff users in the app |
| Stripe / Google keys and webhooks | Operator rotates; staff uses in-app OAuth |
| Application code changes | Developer |

---

## 15. Quick reference commands

```bash
# Activate environment
source .venv/bin/activate

# Database
python manage.py migrate
python manage.py bootstrap_sandbox              # groups only (production first run)
python manage.py createsuperuser

# Maintenance
python manage.py purge_expired_homework

# Quality (match CI)
python manage.py test
ruff check scheduling progress integrations config
cd frontend && npm ci && npm run build

# Docker
docker compose up --build -d
docker compose logs -f web
```

---

## 16. Documentation index

| Document | Purpose |
|----------|---------|
| **This file** | Deploy, env, maintenance |
| [`architecture-and-roadmap.md`](./architecture-and-roadmap.md) | System design, API, flows |
| [`learn-the-app.md`](./learn-the-app.md) | Plain-English code tour (owner / new dev) |
| [`security.md`](./security.md) | Auth and privacy |
| [`glossary.md`](./glossary.md) | Terminology |
| [`future-features.md`](./future-features.md) | Backlog |
| [`README.md`](../README.md) | Dev quickstart |

---

*Questions about this guide: update this file in the repo so the next operator inherits the answer.*
