# Phase 0 — Reading Guide

Study material mapped to what you built in Phase 0. Read in order for a narrative, or skip to topics that feel unclear.

---

## 1. The big picture — how your stack fits together

**What you built:**

```text
Browser  →  Django (Python)  →  PostgreSQL
              ↑
         .env (secrets)
         requirements.txt (Python packages)
         .venv (isolated Python environment)
```

**Read:**

- [Django overview — “What is Django?”](https://docs.djangoproject.com/en/5.2/intro/overview/)
- [MDN — How the web works](https://developer.mozilla.org/en-US/docs/Learn_web_developer/Getting_started/Web_standards/How_the_web_works) (optional)

**Why:** You’re learning a web app where a server handles requests and talks to a database.

---

## 2. Virtual environment + `requirements.txt`

**What you did:**

- `python3 -m venv .venv`
- `source .venv/bin/activate`
- `pip install -r requirements.txt`

**Read:**

- [Python venv (official docs)](https://docs.python.org/3/library/venv.html)
- [pip requirements files](https://pip.pypa.io/en/stable/reference/requirements-file-format/)

**Why:** venv isolates packages per project. `requirements.txt` lets you recreate the same environment later.

**Lesson from your session:** `pip` reads the **saved** file on disk — unsaved editor changes don’t count.

---

## 3. Git + GitHub

**What you did:**

- `git init`, `.gitignore`, `git commit`, `git push`
- Fixed: commit before push; GitHub account mismatch (`gh auth login`)

**Read:**

- [GitHub Docs — Ignoring files](https://docs.github.com/en/get-started/git-basics/ignoring-files)
- [GitHub Docs — Authenticating with CLI](https://docs.github.com/en/cli/github-cli/github-cli)

**Why:** Version history + backup. `.gitignore` keeps `.venv/` and `.env` off public GitHub.

---

## 4. PostgreSQL — server, database, user

**What you did:**

- `brew services start postgresql@16`
- `psql postgres` → `CREATE DATABASE`, `CREATE USER`, `GRANT`
- `psql -U booking_user -d booking_dev -h localhost`
- Created `.env` with connection details

**Read:**

- [PostgreSQL tutorial — Introduction](https://www.postgresql.org/docs/current/tutorial.html)
- [PostgreSQL — Roles](https://www.postgresql.org/docs/current/user-manag.html)
- **Also see:** [postgres-roles-membership-inheritance.md](./postgres-roles-membership-inheritance.md) in this folder

**Why:** Django stores data in Postgres. A dedicated dev user (`booking_user`) matches how real apps connect.

---

## 5. `.env` vs `python-dotenv`

**What you did:**

- File `.env` with `DB_NAME`, `DB_USER`, etc.
- In `settings.py`: `load_dotenv()` and `os.environ[...]`
- Installed `python-dotenv` (import name: `dotenv`)

**Read:**

- [python-dotenv README](https://github.com/theskumar/python-dotenv)
- [12-factor app — Config](https://12factor.net/config)

**Why:** Secrets stay out of code. Only `.env` changes between environments.

---

## 6. Django project vs app

**What you did:**

- `django-admin startproject config .`
- `python manage.py startapp scheduling`
- Added `'scheduling'` to `INSTALLED_APPS`

**Read:**

- [Django — Projects and apps](https://docs.djangoproject.com/en/5.2/intro/reusable-apps/)
- [Django — Settings](https://docs.djangoproject.com/en/5.2/topics/settings/)

**Why:** One project holds settings; apps hold features (`scheduling`, etc.).

---

## 7. Connecting Django to PostgreSQL

**What you did:** `ENGINE: django.db.backends.postgresql` + env vars in `settings.py`

**Read:**

- [Django — Databases](https://docs.djangoproject.com/en/5.2/ref/databases/)
- [psycopg3 basics](https://www.psycopg.org/psycopg3/docs/basic/index.html) (optional)

---

## 8. Migrations

**What you did:** `python manage.py migrate` → Django built-in tables in Postgres

**Read:**

- [Django — Migrations](https://docs.djangoproject.com/en/5.2/topics/migrations/)
- [Django — Models](https://docs.djangoproject.com/en/5.2/topics/db/models/) (preview for Step 6)

**Why:** Schema changes are versioned in code, not hand-edited in the database.

---

## 9. Dev server — `runserver`

**Read:**

- [Django tutorial — Parts 1–2](https://docs.djangoproject.com/en/5.2/intro/tutorial01/) (reinforce, don’t rush to copy)

---

## 10. Saved for later — Step 6

**Read when ready:**

- [Django — Admin site](https://docs.djangoproject.com/en/5.2/ref/contrib/admin/)
- [Django tutorial Part 2 — models and admin](https://docs.djangoproject.com/en/5.2/intro/tutorial02/)

---

## Suggested reading order

| Order | Topic | ~Time |
|-------|--------|-------|
| 1 | Django overview | 15 min |
| 2 | Projects and apps | 15 min |
| 3 | Postgres roles doc (local) + PostgreSQL tutorial | 35 min |
| 4 | Migrations | 20 min |
| 5 | 12-factor config + python-dotenv | 10 min |
| 6 | Skim Django tutorial Parts 1–2 | 30 min |

---

## Self-check questions

1. What’s the difference between **project** and **app**?
2. What lives in **`.env`** vs **`requirements.txt`** vs **`.venv/`**?
3. What did the **first `migrate`** create, and why no `scheduling_*` tables yet?
4. What will **`makemigrations`** do that **`migrate`** doesn’t?
5. What is a Postgres **role** vs an app **student/teacher role**?
