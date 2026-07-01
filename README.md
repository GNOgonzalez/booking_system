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
integrations/      google/ (Meet) + simplybook/ (adapter) scaffolds
frontend/          React SPA (Vite)
docs/              architecture & roadmap, learning notes
TICKETS.md         bug tracker
```

## Configuration

All config is environment-driven — see `.env.example`. Integrations stay inert until you
provide credentials:

| Feature | Enable with | Without it |
|---------|-------------|------------|
| Email (SMTP) | `EMAIL_HOST=...` | emails print to console |
| Stripe payments | `STRIPE_SECRET_KEY=...` | membership purchase is mocked |
| Google Meet | `GOOGLE_CLIENT_ID=...` | placeholder Meet links |
| SimplyBook sync | `SIMPLYBOOK_API_KEY=...` | `sync_simplybook` is a no-op |

## Deploy

```bash
docker compose up --build      # web + postgres
```

Or use the `Procfile` (release runs migrations, web runs gunicorn). Set `DEBUG=False`,
`SECRET_KEY`, `ALLOWED_HOSTS`, and DB env vars in production.

## Roadmap & design

See [`docs/architecture-and-roadmap.md`](docs/architecture-and-roadmap.md). Bugs and polish are
tracked in [`TICKETS.md`](TICKETS.md).
