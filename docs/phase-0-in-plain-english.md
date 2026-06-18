# Phase 0 — What You Actually Built (Plain English)

**For when long docs make your brain leave the room.**

One sentence version: **You built a empty restaurant kitchen, hooked it to a pantry (Postgres), and proved you can add one item to the menu (DemoItem in admin).**

---

## 🎯 What is Django doing?

Django is a **request handler + organizer**.

```text
Someone visits a URL
       ↓
Django receives the request
       ↓
Django decides what to do (settings, urls, views)
       ↓
Maybe reads/writes the database
       ↓
Sends back a webpage (HTML)
```

Right now you mostly use **`/admin/`** — Django's built-in back office. Your custom pages come in Phase 1.

**Django is NOT:**
- The database (that's Postgres)
- The browser
- Python itself

**Django IS:**
- The brain that connects browser ↔ database ↔ your Python code

---

## 🏢 The building analogy

Think of your project as a **small office building**:

| Thing | Real name | Analogy |
|-------|-----------|---------|
| Whole repo | project root | The building |
| `config/` | Django **project** | Building manager's office — rules for whole building |
| `scheduling/` | Django **app** | One department (booking/scheduling) |
| `manage.py` | CLI remote | Intercom to give orders to the building |
| `models.py` | data shapes | Blueprints for filing cabinets |
| `migrations/` | schema history | Instruction manuals for building new cabinets |
| `admin.py` | staff UI config | Which cabinets get a nice GUI |
| `views.py` | request handlers | Reception desks (empty for now) |
| `templates/` | HTML pages | Flyers you hand visitors (don't exist yet) |
| Postgres | database | Basement archive — permanent storage |
| `.env` | secrets file | Key to the basement (never on GitHub) |
| `.venv/` | virtual env | This building's private toolbox |

**The files aren't random.** Django scaffolds a standard layout so every Django dev knows where to look.

---

## 📁 Every file — keep or ignore?

### ✅ You touched these (care about them)

| File | What it does |
|------|----------------|
| `requirements.txt` | Shopping list: Django, psycopg, python-dotenv |
| `.env` | DB password etc. (local only) |
| `.gitignore` | Tells git to ignore `.venv`, `.env` |
| `config/settings.py` | Master config: DB, installed apps, secrets |
| `scheduling/models.py` | Your `DemoItem` table definition |
| `scheduling/admin.py` | Registers `DemoItem` in `/admin/` |
| `scheduling/migrations/0001_initial.py` | "Create DemoItem table" instructions |

### 😴 Exists but ignore for now

| File | Why it's there |
|------|----------------|
| `scheduling/views.py` | Empty — you'll write pages in Phase 1 |
| `scheduling/tests.py` | Empty — tests later |
| `scheduling/apps.py` | Tells Django the app exists |
| `config/wsgi.py` / `asgi.py` | Production server hooks — not dev |
| `config/urls.py` | URL routing — only `/admin/` so far |
| `manage.py` | Django commands — you run it, rarely edit it |

### 📚 Your docs folder

| File | Purpose |
|------|---------|
| `docs/phase-0-in-plain-english.md` | This file |
| `docs/architecture-and-roadmap.md` | Diagrams + roadmap |
| `docs/phase-0-reading.md` | Links if you want depth later |
| `LEARNING_PATH.md` | Checklist (local — gitignored) |

---

## 🔁 The 3 loops you practiced

### Loop 1 — Python environment

```text
.venv  +  requirements.txt  =  "this project's tools only"
```

### Loop 2 — Database connection

```text
Postgres running  →  .env has password  →  settings.py reads .env  →  Django connects
```

### Loop 3 — Models (the big one)

```text
models.py  →  makemigrations  →  migrate  →  admin.py  →  browser
  (idea)      (write plan)      (build)      (GUI)        (use it)
```

You did Loop 3 with `DemoItem`. **Every feature** (bookings, profiles) repeats Loop 3.

---

## 🎬 What happened when you ran each command

| You typed | What happened |
|-----------|----------------|
| `django-admin startproject config .` | Created `config/`, `manage.py` |
| `startapp scheduling` | Created `scheduling/` department |
| `migrate` (first time) | Postgres got Django's built-in tables (`auth_user`, etc.) |
| `makemigrations` | Django wrote plan for `DemoItem` table |
| `migrate` (second time) | Postgres built `scheduling_demoitem` table |
| `createsuperuser` | Created your admin login in `auth_user` |
| `runserver` | Started a tiny web server on your Mac |
| Visited `/admin/` | Django served login + admin pages |

---

## 🧠 Postgres vs Django — who stores what?

```text
         YOU (browser)
              │
         DJANGO (rules + code)
              │
         POSTGRES (rows in tables)
```

| Layer | Stores |
|-------|--------|
| Postgres | Actual rows: your DemoItem title, user passwords (hashed), timestamps |
| Django | Code that **describes** tables and **decides** what's allowed |
| Browser | Just displays what Django sends |

`created_at` with `auto_now_add=True`? **Django** sets it when saving; **Postgres** stores it.

---

## ✅ Phase 0 checklist — what you accomplished

- [x] Python project with isolated dependencies
- [x] Code on GitHub (without secrets)
- [x] Postgres database with a dedicated user
- [x] Django talking to Postgres (not SQLite)
- [x] First model + migration + admin
- [x] Design decisions for Phase 1 (Groups, Profile, services)

**You did not build the booking app yet.** You built the **foundation**.

---

## 🚀 What's coming in Phase 1 (preview)

Same building. New rooms:

```text
Profile model
Login / logout pages  ← views.py + templates/ wake up
Student dashboard vs teacher dashboard
Django Groups
```

Files you'll start using: `views.py`, `templates/`, `urls.py`.

---

## 💡 ADHD-friendly rules for future you

1. **One command, one purpose** — don't run 5 things at once
2. **`cat filename` after saving** — confirms disk matches editor
3. **Only read files marked ✅ above** when confused
4. **Ask "which loop am I in?"** — env, database, or model?
5. **Phase 0 = foundation** — feeling lost is normal; the app comes next

---

## 🆘 "I'm lost" — 30-second reset

Answer these:

1. Is Postgres running? → `pg_isready`
2. Is venv on? → `(.venv)` in prompt
3. Does Django start? → `python manage.py runserver`
4. Can I log into `/admin/`?
5. Do I see Demo items?

If all yes → **you're fine.** Everything else is Phase 1+.
