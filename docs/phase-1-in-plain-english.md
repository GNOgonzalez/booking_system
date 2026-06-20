# Phase 1 — What You Built (Plain English)

**Auth, roles, and your first real pages.**

One sentence: **You made people log in on your site, then only see the dashboard that matches their group.**

---

## The big picture

```text
Browser
   ↓
/accounts/login/     → Django checks username + password
   ↓
Session cookie       → "this browser is logged in as gnogo"
   ↓
/teacher/dashboard/  → view checks group → show HTML or redirect
```

Phase 0 = kitchen + pantry.  
Phase 1 = **ID badges + separate rooms for teachers and students.**

---

## What you added (file by file)

| File | What it does now |
|------|------------------|
| `models.py` | `Profile` linked 1:1 to `User` |
| `admin.py` | Manage Profiles + DemoItems |
| `views.py` | `teacher_dashboard`, `student_dashboard` + guards |
| `templates/registration/login.html` | Site login form |
| `templates/scheduling/teacher_dashboard.html` | Teacher page |
| `templates/scheduling/student_dashboard.html` | Student page |
| `config/urls.py` | Routes URLs → views |
| `config/settings.py` | `LOGIN_REDIRECT_URL` after login |

---

## Three "user" concepts (don't mix them)

| Name | Layer | Example |
|------|-------|---------|
| `booking_user` | Postgres DB login | Django connects to DB |
| Django `User` | App login | `gnogo`, test student |
| `Profile` | Extra info | display name, timezone |

**Groups** (`student`, `teacher`, `staff`) hang off Django `User` — not Profile.

---

## Profile — why it exists

```text
User        = login (username, password)
Profile     = extra info (display_name, timezone)
Groups      = roles (can be multiple)
```

One User → one Profile → zero or more Groups.

---

## Groups — why not a role field on Profile?

```text
role = "teacher"   →  only ONE role
Groups             →  teacher AND student at the same time ✅
```

---

## The request loop (your pages)

```text
URL (urls.py)  →  view (views.py)  →  template (HTML)
```

Example:

```text
/teacher/dashboard/
   → teacher_dashboard()
   → scheduling/teacher_dashboard.html
```

Login uses Django's built-in view — you only supplied the template.

---

## Decorator = bouncer

```python
@login_required
def teacher_dashboard(request):
```

**Bouncer rule:** not logged in? → go to `/accounts/login/`

Group check **inside** the view = second bouncer:

```python
if user.groups.filter(name="teacher").exists():
    return render(...)
if user.groups.filter(name="student").exists():
    return redirect("student_dashboard")
```

---

## `redirect("teacher_dashboard")` — what's that string?

The **name** from `urls.py`:

```python
path('teacher/dashboard/', views.teacher_dashboard, name='teacher_dashboard')
```

Not the URL string — the **nickname** so URLs can change without breaking redirects.

---

## Settings vs views

| Thing | Lives in | Example |
|-------|----------|---------|
| After login, go here | `settings.py` | `LOGIN_REDIRECT_URL` |
| Wrong role on a page | `views.py` | `redirect("student_dashboard")` |

Login redirect happens **before** your dashboard view runs.

---

## Template paths cheat sheet

| Page | `render(...)` path | File on disk |
|------|-------------------|--------------|
| Login | `registration/login.html` | `templates/registration/login.html` |
| Teacher | `scheduling/teacher_dashboard.html` | `templates/scheduling/teacher_dashboard.html` |
| Student | `scheduling/student_dashboard.html` | `templates/scheduling/student_dashboard.html` |

Login has no `scheduling/` prefix — Django auth convention.

---

## Phase 1 wins checklist

- [ ] Profile model + migration
- [ ] Groups: student, teacher, staff
- [ ] Site login at `/accounts/login/`
- [ ] Teacher + student dashboards
- [ ] Role checks in **views** (not just hidden links)
- [ ] Test student user in admin
- [ ] Checkpoint: student blocked from teacher dashboard (redirect)

---

## "I'm lost" reset

```bash
cd /Users/gnogo/booking_scheduling_app
source .venv/bin/activate
pwd   # must show booking_scheduling_app
python manage.py runserver
```

| URL | Expect |
|-----|--------|
| `/accounts/login/` | Login form |
| `/teacher/dashboard/` | Teacher page (if in teacher group) |
| `/student/dashboard/` | Student page (if in student group) |
| `/admin/` | Django admin |

---

## What's next — Phase 2

- [phase-2-in-plain-english.md](./phase-2-in-plain-english.md) — what you're building
- [phase-2-reading.md](./phase-2-reading.md) — concepts + links before you code

Booking models (`ClassSession`, `Booking`), `services/booking.py`, forms, book/cancel flow.

Same loop — new models, new views, new rules.
