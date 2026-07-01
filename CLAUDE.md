# CLAUDE.md — booking_scheduling_app

Instructions for AI assistants working in this repo.

---

## Project status

**Full sandbox build complete** (Phases 2–6 + deferred scaffolds). Owner uses this app while studying **CS50P**; bugs and polish go in **`TICKETS.md`**. Primary stack goal: **Django + DRF + React**.

---

## What this is

Django booking/scheduling app: teachers create sessions, students book/cancel, availability blocks, class types, membership gating + mock payments, email + calendar invites, messages, curriculum, and a `progress` app for teacher→student reports. Dual UI:

| UI | URL | Stack |
|----|-----|-------|
| Templates | http://127.0.0.1:8000 | Django views + HTML |
| React | http://127.0.0.1:5173 | Vite + JWT → DRF |

---

## Tech stack

- Python 3.14, Django 5.2, PostgreSQL 16 (SQLite for tests)
- **DRF** + **simplejwt** + **django-cors-headers**
- **WhiteNoise** + **gunicorn** for deploy
- React 19 + Vite (`frontend/`)
- Auth: Django Groups (`student`, `teacher`, `staff`) + session (HTML) or JWT (React)

---

## Commands

```bash
cd ~/repos/booking_scheduling_app
source .venv/bin/activate
pip install -r requirements.txt

python manage.py migrate
python manage.py bootstrap_sandbox            # groups only
python manage.py bootstrap_sandbox --demo     # demo_teacher / demo_student (demo1234)
python manage.py sync_simplybook              # no-op unless SIMPLYBOOK_API_KEY set

python manage.py runserver                    # :8000
python manage.py test                         # SQLite test DB

cd frontend && npm install && npm run dev     # :5173
```

Deploy: `docker compose up --build` (or `Procfile` + gunicorn). Config via `.env` (see `.env.example`).

---

## Architecture rules

1. **Business rules in `scheduling/services/` and `progress/services.py`** — HTML views and DRF call services, never duplicate logic.
2. **Templates / React = display only.**
3. **POST** for writes; **GET** for lists.
4. **Integrations degrade gracefully** — Google/Stripe/SimplyBook are stubs until env creds are set; never crash without them.
5. Target product flow documented in `docs/architecture-and-roadmap.md` §11.

```text
HTML view  ──┐
DRF view   ──├──► services/ ──► models ──► Postgres
React      ──┘         ▲
                       └── JWT or session auth
```

---

## Key paths

```text
config/settings.py            env-driven; DRF, CORS, JWT, email, integrations
config/urls.py                root routes + api/ + progress/
scheduling/models.py          Session, Booking, Membership, ClassType, AvailabilityBlock, Message, CurriculumItem
scheduling/services/          booking, membership, availability, payments, notifications, calendar
scheduling/views/             HTML views (package: dashboard, student, teacher, messages, common)
scheduling/api/               DRF serializers, views, urls, permissions
scheduling/management/commands/  bootstrap_sandbox, sync_simplybook
progress/                     student progress app (models, services, views, api, templates)
integrations/google/          Meet link scaffold
integrations/simplybook/      client + adapter scaffold
frontend/src/                 React SPA (all pages migrated)
TICKETS.md                    bug tracker
docs/architecture-and-roadmap.md
```

---

## API (JWT — `/api/`)

| Method | Path | Role |
|--------|------|------|
| POST | `auth/token/`, `auth/token/refresh/` | any |
| GET | `sessions/open/` | student |
| GET/POST | `bookings/`, `bookings/create/` | student |
| POST | `bookings/<id>/cancel/` | student |
| GET/POST | `membership/` | student |
| GET/POST | `teacher/sessions/` | teacher |
| GET/POST | `teacher/availability/`, `teacher/class-types/` | teacher |
| DELETE | `teacher/availability/<id>/` | teacher |
| GET | `messages/`, `curriculum/` | authenticated |
| GET | `progress/` | student |
| GET/POST | `progress/teacher/` | teacher |

Browsable API: http://127.0.0.1:8000/api/ (session auth if logged in).

---

## Collaboration mode

**Build mode** unless the user asks to learn step-by-step. Prefer focused fixes tied to `TICKETS.md`. Do not commit unless asked.

---

## Not done (needs real credentials / infra)

- Google OAuth consent + token storage (Meet link is a placeholder until then)
- Live Stripe checkout + webhooks (payments are mocked)
- Real SimplyBook API calls (adapter + command are inert)
- Production hosting / DNS / TLS

See `docs/architecture-and-roadmap.md` Phase 6 + Beyond.
