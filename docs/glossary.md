# Glossary

Plain-English definitions for this project. Use these words in chat and docs so we don't mix layers up.

---

## People & access (app layer)

### Django user (app user)

A person who **logs into your website**.

- Stored in: `auth_user` table (Postgres)
- Created in: Django admin → **Users**, or `createsuperuser`
- Examples: `gnogo`, `teststudent`
- Has: username, password (hashed), optional email
- **Not** the same as Postgres role `booking_user`

**Say:** “Django user” or “app user” — not just “user” if it could be confused with the DB.

---

### Profile

Extra information **about one Django user** — not used for login or roles.

- Stored in: `scheduling_profile` table
- Link: **one Profile per Django user** (one-to-one)
- Examples: `display_name`, `timezone`
- **Does not** store student/teacher role (Groups do that)

---

### Group (Django Group)

A **role badge** on a Django user. A user can have **multiple** groups.

- Stored in: `auth_group` + `auth_user_groups` (link table)
- Your groups: `student`, `teacher`, `staff`
- Checked in **views** (e.g. `user.groups.filter(name="teacher")`)
- **Not** the same as Postgres “role membership” (see below)

---

### Superuser / staff (Django flags)

Special flags on a **Django user**:

| Flag | Meaning |
|------|---------|
| `is_superuser` | Full access to `/admin/` |
| `is_staff` | Can access `/admin/` (with permissions) |

Separate from Groups — though you may put admins in a `staff` **Group** for app pages too.

---

## Database layer (Postgres)

### PostgreSQL server

The background program that runs your database (port 5432).

---

### Database (`booking_dev`)

A **named container** inside Postgres where your tables live.

- **Not** a user
- Django stores all app tables here

---

### Postgres role (DB user)

A **database login** — who is allowed to connect to Postgres and touch tables.

- Example: `booking_user`
- Password in: `.env` (`DB_PASSWORD`)
- Used by: **Django only** — website visitors never see this
- Created with: `CREATE USER` in `psql`

**Say:** “Postgres role” or “DB user” — never “app user”.

---

### Table

A collection of rows in Postgres (e.g. `auth_user`, `scheduling_profile`).

---

### Row

One record in a table (one Django user, one Profile, one booking later).

---

### Primary key (`id`)

The **unique name tag** for one row. Other tables point at it via foreign keys.

- Django adds `id` automatically on almost every model (see [IDs](#ids-primary-keys))
- Example: Profile `id=3`, User `id=5`

---

### Foreign key

A column that stores **another row’s `id`** to link tables.

- Example: `Profile.user_id` → points to `auth_user.id`
- In Django models: `ForeignKey`, `OneToOneField`

---

### Migration

Instructions to change Postgres tables when models change.

| Command | Job |
|---------|-----|
| `makemigrations` | Write plan file in `migrations/` |
| `migrate` | Run plan against Postgres |

Alembic in SQLAlchemy projects = same idea, different tool.

---

### Schema

Namespace inside a database (often `public`). Tables live here.

---

## Django project structure

### Project (`config/`)

Whole site settings: `settings.py`, root `urls.py`, `manage.py`.

---

### App (`scheduling/`)

One feature area: models, views, templates, admin.

---

### Model

Python class = blueprint for a Postgres **table** (`models.py`).

---

### View

Python function that runs when someone hits a URL — decides what happens (`views.py`).

---

### Template

HTML file the user sees (in `templates/`).

---

### URL / route

Maps a path like `/teacher/dashboard/` to a view (`urls.py`).

The `name=` in `path()` is a **nickname** for `redirect("teacher_dashboard")`.

---

### Admin (`/admin/`)

Django’s built-in staff UI to manage models — not your student/teacher dashboards.

---

## Auth & HTTP

### Session

How Django remembers “this browser is logged in as gnogo” after login (cookie + DB row).

---

### `@login_required`

Decorator on a view: guest → redirect to login page.

---

### CSRF token

Hidden security field in POST forms (`{% csrf_token %}`). Required for login, logout, booking forms later.

---

### POST vs GET

| Method | Typical use |
|--------|-------------|
| GET | Load a page (address bar) |
| POST | Submit a form (login, logout, create booking) |

Django 5 **logout requires POST** — use a form button, not the address bar.

---

## Settings (`.env` vs `settings.py`)

| File | Holds |
|------|-------|
| `.env` | Secrets: DB password, DB name (not in git) |
| `settings.py` | App config; reads `.env` via `python-dotenv` |
| `requirements.txt` | Python packages to install |

---

## IDs (primary keys)

### Django (this project)

**You usually do not define `id` yourself.** Every `models.Model` gets:

```text
id — BigAutoField, primary key, auto-increment
```

You define **relationships** (`ForeignKey`, `OneToOneField`); Django creates `something_id` columns.

---

### SQLAlchemy + Alembic + SQLite (your other project)

**Different stack — different defaults.**

| Tool | Role |
|------|------|
| SQLAlchemy | ORM (like Django models) |
| Alembic | Migrations (like `makemigrations` / `migrate`) |
| SQLite | Database file (like Postgres here) |

SQLAlchemy **does not** automatically add an `id` column to every model. You typically **define it yourself**:

```python
id = Column(Integer, primary_key=True, autoincrement=True)
# SQLAlchemy 2.0 style:
id: Mapped[int] = mapped_column(primary_key=True)
```

So manually creating IDs in your CRUD project was **normal and correct** for that stack.

| | Django ORM | SQLAlchemy |
|---|------------|------------|
| Auto `id` on every model? | **Yes** (default) | **No** — you declare primary key |
| Migrations | Django migrations | Alembic |
| DB | Postgres (here) | SQLite (there) |

Same SQL idea (primary keys, foreign keys); different ORM conventions.

---

## Quick disambiguation

| If someone says… | They probably mean… |
|------------------|---------------------|
| “user” (ambiguous) | Ask: Django user or Postgres role? |
| “role” (ambiguous) | Django Group (`teacher`) or Postgres role (`booking_user`)? |
| “membership” (later) | App billing model — **not** Postgres role membership |
| “admin” | `/admin/` site **or** `staff` group — clarify which |

---

## Layer diagram

```text
Browser (human)
    ↓
Django user + Groups + Profile     ← app layer (your code)
    ↓
Django ORM (models, migrations)
    ↓
Postgres role booking_user → booking_dev   ← database layer
```

---

## Related docs

- [glossary.md](./glossary.md)
- [django-vs-crud-project.md](./django-vs-crud-project.md) — map Reflet/FastAPI stack to Django
- [phase-0-in-plain-english.md](./phase-0-in-plain-english.md)
- [phase-1-in-plain-english.md](./phase-1-in-plain-english.md)
- [postgres-roles-membership-inheritance.md](./postgres-roles-membership-inheritance.md)
