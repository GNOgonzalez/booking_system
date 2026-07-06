# Django (booking app) vs crud_project (Reflet)

Side-by-side map so you know what you built manually vs what Django gives you — and how a rebuild might work.

**crud_project** = FastAPI + SQLAlchemy + Alembic + SQLite/Postgres + React + JWT  
**booking_scheduling_app** = Django + Postgres + templates (React in Phase 5)

See also: [glossary.md](./glossary.md) for **Django user** vs **Postgres role**.

---

## Big picture

```text
CRUD PROJECT (Reflet)                    BOOKING APP (Django)
─────────────────────                    ────────────────────
React (frontend/)                        Django templates (Phase 1–4)
    ↓ fetch + JWT                            ↓ HTML forms
main.py (FastAPI routes)                 urls.py + views.py
deps.py (auth guards)                    @login_required + group checks
security.py (JWT, bcrypt)                django.contrib.auth (sessions)
crud.py (queries + rules)                models + services/ (Phase 2+)
models.py (SQLAlchemy)                   models.py (Django ORM)
schemas.py (Pydantic)                    Django Forms / DRF serializers later
database.py + SessionLocal               settings DATABASES + ORM
alembic/ (migrations)                    makemigrations / migrate
SQLite app.db                            PostgreSQL booking_dev
Admin CRUD in React AdminPanel           Django /admin/ + custom pages
```

You had fun wiring every layer. Django collapses several layers into built-ins — you still write **your** domain (sessions, bookings, badges).

---

## File-by-file map

| crud_project | What it did | Django equivalent |
|--------------|-------------|-----------------|
| **`models.py`** | SQLAlchemy tables, **you set `id`** | **`scheduling/models.py`** — auto `id`, `ForeignKey` |
| **`database.py`** | Engine, `SessionLocal`, `get_db` | **`config/settings.py`** `DATABASES` + ORM (no session factory in your code) |
| **`alembic/`** | Migration scripts | **`scheduling/migrations/`** + `makemigrations` |
| **`crud.py`** | All DB queries + business logic | **`models` querysets** + **`services/`** (Phase 2) |
| **`schemas.py`** | Request/response validation | **Django Forms** (templates) or **DRF serializers** (API) |
| **`main.py`** | Every URL + route handler | **`config/urls.py`** + **`scheduling/views.py`** |
| **`deps.py`** | `get_current_teacher`, role guards | **`@login_required`** + **Group checks** in views |
| **`security.py`** | JWT create/verify, bcrypt | **`django.contrib.auth`** (hashing, sessions) |
| **`test_main.py`** | API tests | **`scheduling/tests.py`** (you add tests) |
| **`frontend/`** | React UI | **templates/** now; **React + DRF** in Phase 5 |
| **`import_csv.py`** | Data import | Management command or script (you'd rebuild) |
| **`badges.py`** | Business rules | **`services/badges.py`** or methods on models |
| **`.env`** | Secrets | **`.env`** + **`python-dotenv`** (same idea) |

---

## Concepts you already know → Django name

| You learned in crud_project | Same idea in Django |
|----------------------------|---------------------|
| SQLAlchemy `Session` + `get_db` | Django ORM (no manual session in views) |
| `Column(Integer, primary_key=True)` | Automatic `id` on `models.Model` |
| `ForeignKey` in SQLAlchemy | `models.ForeignKey` / `OneToOneField` |
| Alembic `upgrade head` | `python manage.py migrate` |
| Pydantic `StudentCreate` | `forms.ModelForm` or DRF `Serializer` |
| FastAPI `Depends(get_current_teacher)` | `@login_required` + `if user.groups...` |
| JWT in `Authorization` header | Session cookie (Phase 1–4); JWT optional in Phase 5 |
| Separate `Admin`, `Teacher`, `Student` **tables** | One **Django user** + **Groups** + **Profile** (your Phase 1 design) |
| `crud.get_student_dashboard_stats()` | Service function or model manager |
| React calls `/api/me/dashboard` | View renders template or DRF returns JSON |

---

## Auth: biggest architectural difference

**Reflet (crud_project):**

```text
Login → JWT in localStorage → every API call sends Bearer token
deps.py validates token → loads Student or Teacher or Admin row
Three separate model types for roles
```

**Booking app (Django Phase 1):**

```text
Login → session cookie → Django knows request.user
Groups: student, teacher, staff
One User table; roles are badges not separate tables
```

Both are valid. Django's way is less code for server-rendered apps. Your JWT + React way matches **Phase 5** (DRF + React) better.

---

## What you did manually that Django gave you for free

| You built in Reflet | Django built-in |
|---------------------|-----------------|
| Password hashing (passlib/bcrypt) | `User.set_password()` |
| Login/register routes | `django.contrib.auth.urls` |
| JWT issue/verify | Sessions (or add JWT later with DRF) |
| Role dependency injection | Groups + view checks |
| Admin CRUD UI (React AdminPanel) | `/admin/` (plus custom pages) |
| Manual `id` columns | Auto primary key |
| CORS, health (you added) | Add if needed; not core Phase 1 |

---

## What Reflet has that booking app doesn't yet

| Reflet feature | Booking app status |
|----------------|-------------------|
| Student / Teacher / Session / Booking models | Phase 2+ |
| Skill feedback, badges, charts | Not planned yet (domain-specific) |
| CSV import pipeline | Not yet |
| React dashboards | Phase 5 (or rebuild Reflet UI against DRF) |
| JWT API | Phase 5 DRF |
| Alembic on Postgres path | Django migrations on Postgres ✅ |

---

## Rebuild crud_project in Django — sensible path

**Don't merge repos by copying files.** Different stacks. **Re-implement domain in Django**, reusing *ideas* from `crud.py`, not paste.

### Option A — One Django project, multiple apps (recommended long-term)

```text
reflet_django/                    # or grow booking_scheduling_app
├── config/
├── scheduling/                   # booking (ClassSession, Booking)
├── reflet/                       # Reflet domain (Session, Feedback, badges)
│   ├── models.py
│   ├── services/                 # port logic from crud.py + badges.py
│   └── ...
├── accounts/                     # Profile, Groups (or keep in scheduling)
└── frontend/                     # Phase 5: React from crud_project, pointed at DRF
```

**Pros:** One Postgres DB, one auth system, shared Django users.  
**Cons:** Big project; do it incrementally.

### Option B — Finish booking app first, then port Reflet features

1. Complete **Phase 2–4** on booking_scheduling_app (templates).
2. Add **DRF + React** (Phase 5) — now close to Reflet architecture.
3. Port Reflet **models** → Django models; **crud.py** → **services/**.
4. Reuse or adapt **frontend/** from crud_project against new API.

**Pros:** You learn Django deeply before a big port.  
**Cons:** Two codebases temporarily.

### Option C — Rebuild Reflet from scratch in new Django repo

Same as B but fresh `startproject`. Only if you want a clean name/structure.

---

## What transfers directly vs rewrite

| Transfers (concepts / partial code) | Rewrite from scratch |
|-------------------------------------|----------------------|
| Table relationships (Student ↔ Session ↔ Feedback) | FastAPI routes → views/DRF |
| Logic in `crud.py`, `badges.py` | SQLAlchemy models → Django models |
| React components (with API URL changes) | JWT auth flow → session or DRF JWT |
| CSV import *logic* | `database.py`, `deps.py`, `security.py` |
| Alembic history | Use Django migrations instead |

---

## IDs reminder

| Stack | Primary key |
|-------|-------------|
| **SQLAlchemy (Reflet)** | You defined `id = Column(..., primary_key=True)` ✅ normal |
| **Django** | Auto `id` on every model — don't add unless special case |

Same SQL; different ORM defaults.

---

## Merge fantasy vs reality

**"Merge apps"** usually means:

1. **One database** — Django models for both booking + Reflet progress data  
2. **One login** — Django users with Groups (student, teacher, staff)  
3. **One API** (later) — DRF endpoints replacing FastAPI  
4. **One React app** (optional) — reuse crud_project `frontend/`  

It does **not** mean running FastAPI and Django side by side forever.

Your **Phase 5 plan** (DRF + React) is already the bridge toward Reflet's shape — with Django owning the brain.

---

## Suggested order (if rebuild is the goal)

1. ✅ **booking Phase 0–1** — Django basics, auth, Groups (done)  
2. **booking Phase 2** — ClassSession, Booking, `services/booking.py`  
3. **booking Phase 3–4** — availability, messages  
4. **booking Phase 5** — DRF + React (reuse skills from crud_project frontend)  
5. **Port Reflet models** into a second Django app (`reflet` or `progress`)  
6. **Port `crud.py` → services** one function at a time  
7. **Point React** at DRF instead of FastAPI; retire `main.py`  

---

## One sentence

**Reflet:** you built the platform and the product.  
**Django booking app:** Django built much of the platform; you're building the product — and Phase 5 + a Reflet app is how the two worlds meet.
