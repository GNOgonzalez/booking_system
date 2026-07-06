# Phase 2 — What You're About to Build (Plain English)

**For when long docs make your brain leave the room.**

One sentence: **A teacher posts a class slot, a student books it, a student cancels it — and Python enforces the rules, not just hidden buttons.**

---

## The big picture

```text
Phase 1:  Who are you?  →  teacher room or student room
Phase 2:  What can you do?  →  create slots, book seats, cancel bookings
```

```text
Teacher
   ↓
POST create ClassSession   →  row in Postgres
   ↓
Student sees open sessions
   ↓
POST book                  →  services/booking.py checks rules → Booking row
   ↓
POST cancel                →  booking.can_cancel()? → status = cancelled
```

Phase 0 = kitchen + pantry.  
Phase 1 = ID badges + separate rooms.  
Phase 2 = **the actual menu — slots on the board and students signing up.**

---

## Two new filing cabinets (models)

### `ClassSession` — the offer on the board

A time slot a **teacher** creates.

| Field | Plain English |
|-------|---------------|
| `teacher` | Which Django user owns this slot (FK to `User`) |
| `starts_at`, `ends_at` | When it happens (store UTC) |
| `capacity` | Max students who can book |
| `status` | e.g. `open` or `cancelled` |

### `Booking` — someone's reservation

A **student** claiming a seat in a session.

| Field | Plain English |
|-------|---------------|
| `student` | Who booked (FK to `User`) |
| `session` | Which slot (FK to `ClassSession`) |
| `status` | e.g. `confirmed` or `cancelled` |
| `created_at` | When they booked |

```text
User (teacher) ──owns──▶ ClassSession ◀──has── Booking ──made by── User (student)
```

One session → many bookings (up to `capacity`).

---

## The service layer — new brain for rules

Phase 1: views checked groups and showed HTML. Fine for simple pages.

Phase 2: booking has **rules that must never be wrong** — full session, double-book, wrong role. Those rules live in one place:

```text
Browser  →  View  →  Service  →  Database
              │         │
              │         └── can_book? create_booking? cancel?
              └── show form, handle POST, redirect
```

**Rule you'll repeat:**

| Layer | Job |
|-------|-----|
| **Template** | Show data and buttons — no business logic |
| **View** | HTTP: GET page, POST form, redirect |
| **Service** (`services/booking.py`) | All booking rules and writes |
| **Model** | Data shape + simple per-row checks |

This is your Reflet `crud.py` — split so models hold data and services hold workflow.

---

## Three functions (memorize these)

### `can_book(user, session)` — in **services**

Asked **before** a Booking exists.

- Is user a student?
- Is session open and in the future?
- Is there a seat left?
- Did they already book this session?
- Mock membership active? (see below)

### `Booking.can_cancel(user)` — on the **model**

Asked on an **existing** booking.

- Is this their booking? (or teacher/staff allowed)
- Is status still `confirmed`?

### `create_booking(user, session)` — in **services**

**Single front door** for new bookings. Views never call `Booking.objects.create(...)` directly.

```text
create_booking:
    1. can_book?  → no → error
    2. INSERT Booking (confirmed)
    3. return booking
```

**Checkpoint:** Explain `create_booking()` out loud without notes.

---

## Membership — fake it for now

Real plans and billing come in Phase 4. Phase 2 still **calls** a membership check inside `can_book()` — but the answer can be "always yes" or a simple boolean.

**Don't mix up:**

| Term | What it is |
|------|------------|
| Postgres role `booking_user` | DB login for Django |
| App **Membership** | Student's plan / can they book? (Phase 2 mock) |

---

## What you'll add (file by file)

| File | What it does |
|------|----------------|
| `models.py` | `ClassSession`, `Booking` + status choices |
| `services/booking.py` | `can_book`, `create_booking`, `cancel_booking` |
| `forms.py` | `ClassSessionForm` (teacher creates slot) |
| `views.py` | Thin: auth + call service + render/redirect |
| `admin.py` | Register new models (debug before UI is done) |
| `templates/scheduling/` | Session list, booking list, create form |
| `config/urls.py` | New routes for teacher + student actions |

`services/` **does not exist yet** — you create it in Phase 2.

---

## Three user flows

### A — Teacher creates a session

```text
GET  /teacher/sessions/new/     → empty form
POST /teacher/sessions/new/     → save ClassSession → redirect
```

### B — Student books

```text
GET  /student/sessions/              → list open sessions
POST /student/sessions/<id>/book/    → create_booking() → redirect
```

### C — Student cancels

```text
POST /student/bookings/<id>/cancel/  → can_cancel? → status = cancelled
```

**POST for actions** (book, cancel, create) — same habit as logout in Phase 1.

---

## Build order (test each step)

1. `ClassSession` model → migrate → admin
2. `Booking` model → migrate → admin
3. `services/booking.py` — test in Django shell
4. `Booking.can_cancel` + cancel in service
5. Teacher: create-session form
6. Student: list + book
7. Student: my bookings + cancel
8. Mock membership inside `can_book`

Steps 1–4 work in shell + admin before you write new HTML.

---

## Phase 2 wins checklist

- [ ] `ClassSession` + `Booking` models + migrations
- [ ] `services/booking.py` with `can_book`, `create_booking`
- [ ] `Booking.can_cancel(user)` on the model
- [ ] Teacher creates session from the site (not only admin)
- [ ] Student lists open sessions and books one
- [ ] Full session → second student blocked
- [ ] Double-book same session → blocked
- [ ] Student cancels own booking
- [ ] Student cannot cancel someone else's
- [ ] Checkpoint: explain `create_booking()` without notes

---

## What Phase 2 is NOT

- Teacher availability blocks (Phase 3)
- Messages / curriculum (Phase 4)
- React / API (Phase 5)
- SimplyBook sync (much later)
- Pretty calendar UI (Phase 6)

Plain lists and forms are enough. Ugly and correct beats pretty and wrong.

---

## "I'm lost" reset

```bash
cd /Users/gnogo/repos/booking_scheduling_app
source .venv/bin/activate
pwd   # must end with repos/booking_scheduling_app
python manage.py runserver
```

| URL | Expect (after Phase 2) |
|-----|--------------------------|
| `/teacher/dashboard/` | Teacher home + link to create sessions |
| `/teacher/sessions/new/` | Create session form |
| `/student/sessions/` | Open slots + Book buttons |
| `/student/bookings/` | My bookings + Cancel |
| `/admin/` | ClassSession + Booking tables |

Shell sanity check (anytime):

```bash
python manage.py shell
```

```python
from scheduling.models import ClassSession, Booking
ClassSession.objects.count()
Booking.objects.count()
```

---

## What's next — Phase 3

`AvailabilityBlock` — teachers define when they're generally free; optional guard when creating sessions.

Same loop: new model, new views, rules in services.
