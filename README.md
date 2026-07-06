# Booking & Scheduling App

Django + DRF + React booking app. Teachers publish sessions from their availability and class
catalog; students with an active membership book, cancel, get email + calendar invites, and track
progress. Dual UI: server-rendered Django templates **and** a React SPA on the JSON API.

## Stack

- Python 3.14, Django 5.2, PostgreSQL 16 (SQLite for tests)
- Django REST Framework + SimpleJWT + django-cors-headers
- WhiteNoise + gunicorn (deploy)
- React 19 + Vite (`frontend/`)

## Quickstart

```bash
# 1. Backend
cp .env.example .env            # fill DB creds
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py bootstrap_sandbox --demo   # demo_teacher / demo_student  (demo1234)
python manage.py runserver                  # http://127.0.0.1:8000

# 2. Frontend (separate terminal)
cd frontend
npm install
npm run dev                                 # http://127.0.0.1:5173
```

| Surface | URL |
|---------|-----|
| Django templates | http://127.0.0.1:8000 |
| Django admin | http://127.0.0.1:8000/admin/ |
| Browsable API | http://127.0.0.1:8000/api/ |
| React SPA | http://127.0.0.1:5173 |

## Testing

```bash
python manage.py test          # runs on a SQLite test DB (no Postgres perms needed)
```

## Project structure

```text
config/            settings (env-driven), urls, wsgi
scheduling/        core app: models, services, HTML views, DRF api, templates
progress/          student progress reports app
integrations/      google/ (Meet), zoom/, stripe/ (payment scaffolds)
frontend/          React SPA (Vite)
docs/              architecture, roadmap, audit plan
docs/learn/        CS50P / Django self-study (optional)
TICKETS.md         bug tracker
```

## Configuration

All config is environment-driven — see `.env.example`. Integrations stay inert until you
provide credentials:

| Feature | Enable with | Without it |
|---------|-------------|------------|
| Email (SMTP) | `EMAIL_HOST=...` | emails print to console |
| Stripe payments | `STRIPE_SECRET_KEY` + `STRIPE_PUBLISHABLE_KEY` | mock purchases in **DEBUG only**; blocked in production unless `ALLOW_MOCK_PAYMENTS=true` |
| Stripe webhooks | `STRIPE_WEBHOOK_SECRET` + forward to `/api/payments/stripe/webhook/` | membership activates after `checkout.session.completed` |
| Google Meet | `GOOGLE_CLIENT_ID=...` | placeholder Meet links |

## Deploy

```bash
docker compose up --build      # web + postgres
```

Or use the `Procfile` (release runs migrations, web runs gunicorn). Set `DEBUG=False`,
`SECRET_KEY`, `ALLOWED_HOSTS`, and DB env vars in production. Configure **Stripe** for
membership purchases — mock `POST /api/membership/` is disabled when `DEBUG=False` unless
`ALLOW_MOCK_PAYMENTS=true` (testing only; do not use in real production).

### Media files in production (privacy)

WhiteNoise serves **static files only** — it never serves `MEDIA_ROOT`. Django itself serves
`/media/` only when `DEBUG=True`. In production:

| Path | Visibility | How to serve |
|------|------------|--------------|
| `media/homework/` | **Private** — participants + staff only | Never map publicly. Files are streamed through the authenticated API (`/api/progress/homework/entries/<id>/download/`). |
| `media/blog/` | Public (home-page images) | Map in nginx/CDN, or serve from object storage |
| `media/branding/` | Public (sign-in logo) | Same as blog |

If you add an nginx `location /media/` block, restrict it to the public subfolders:

```nginx
location /media/blog/     { alias /app/media/blog/; }
location /media/branding/ { alias /app/media/branding/; }
# NO location for /media/homework/ — must stay API-only
```

For real hosting, prefer object storage (e.g. S3) with a **private** bucket for homework and
public bucket/prefix for blog + branding. Also mount `media/` on a persistent volume — the
Docker image filesystem is ephemeral.

## Stripe (local testing)

1. Add keys to `.env` (from [Stripe Dashboard](https://dashboard.stripe.com/test/apikeys)):
   ```bash
   STRIPE_SECRET_KEY=sk_test_...
   STRIPE_PUBLISHABLE_KEY=pk_test_...
   ```
2. Install [Stripe CLI](https://stripe.com/docs/stripe-cli) and forward webhooks:
   ```bash
   stripe listen --forward-to http://127.0.0.1:8000/api/payments/stripe/webhook/
   ```
   Copy the webhook signing secret into `.env` as `STRIPE_WEBHOOK_SECRET=whsec_...`
3. Log in as a student → **Membership** → **Pay with Stripe** (test card `4242 4242 4242 4242`).

Unset `STRIPE_SECRET_KEY` to use mock purchases in local dev (`DEBUG=True` only). In production
(`DEBUG=False`), mock purchases are blocked unless `ALLOW_MOCK_PAYMENTS=true`.

## Roadmap & design

See [`docs/architecture-and-roadmap.md`](docs/architecture-and-roadmap.md). Bugs and polish are
tracked in [`TICKETS.md`](TICKETS.md).
