# Future: Student Progress & Class Reporting

**Status:** Planned — start **after** main booking system is done.  
**Reference:** `crud_project` (Reflet) — **read for requirements and logic, do not copy-paste code.**

---

## The plan in one sentence

Finish the **booking app** on Django (Phases 2–4, optionally 5–6), then build a **clean, second product** for progress/reporting using Reflet as a **spec**, not a merge.

---

## Why this order makes sense

| First: booking app | Then: progress/reporting |
|--------------------|---------------------------|
| Learn Django ORM, services, auth, Groups | Reuse those skills on harder domain |
| Simpler models (ClassSession, Booking) | Richer models (Session, Feedback, badges, charts) |
| Templates → optional React (Phase 5) | Can use DRF + React from day one if you did Phase 5 |
| One problem at a time | crud_project tells you *what* to build |

You won't throw away Reflet work — it becomes a **checklist**.

---

## What crud_project is for (reference only)

Use it to answer: *"What did the old app do?"*

| Reference in crud_project | Use it to decide |
|---------------------------|------------------|
| **`models.py`** | Which tables/relationships you need (Student, Session, Feedback, etc.) |
| **`crud.py`** | What queries and calculations exist (dashboard stats, history, averages) |
| **`badges.py`** | Business rules for badges |
| **`schemas.py` / API routes** | What data the UI needs (later: DRF serializers) |
| **`frontend/` dashboards** | What screens to build (charts, tables, modals) |
| **`import_csv.py`** | Whether you still need CSV import |
| **`docs/DATAFLOW.md`** | End-to-end data flow |

**Do not:** merge repos, run FastAPI + Django together long-term, or paste SQLAlchemy models into Django files.

---

## Clean schema vs Reflet legacy (SimplyBook + Sheets)

Reflet’s tables were shaped by **imports**, not by ideal domain design. That was fine for a prototype — don’t copy that shape forward.

### What made the old schema clunky

| Pattern in crud_project | Why it happened | Clean approach |
|-------------------------|-----------------|----------------|
| String primary keys (`email`, export IDs) | SimplyBook / Sheets rows | Django auto `id`; optional `external_id` for sync |
| Dates as strings (`booking_date`, `date_time`) | CSV columns | `DateTimeField` (UTC in DB, timezone in Profile) |
| Three user tables (Admin, Teacher, Student) | Each import source had its own row type | One Django `User` + Groups + `Profile` |
| `Booking` **and** `Session` loosely linked by string `booking_id` | Sheets had both concepts, merged in import | One lifecycle or explicit FK — designed in Phase 2+ |
| FK to `sessions.session_id` (natural key) not `id` | Export used SimplyBook session code | FK to model `id`; store SimplyBook code in `simplybook_session_id` |
| Duplicate columns (`event_name`, `class_name`, `membership` as free text) | Copied export headers | Normalized: FK to `Service` / `ClassType` or enums where it fits |
| `simplybook_client_id`, `student_type = "simplybook"` on every student | Import metadata | `ExternalIdentity` or nullable fields on `Profile` / `StudentProfile` — only when syncing |

**Rule:** Postgres tables describe **your business**. SimplyBook describes **their booking product**. Map between them at the edges.

### Target architecture (now and later)

```text
                    ┌─────────────────────┐
                    │  Your Postgres DB   │
                    │  (clean domain)     │
                    │  User, ClassSession │
                    │  Booking, Feedback  │
                    └──────────▲──────────┘
                               │
                    sync / map │  (future — not Phase 2)
                               │
                    ┌──────────┴──────────┐
                    │  SimplyBook API       │
                    │  (webhooks / poll)    │
                    └─────────────────────┘
```

**Today:** You own the data; teachers/students use your app (or admin).  
**Later (company ask):** Add `integrations/simplybook/` — fetch bookings/clients, map into **existing** tables, store external IDs for idempotent sync.

### Integration fields (when you need them — not day one)

Add **only when** syncing, e.g. on `Booking` or `Profile`:

| Field | Purpose |
|-------|---------|
| `simplybook_booking_id` | Unique, nullable — upsert key |
| `simplybook_client_id` | Match client on import |
| `synced_at` | Last successful pull/push |
| `source` | `app` \| `simplybook` \| `manual` (optional) |

Don’t design the whole schema around these columns. They’re **labels on the filing cabinet**, not the cabinet layout.

### What to take from Reflet vs redesign

| Take from Reflet | Redesign fresh |
|------------------|----------------|
| Feedback stars, badges, dashboard stats | Table shapes and string dates |
| Teacher/student report screens | Separate Admin/Teacher/Student tables |
| CSV import **workflow** idea | CSV column layout as schema |
| Business rules in `crud.py` / `badges.py` | Natural-key FKs and duplicate booking/session rows |

See also: [architecture-and-roadmap.md](./architecture-and-roadmap.md) for booking Phase 2 models (`ClassSession`, `Booking`) — those are the first clean domain tables.


| Layer | New Django approach |
|-------|---------------------|
| Auth | Same pattern as booking: Django user + Groups + Profile |
| Models | New Django models + migrations (design from Reflet, implement clean) |
| Business logic | `services/` modules (port **ideas** from `crud.py`, rewrite in Django ORM) |
| Admin | Django admin for staff + custom teacher/student pages |
| UI Phase 1 | Templates (like booking Phase 1–4) **or** skip to DRF + React if booking Phase 5 done |
| API | DRF when/if you want React dashboards like Reflet |

---

## One project or two?

**Recommended:** Same Django **project**, new **app** (e.g. `progress` or `reflet`).

```text
booking_scheduling_app/
├── config/
├── scheduling/          ← booking (ClassSession, Booking, …)
├── progress/            ← NEW app later (Session, Feedback, badges, …)
│   ├── models.py
│   ├── services/
│   ├── views/ or api/
│   └── templates/ or leave UI to React
└── docs/
```

**Why one project:**

- One Postgres database (if you want shared Django users and bookings ↔ sessions links later)
- One login system
- One deploy

**Alternative:** New repo if you want total separation — fine for learning, more duplication.

Decide when you start — not now.

---

## Suggested phases (progress app — draft)

Start from **Step 1** again when booking is done. Same teaching style: questions first, you code.

| Phase | Focus | crud_project reference |
|-------|--------|----------------------|
| **P0** | New app `progress/`, empty models, admin | `models.py` — list entities |
| **P1** | Auth reuse (same Users/Groups) | `deps.py` — who can see what |
| **P2** | Core models: Session, Feedback (minimal) | `models.py`, `crud.py` read paths |
| **P3** | Teacher: create/view reports | `TeacherDashboard.jsx`, teacher routes |
| **P4** | Student: view own progress | `StudentDashboard.jsx`, `/api/me/dashboard` |
| **P5** | Badges + stats services | `badges.py`, `get_student_dashboard_stats` |
| **P6** | Charts UI (templates or React) | `frontend/` components |
| **P7** | CSV import (optional) | `import_csv.py` |

Checkpoints at each phase — same as booking learning path.

---

## Overlap with booking app (decide later)

Some concepts exist in **both** systems:

| Concept | Booking app | Progress app |
|---------|-------------|--------------|
| Django user | ✅ | ✅ same users |
| Class / session | `ClassSession` (bookable slot) | Reflet `Session` (completed class w/ feedback) |
| Student ↔ class link | `Booking` | `StudentSessionFeedback` |

**Later decision:** Are these the **same** `Session` model with a lifecycle (scheduled → completed), or **two** models linked by FK? Don't decide until booking Phase 2 is done. Reflet + booking docs will inform that.

---

## Prerequisites before starting progress app

- [ ] Booking Phase 2 checkpoint (book / cancel works)
- [ ] Booking Phase 3–4 (or conscious deferral written down)
- [ ] Comfortable with: models, migrations, services/, Group checks
- [ ] Optional: Booking Phase 5 (DRF + React) if you want Reflet-style UI immediately

---

## Docs to use when you start

| Doc | Purpose |
|-----|---------|
| [django-vs-crud-project.md](./django-vs-crud-project.md) | File-by-file map Reflet → Django |
| [glossary.md](./glossary.md) | Terminology |
| crud_project `docs/PROJECT-STRUCTURE.md` | What each Reflet file did |
| crud_project `docs/DATAFLOW.md` | Data flow for reporting |
| [architecture-and-roadmap.md](./architecture-and-roadmap.md) | Big picture |

---

## Decision log entry (when you start)

Add to `LEARNING_PATH.md` decisions log:

```text
Progress/reporting app: greenfield Django app using crud_project as reference only.
Start after booking Phase X complete. Same project, new app `progress/`.
```

---

## Current focus

**Stay on booking Phase 2** when ready. This doc is the parking lot for the next product.
