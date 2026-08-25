# CLAUDE.md — booking_scheduling_app

Instructions for AI assistants working in this repo.

---

## Project status

**Full sandbox build complete** (Phases 2–6 + deferred scaffolds + staff studio admin, metrics, glossary, homework). Owner uses this app while studying **CS50P**; bugs and polish go in **`TICKETS.md`**. Primary stack: **Django + DRF + React**.

---

## What this is

Django booking/scheduling app: teachers manage sessions, classes, and availability; students book/cancel; membership gating + mock payments; email + calendar invites; messages, curriculum; `progress` app for feedback, subject dashboards, and homework. Dual UI:

| UI | URL | Stack |
|----|-----|-------|
| Templates | http://127.0.0.1:8000 | Django views + HTML (**legacy** — React SPA is primary) |
| React | http://127.0.0.1:5173 | Vite + JWT → DRF |

---

## Tech stack

- Python 3.14, Django 5.2, PostgreSQL 16 (SQLite for tests)
- **DRF** + **simplejwt** + **django-cors-headers**
- **WhiteNoise** + **gunicorn** for deploy
- React 19 + Vite (`frontend/`)
- Auth: Django Groups (`student`, `teacher`, `staff`) + session (HTML) or JWT (React)
- Media: `MEDIA_ROOT` for homework files (7-day purge)

---

## Commands

```bash
cd ~/repos/booking_scheduling_app
source .venv/bin/activate
pip install -r requirements.txt

python manage.py migrate
python manage.py bootstrap_sandbox            # groups only
python manage.py bootstrap_sandbox --demo     # demo users (demo1234)
python manage.py bootstrap_sandbox --demo --showcase  # portfolio demo seed
python manage.py purge_expired_homework       # delete homework files past 7 days

python manage.py runserver                    # :8000
python manage.py test                         # SQLite test DB

cd frontend && npm install && npm run dev     # :5173
```

Deploy: `docker compose up --build` (or `Procfile` + gunicorn). Config via `.env` (see `.env.example`).

**Demo accounts:** `demo_teacher`, `demo_student`, `demo_staff` (+ `demo_student_2`–`_4`) — all `demo1234`.

---

## Architecture rules

1. **Business rules in `scheduling/services/` and `progress/services.py` / `progress/homework_services.py`** — HTML views and DRF call services, never duplicate logic.
2. **Templates / React = display only.**
3. **POST** for writes; **GET** for lists.
4. **Integrations degrade gracefully** — Google/Stripe/Zoom are stubs until env creds are set; never crash without them.
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
config/settings.py            env-driven; DRF, CORS, JWT, MEDIA, integrations
config/urls.py                root routes + api/ + progress/ + media (DEBUG)
scheduling/models.py          Session, Booking, ClassOffering, TeacherPermission, StudioGlossary, …
                              (`ClassType` is legacy — use `ClassOffering` for new work)
scheduling/services/          booking, membership, availability, classes, users, glossary, staff, teacher_permissions
scheduling/api/               DRF views, staff_views, glossary_views, serializers, permissions
scheduling/views/             HTML views (package)
progress/models.py            SessionFeedback, ScoreDimension, HomeworkAssignment, HomeworkEntry
progress/services.py          metrics, feedback, student_dashboard
progress/homework_services.py file exchange, journal, purge
progress/api/ + api_urls.py     DRF for progress + homework + staff metrics
frontend/src/pages/           React SPA (all pages)
frontend/src/hooks/           useTeacherScope, useGlossary, useScoreDimensions, …
docs/architecture-and-roadmap.md
docs/operations-guide.md
docs/learn-the-app.md         Plain-English tour; CS50-aligned study path
docs/glossary.md
```

---

## API (JWT — `/api/`)

### Auth & account

| Method | Path | Role |
|--------|------|------|
| POST | `auth/token/`, `auth/token/refresh/` | any |
| GET/PATCH | `me/` | authenticated |
| POST | `me/password/` | authenticated |
| GET | `glossary/` | authenticated |

### Student

| Method | Path | Role |
|--------|------|------|
| GET | `student/home/` | student |
| GET | `sessions/open/` | student |
| GET/POST | `bookings/`, `bookings/create/` | student |
| POST | `bookings/<id>/cancel/` | student |
| GET/POST | `membership/` | student |

### Teacher

| Method | Path | Role |
|--------|------|------|
| GET/POST | `teacher/sessions/` | teacher |
| PATCH/DELETE | `teacher/sessions/<id>/` | teacher |
| GET/POST | `teacher/classes/` | teacher (+ `manage_classes`) |
| PATCH | `teacher/classes/<id>/` | teacher |
| GET/POST | `teacher/availability/` | teacher (+ `manage_availability`) |
| PATCH/DELETE | `teacher/availability/<id>/` | teacher |
| GET | `teacher/permissions/` | teacher |

### Staff (`scheduling`)

| Method | Path | Role |
|--------|------|------|
| GET | `staff/teachers/`, `staff/students/`, `staff/schedule/` | staff |
| GET | `staff/alerts/` | staff |
| POST | `staff/alerts/mark-read/` | staff |
| PATCH | `staff/teachers/<id>/`, `staff/students/<id>/` | staff |
| GET/PATCH | `staff/glossary/` | staff |
| GET/PATCH | `staff/llm/` | staff |
| POST | `staff/llm/test/` | staff |
| POST | `teacher/ai/suggest-feedback/` | teacher (+ `use_ai`) |
| GET | `teacher/ai/status/` | teacher/staff |
| POST | `staff/classes/` | staff |
| `staff/teachers/<id>/sessions|classes|availability|permissions/…` | staff |

### Shared

| Method | Path | Role |
|--------|------|------|
| GET | `messages/`, `curriculum/` | authenticated |

### Progress (`/api/progress/`)

| Method | Path | Role |
|--------|------|------|
| GET | `/`, `dashboard/`, `feedback/` | student |
| GET/POST | `homework/`, `homework/<id>/entries/` | student |
| GET | `homework/entries/<id>/download/` | participant |
| GET/POST | `feedback/teacher/` | teacher (+ `write_reports`) |
| PATCH/DELETE | `feedback/teacher/<id>/` | teacher |
| GET/POST | `homework/teacher/` | teacher (+ `assign_homework`) |
| GET | `score-dimensions/` | authenticated |
| Staff metrics | `staff/score-dimensions/…` | staff |
| Staff per-teacher | `staff/teachers/<id>/feedback|homework/…` | staff |

Browsable API: http://127.0.0.1:8000/api/

---

## Teacher permissions (staff-controlled)

| Key | Capability |
|-----|------------|
| `manage_schedule` | Create/edit/cancel sessions |
| `manage_classes` | Create/edit classes |
| `manage_availability` | Edit availability blocks |
| `write_reports` | Session feedback |
| `assign_homework` | File exchange + journal prompts |
| `use_ai` | AI-assisted session note drafting |

---

## Collaboration mode

**Build mode** unless the user asks to learn step-by-step. Prefer focused fixes tied to `TICKETS.md`. Do not commit unless asked.

---

## Not done (needs real credentials / infra)

- Google OAuth consent + token storage (Meet link is a placeholder until then)
- Real Stripe Checkout + webhooks at `/api/payments/stripe/webhook/` (set `STRIPE_*` in `.env`; mock when unset)
- Production media storage for homework uploads (volume or S3; WhiteNoise is static-only)
- Production hosting / DNS / TLS

See `docs/architecture-and-roadmap.md` §10.
