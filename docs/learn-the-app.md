# Learn this app

> **Pickup note (July 2026 — stepping away ~1 month)**  
> This file exists **only on your machine** until you commit and push it (`git add docs/learn-the-app.md` and any other doc changes, then push).  
> **Pausing for:** CS50P + a solo pomodoro/to-do app. **When you return:**  
> 1. `git pull` · 2. `python manage.py migrate` · 3. skim this doc · 4. do **Walkthrough A** (§7) with servers running · 5. pick one small task from [`future-features.md`](./future-features.md) — not a big refactor.  
> Last big shipped slice: class requests, catalog roadmap, mobile nav, booking UX (commit `72911d9` on `main`).

**Audience:** You — building CS50P now, planning CS50 Web next, and owning this codebase.

**Goal:** Understand what you built in **plain English**, tied to concepts from CS50P and (preview) CS50 Web, so you can maintain it, explain it to an engineer, and keep learning after the courses.

**Not in this doc:** sales pitch, audit history, old integration plans. For engineers: [`architecture-and-roadmap.md`](./architecture-and-roadmap.md). For deploy: [`operations-guide.md`](./operations-guide.md).

---

## 1. What is this app? (30-second version)

A **music/language/lesson studio** (or similar) runs classes online or in person. This software lets them:

- **Teachers** publish lesson times, set availability, review student requests, assign homework, write session reports.
- **Students** buy a membership (tickets), book lessons, submit homework, see progress.
- **Staff** configure the studio: branding, class roadmap, membership prices, teacher permissions.

Everything important is stored in **PostgreSQL**. The **React** site is what people use day to day. **Django** on the server holds the rules and talks to Stripe, email, and Google when configured.

---

## 2. The three layers (preview of CS50 Web)

You will see this pattern everywhere:

```text
┌──────────────┐     HTTP + JSON      ┌──────────────┐     SQL     ┌────────────┐
│   Browser    │  ◄────────────────►  │   Django     │ ◄────────► │ PostgreSQL │
│   (React)    │      /api/...        │   + DRF      │            │            │
└──────────────┘                      └──────────────┘            └────────────┘
     UI only                            rules + auth                  data
```

| Layer | Folder | Your job when learning |
|-------|--------|-------------------------|
| **Browser** | `frontend/src/` | Show data, collect clicks — **no business rules** |
| **Server** | `scheduling/`, `progress/`, `config/` | **All the rules** live here |
| **Database** | Postgres tables from `models.py` | What gets saved |

**The one rule to remember:** If a student “shouldn’t be allowed to book,” the check belongs in **`scheduling/services/booking.py`**, not in a React `if` statement.

---

## 3. CS50P concepts → this repo

You are on **week 2** — functions, variables, conditionals, loops. You already have the mental tools; this app is just **many files** doing those things together.

| CS50P idea | Plain meaning | Example in this app |
|------------|---------------|---------------------|
| **Function** | Reusable block of logic | `create_booking()` in `scheduling/services/booking.py` |
| **Variable** | Name for a value | `tickets_remaining` on a membership |
| **Conditional** | `if` / `else` | “If no tickets left, don’t allow book” |
| **Loop** | Repeat over a list | Loop open sessions to show calendar days |
| **Dictionary** | Key → value map | JSON from API: `{"title": "Piano …", "start_time": "…"}` |
| **File I/O** | Read/write files | Homework uploads in `media/homework/` |
| **Library** | Someone else’s code | Django, Stripe SDK, React |

**Exercise (15 min):** Open `scheduling/services/booking.py`. Find `create_booking`. Circle (mentally) every `if` — each one is a **business rule**.

---

## 4. CS50 Web concepts → this repo (read after the course)

When you take **CS50 Web**, map lectures to this project:

| CS50 Web topic | In this app |
|----------------|-------------|
| **HTTP** | Browser `fetch()` in `frontend/src/api.js`; Django receives GET/POST |
| **Routes / URLs** | `scheduling/api/urls.py`, `config/urls.py` |
| **Templates vs API** | Legacy HTML in `scheduling/templates/`; React is primary |
| **Models (ORM)** | `scheduling/models.py` — Python class ↔ database table |
| **Migrations** | `scheduling/migrations/` — schema changes over time |
| **Sessions / auth** | JWT tokens in `sessionStorage`; Django Groups for roles |
| **SQL** | Mostly hidden by Django; Postgres is the engine |
| **JavaScript / DOM** | React components in `frontend/src/components/` |
| **AJAX / fetch** | Every `apiFetch('/api/...')` call |

After CS50 Web, redo **Section 7** walkthroughs below and trace one request in the browser Network tab.

---

## 5. People and roles (don’t mix these up)

Read [`glossary.md`](./glossary.md) when confused. Short version:

| Term | What it is |
|------|------------|
| **User** | Login account (`demo_student`) — stored in Django’s user table |
| **Profile** | Extra info (display name, timezone, theme) — one per user |
| **Group** | Role badge: `student`, `teacher`, or `staff` |
| **TeacherPermission** | Fine-grained switches staff set per teacher (can they create sessions? use AI?) |

**Staff** is not the same as Django **superuser**. Superuser = break-glass `/admin/`. Staff = studio manager in the React app.

---

## 6. Main “things” in the database

Think of these as **nouns** the app cares about:

| Noun | Real-world meaning |
|------|-------------------|
| **ClassOffering** | “Ms. Lee teaches Beginner Piano · Technique” |
| **CatalogSubject…Topic** | Staff’s master roadmap template (subjects, levels, topics) |
| **Session** | A specific lesson slot on the calendar (time, teacher, capacity) |
| **Booking** | Student X has a seat in that session |
| **MembershipPlan** | Product you sell (“10 tickets / month”, “Unlimited Japanese”) |
| **Membership** | Student’s active subscription + ticket balance |
| **ClassRequest** | Student asked for a custom time; teacher must approve |
| **HomeworkAssignment** | File exchange or journal prompt tied to a session |
| **SessionFeedback** | Teacher’s scores/notes after a lesson |

Relationships in one sentence: **Plans** gate **Bookings** on **Sessions** for **ClassOfferings** taught by **Users** in the **teacher** group.

---

## 7. Walkthroughs — follow the code

Do these with **`python manage.py runserver`** and **`npm run dev`** running. Log in as `demo_student` / `demo_teacher` / `demo1234`.

### Walkthrough A — Student books an open session

**Story:** Student picks a published lesson and spends 1 ticket.

```text
StudentSessionsPage.jsx
  → user clicks Book
  → StudentOpenSessionPanel.jsx (confirm modal)
  → api.js: POST /api/bookings/create/
  → scheduling/api/views.py: BookingCreateView
  → scheduling/services/booking.py: create_booking()
       checks membership, tickets, capacity, duplicate
  → saves Booking row
  → scheduling/services/notifications.py: email student + teacher
  → JSON back to React → BookingSuccessModal
```

**Files to open in order:**

1. `frontend/src/pages/StudentSessionsPage.jsx`
2. `frontend/src/components/StudentOpenSessionPanel.jsx`
3. `frontend/src/api.js` — search `bookings/create`
4. `scheduling/api/views.py` — `BookingCreateView`
5. `scheduling/services/booking.py` — `create_booking`

**Question to answer:** What happens if the student has zero tickets?

---

### Walkthrough B — Student requests a custom time

**Story:** No suitable open session — student requests a slot from teacher availability.

```text
StudentRequestClassPage.jsx
  → pick teacher OR "any available teacher"
  → AvailabilitySlotCalendar.jsx loads slots from API
  → POST /api/class-requests/
  → scheduling/services/class_requests.py: create_class_request() or create_open_class_request()
  → tickets HELD (not spent until approve)
  → email to teacher(s)
  → ClassRequestSuccessModal ("wait for approval email")

TeacherClassRequestsPage.jsx
  → POST …/approve/
  → approve_class_request() creates Session + Booking
  → notify_booking_created() → student gets booking email
```

**Files:**

1. `frontend/src/pages/StudentRequestClassPage.jsx`
2. `scheduling/services/scheduling_slots.py` — where slots come from
3. `scheduling/services/class_requests.py` — hold/approve/deny logic
4. `frontend/src/pages/TeacherClassRequestsPage.jsx`

---

### Walkthrough C — Student buys membership (Stripe)

**Story:** Student pays; tickets appear on their account.

```text
MembershipPage.jsx
  → POST /api/membership/checkout/
  → integrations/stripe/checkout.py
  → browser redirects to Stripe
  → student pays → Stripe webhook POST /api/payments/stripe/webhook/
  → scheduling/services/payments.py: fulfill_payment()
  → Membership updated, tickets added
  → React polls /api/membership/payments/<id>/ after return
```

**Local dev:** needs Stripe test keys + `stripe listen` (see `operations-guide.md` §9.2).

---

### Walkthrough D — Teacher creates a session

```text
TeacherCreateSessionPage.jsx
  → may load /api/teacher/scheduling-slots/
  → POST /api/teacher/sessions/
  → scheduling/services/sessions.py + availability checks
  → Session row created; optional Google Calendar event + Meet link
```

---

## 8. Where logic lives (cheat sheet)

| If you want to change… | Open… |
|------------------------|--------|
| Can student book? | `scheduling/services/booking.py` |
| Ticket cost / refund | `scheduling/services/tickets.py` |
| Which classes a plan covers | `scheduling/services/membership.py` |
| Class request rules | `scheduling/services/class_requests.py` |
| Availability / slots | `scheduling/services/availability.py`, `scheduling_slots.py` |
| Email text | `scheduling/services/notifications.py` |
| Stripe / payments | `scheduling/services/payments.py`, `integrations/stripe/` |
| Meet links | `scheduling/services/meetings.py`, `integrations/google/meet.py` |
| Homework files / purge | `progress/homework_services.py` |
| Progress charts | `progress/services.py` |
| API URL wiring | `scheduling/api/urls.py`, `progress/api_urls.py` |
| What student sees | `frontend/src/pages/` |

**Tests** in `scheduling/tests.py` and `progress/tests.py` describe expected behavior — read them like examples.

---

## 9. Two user interfaces (ignore one at first)

| UI | URL | Status |
|----|-----|--------|
| **React** | http://127.0.0.1:5173 | Primary — learn this |
| **Django templates** | http://127.0.0.1:8000 | Legacy — same services, older HTML |

Both call the same `services/` functions. When in doubt, grep the service name from the React API view.

---

## 10. Auth in plain English

1. Student logs in → `POST /api/auth/token/` → JWT **access** + **refresh** tokens.
2. React stores them in **`sessionStorage`** (per tab) — see `frontend/src/api.js`.
3. Every API call sends `Authorization: Bearer <access token>`.
4. Django checks token + user is active + user is in the right **Group** (student/teacher/staff).

Teachers also need **permission flags** for some actions (e.g. `manage_schedule`).

---

## 11. Integrations (optional extras)

The app **must run** without these; they turn on when env vars are set:

| Integration | When configured | When blank |
|-------------|-----------------|------------|
| Email | Real SMTP sends mail | Prints to terminal |
| Stripe | Real checkout | Mock purchase in DEBUG only |
| Google | Real Meet + Calendar | Placeholder Meet URL |

See `.env.example` and `operations-guide.md` §9.

---

## 12. How to run and test (muscle memory)

```bash
cd ~/repos/booking_scheduling_app
source .venv/bin/activate
python manage.py migrate
python manage.py bootstrap_sandbox --demo   # demo users

python manage.py runserver                  # :8000
cd frontend && npm run dev                  # :5173

python manage.py test                       # backend tests
cd frontend && npm run build                # production build check
```

**Demo logins:** `demo_student`, `demo_teacher`, `demo_staff` — password `demo1234`.

---

## 13. Study plan — tie courses to this repo

### While finishing CS50P (weeks 2–9)

| Week / topic | Activity in this repo |
|--------------|----------------------|
| Functions | Read one service file end-to-end (`booking.py`) |
| Unit tests | Run `python manage.py test scheduling.tests.BookingTests` |
| File I/O | Trace homework upload → `media/homework/` |
| OOP (later weeks) | Skim one `models.Model` class in `scheduling/models.py` |
| APIs (if covered) | Use browser DevTools → Network while booking |

**Don’t:** try to memorize every file. **Do:** complete Walkthrough A once.

### During / after CS50 Web

| Week / topic | Activity |
|--------------|----------|
| HTTP / routes | Map `urls.py` paths to views |
| Models | Draw ER diagram from §6 above |
| Auth | Trace login in `api.js` + JWT settings in `config/settings.py` |
| JavaScript | Pick one page component; follow `useState` / `useEffect` |
| Capstone mindset | Re-implement one small feature by hand (e.g. “list my bookings”) |

### After both courses

1. Read [`architecture-and-roadmap.md`](./architecture-and-roadmap.md) once — full picture.
2. Fix one small bug or UX item from [`future-features.md`](./future-features.md) without AI.
3. Deploy to a small VPS or Railway using [`operations-guide.md`](./operations-guide.md).

---

## 14. Explaining this to a hired engineer

Give them:

1. This repo + [`architecture-and-roadmap.md`](./architecture-and-roadmap.md)
2. [`operations-guide.md`](./operations-guide.md) + filled `.env.example` template
3. [`security.md`](./security.md)
4. Honest scope: **single-tenant** (one studio per deploy), not multi-tenant SaaS yet

Say: *“Business logic is in `scheduling/services/` and `progress/` services. React is display-only. Tests in `scheduling/tests.py` are the spec.”*

---

## 15. Glossary reminders

| Confused about… | Read |
|-----------------|------|
| User vs Postgres user | [`glossary.md`](./glossary.md) |
| ClassOffering vs Catalog | §6 above + architecture §3 |
| Session vs Booking | Session = slot; Booking = student’s seat in it |
| Tickets vs membership | Plan defines allowance; membership holds current balance |

---

## 16. What to learn next (in the product)

Not required for CS50 — this is **your** product backlog:

| Feature | Why it matters |
|---------|----------------|
| Availability-first booking | One UX for “book” and “request” — see architecture §11 Flow C |
| Multi-tenant | Many studios on one install — `future-features.md` §10 |
| Homework markup | Teacher draws on PDFs — `future-features.md` §1 |

---

*You built a real full-stack app. The courses give you vocabulary; this file gives you a map. Re-read one walkthrough per week until it feels boring — that’s when it sticks.*
