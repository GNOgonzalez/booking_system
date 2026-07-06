# Session progress & roadmap

**Created:** 2026-07-06  
**Branch:** `main` (large uncommitted working tree — ~49 modified files + new migrations/components)  
**Audience:** Owner / developer reference after the latest build sprint

Use this alongside [`architecture-and-roadmap.md`](./architecture-and-roadmap.md), [`audit-remediation-plan.md`](./audit-remediation-plan.md), and [`future-features.md`](./future-features.md).

---

## Executive summary

You have a **full-featured studio booking app**: Django + DRF backend, React SPA as the primary UI, role-based access (student / teacher / staff), memberships & tickets, homework & progress tracking, staff admin, and optional integrations (Stripe, Google, email).

The **audit remediation plan (Phases 0–22) is marked complete** in project docs. On top of that baseline, your **current working tree** adds substantial product polish: mobile navigation, student self-registration, class catalog roadmap, availability-driven scheduling slots, open class requests, booking/request confirmation flows, Stripe checkout polling, timezone fixes, and Gmail SMTP setup notes.

**Nothing on this branch is committed yet.** Before deploying or sharing, run migrations, tests, and consider splitting into reviewable commits or PRs.

---

## Part 1 — What you already had (sandbox + audit)

### Core platform

| Area | What it does |
|------|----------------|
| **Dual UI** | React SPA (`:5173`) primary; Django templates (`:8000`) legacy |
| **Auth** | Django Groups + JWT (React) or session (HTML) |
| **Scheduling** | Teachers create sessions from `ClassOffering` catalog; students book/cancel |
| **Membership gating** | Plans, ticket packs, subject-scoped plans, mock or Stripe payments |
| **Progress** | Session feedback, score dimensions, student dashboards, homework file exchange |
| **Staff admin** | Teachers, students, schedule, glossary, LLM config, branding, metrics, reports |
| **Teacher permissions** | Staff-controlled flags (`manage_schedule`, `write_reports`, `use_ai`, etc.) |

### Audit remediation (Phases 0–22 — complete per plan)

Security, privacy, and hygiene work including: inactive-user blocking, mock-payment prod guard, homework download auth, JWT/XSS notes, rate limiting, N+1 fixes, IDOR tests, CI, Ruff, LLM URL allowlist, frontend code splitting, progress API split, session history privacy, Stripe E2E path, user themes, onboarding checklist, Google OAuth scaffold, Markdown preview for blog/journal.

See [`audit-remediation-plan.md`](./audit-remediation-plan.md) progress table for the full checklist.

---

## Part 2 — What you built recently (current uncommitted work)

### Student experience

| Feature | Details |
|---------|---------|
| **Self-registration** | `POST /api/auth/register/` + `RegisterPage.jsx`; link from login |
| **Mobile navigation** | Drawer sidebar, top bar, backdrop, Escape to close, safe-area padding |
| **Per-tab JWT** | Tokens in `sessionStorage` (fixes cross-tab account switching) |
| **Timezone sync** | `loadMeProfile()` auto-sets browser timezone when profile is still UTC |
| **Datetime helpers** | Shared `frontend/src/utils/datetime.js` — local ↔ ISO for forms and display |
| **Booking UX** | Confirm modal before book; success modal with email/meeting link; “Booked” badge on calendar |
| **Duplicate book guard** | `student_booked` on open sessions API; disabled “Already booked” button |
| **Class requests — specific teacher** | Pick teacher → class → availability slot calendar → review modal → success modal |
| **Class requests — any teacher** | Open pool by subject/level/focus; eligible teachers notified on submit |
| **Request email flow** | Teacher emailed on submit; **student emailed on approval** (via booking confirmation), not on submit |
| **Membership checkout** | Stripe return URL polling; success/cancel handling; subject-scoped plan display |
| **Profile** | Theme, timezone, Google Calendar connect (teachers/staff) |

### Teacher experience

| Feature | Details |
|---------|---------|
| **Scheduling slots API** | `scheduling/services/scheduling_slots.py` — bookable times from availability minus busy |
| **Session create** | Slot picker, availability check, special-day handling |
| **Class requests inbox** | Approve/deny; open-request labeling; edit before approve |
| **Availability page** | Updates aligned with scheduling slot model |

### Staff experience

| Feature | Details |
|---------|---------|
| **Class catalog / roadmap** | `CatalogSubject → Level → Focus → Topic`; `StaffClassCatalogPage.jsx`, `ClassCatalogPicker.jsx` |
| **Class create** | Catalog-driven picker when creating offerings |
| **Membership plans** | Subject field on plans (`0026_membershipplan_subject`) |

### Backend & integrations

| Feature | Details |
|---------|---------|
| **Class request model** | Migration `0027` — nullable teacher/offering, `open_to_any_teacher`, subject/level/focus |
| **Notifications** | Teacher class-request email; booking confirmation on approve |
| **Google Meet / Calendar** | OAuth flow, `google_calendar_event_id` on sessions, meet link generation (needs real creds) |
| **Stripe** | Checkout success/cancel URLs from frontend; payment status polling endpoint |
| **Email** | Gmail app-password note in `.env.example`; strip spaces from app password in settings |
| **Tests** | Large expansion in `scheduling/tests.py` (class requests, slots, Stripe, registration, etc.) |

### New files (untracked — need `git add`)

```
frontend/src/components/AvailabilitySlotCalendar.jsx
frontend/src/components/BookingSuccessModal.jsx
frontend/src/components/ClassCatalogPicker.jsx
frontend/src/components/ClassRequestSuccessModal.jsx
frontend/src/pages/RegisterPage.jsx
frontend/src/pages/StaffClassCatalogPage.jsx
frontend/src/utils/datetime.js
scheduling/api/class_catalog_views.py
scheduling/migrations/0024–0027
scheduling/services/class_catalog.py
scheduling/services/registration.py
scheduling/services/scheduling_slots.py
scheduling/services/timezones.py
```

---

## Part 3 — Current state checklist

Before your next session:

```bash
cd ~/repos/booking_scheduling_app
source .venv/bin/activate
python manage.py migrate          # applies 0024–0027 if not yet run
python manage.py test             # full suite
cd frontend && npm run build && cd ..
```

**Demo accounts:** `demo_student`, `demo_teacher`, `demo_staff` · password `demo1234`

**Env you may have configured:**

- `EMAIL_HOST=smtp.gmail.com` + app password → real booking/request emails
- `STRIPE_*` → live test checkout (webhook via Stripe CLI)
- `GOOGLE_*` → OAuth + Meet (redirect must be `http://127.0.0.1:8000/...`, not LAN IP)

**Restart Django** after any `.env` change.

---

## Part 4 — Roadmap (recommended next steps)

### Immediate (stabilize this sprint)

| # | Task | Why |
|---|------|-----|
| 1 | **Commit or PR this work** | ~4k lines uncommitted; easy to lose context |
| 2 | **Run full test suite + manual smoke test** | Register → membership → book → request class → teacher approve |
| 3 | **Apply pending migrations on any other machine** | 0024–0027 required |
| 4 | **Verify Gmail + Stripe in your `.env`** | Restart runserver; test one booking email and one checkout |

### Short term — UX quick wins (1–2 sessions)

High impact, mostly frontend. See Part 5 for detail.

1. Loading states on calendar/list pages (sessions, bookings, class requests)
2. Empty states with CTAs (“No bookings → Browse sessions”, “No tickets → Membership”)
3. Fix `<a href>` → React `<Link>` on request-class link in sessions page
4. Student home: **next upcoming lesson** card
5. Class request **history with status** (pending / approved / cancelled)
6. Replace `window.confirm` with in-app modals (cancel booking, deny request, delete availability)
7. Mobile: scroll detail panel into view when selecting a calendar session

### Medium term — product (from `future-features.md`)

| Priority | Feature | Effort |
|----------|---------|--------|
| 1 | Homework PDF/image markup (iPad-friendly) | Medium–High |
| 2 | Production homework media (S3 or volume) | Medium |
| 3 | **Availability-driven booking refactor** (session born on first book) | High |
| 4 | Google Calendar sync (cancel events, ICS “Add to calendar”) | Low–Medium |
| 5 | Real Zoom meetings | Medium |
| 6 | Frontend Vitest + ESLint in CI | Medium |
| 7 | High-contrast theme | Low |

### Integrations & production (when you have creds + hosting)

| Integration | Today | Next |
|-------------|-------|------|
| **Email** | Console or Gmail SMTP | Production SMTP / transactional provider |
| **Stripe** | Test checkout + webhook | Live keys, webhook on deployed URL |
| **Google** | OAuth + placeholder Meet until consent | Production OAuth consent, token refresh |
| **Deploy** | Docker Compose / Procfile | TLS, `MEDIA_ROOT` volume, env secrets |
| **SimplyBook** | Inert adapter | Only if you need external sync |

### Architecture direction (longer term)

Per [`architecture-and-roadmap.md` §11](./architecture-and-roadmap.md):

- **Today:** Teacher creates `Session` → student books.
- **Target:** Student picks class + availability slot → session created on first booking.

You’ve already laid groundwork (`scheduling_slots`, class requests, availability calendar). The refactor would unify “book open session” and “request custom time” into one availability-first flow.

---

## Part 5 — UX audit (lookaround findings)

Review of the React app as of 2026-07-06. Grouped by impact.

### What’s already solid

- **Mobile shell** — drawer nav, touch targets, stacked form actions
- **Student booking** — filters, calendar, confirm + success modals, ticket-aware buttons
- **Class requests** — slot calendar, review confirm, success modal with approval-email messaging
- **Membership** — Stripe return polling, multi-membership purchase confirms
- **Teacher create session** — slot dropdown, outside-availability warning
- **Onboarding checklist** — progress, deep links, dismiss
- **Visual consistency** — cards, badges, `.error` / `.success`, modals

### High-impact quick wins

| Page / area | Gap |
|-------------|-----|
| `StudentSessionsPage` | No loading state; flashes empty before fetch |
| `StudentBookingsPage` | No loading; empty state has no CTA; shows past bookings under “upcoming” |
| `TeacherSessionsPage` | No loading or empty-state CTA to create session |
| `TeacherClassRequestsPage` | No loading; dense forms on mobile; approve without confirm |
| `StudentOpenSessionPanel` | “Not enough tickets” but no link to `/membership` |
| `StudentSessionsPage` | Uses `<a href>` for request-class link (full page reload) |
| `StudentHomeDashboard` | No next-lesson preview or pending-request summary |
| `StudentRequestClassPage` | Pending-only list; no approved/cancelled history |
| `TeacherAvailabilityPage` | Delete with no confirmation; no success feedback after save |
| `InboxPage` | Minimal — no intro, loading, or polished empty state |
| `ProfilePage` | Form blank until load; free-text timezone field |
| `OnboardingChecklist` | Silent failure if API errors |
| **Global** | `window.confirm` on some flows vs polished modals elsewhere |

### Medium-term UX improvements

- **Student home widget:** next lesson (time, teacher, join link), low-ticket warning
- **Bookings page:** upcoming vs past tabs; “starts in X hours” for today
- **Request history:** status badges + link to booking when approved
- **Teacher home widget:** today’s sessions, pending request count
- **Availability:** visual week grid (reuse slot calendar patterns)
- **Shared infrastructure:** `PageLoading` skeleton, toast notifications, in-app confirm dialog component
- **Nav badges:** pending class requests (teacher), optional unread inbox count
- **Multi-role users:** home page shows both student and teacher sections (today student-only dashboard is hidden if user is also teacher)

### Nice-to-haves

- Add to calendar (ICS / Google link) on booking success
- Waitlist when session full
- Agenda list view alternate to calendar
- Search sessions / teachers / classes
- Notification preferences in Profile
- Keyboard/a11y pass on modals (focus trap, screen reader announcements)
- Past booking archive with filters

### Suggested UX priority order

1. Loading + empty-state CTAs on booking/calendar pages  
2. `<Link>` fix + membership link when out of tickets  
3. Student home upcoming booking + request status history  
4. Teacher approve confirm + availability delete confirm  
5. Mobile scroll-to-panel on calendar selection  
6. Shared toast + confirm-dialog components  

---

## Part 6 — Suggested session prompts (copy-paste for Cursor)

**Stabilize & commit:**
```
Read docs/session-progress-and-roadmap.md Part 3. Run migrate, test, and npm run build.
Summarize any failures. Do not commit unless I ask.
```

**UX quick wins batch 1:**
```
Read docs/session-progress-and-roadmap.md Part 5 (high-impact quick wins).
Implement loading states and empty-state CTAs on StudentSessionsPage, StudentBookingsPage, and TeacherSessionsPage.
Match existing .empty and page-intro patterns. Propose before applying.
```

**Student home polish:**
```
Add a "Next lesson" card to StudentHomeDashboard using GET /api/bookings/.
Show date, session title, teacher, and link to /bookings or meeting URL if present.
```

**Availability-driven booking (large):**
```
Read docs/future-features.md §3 and architecture-and-roadmap.md §11.
Propose a minimal first step toward availability-first booking using scheduling_slots.py.
Do not rewrite everything at once.
```

---

## Part 7 — Documentation map (updated)

| Doc | Use when |
|-----|----------|
| **This file** | What’s done + what’s next after latest sprint |
| [`architecture-and-roadmap.md`](./architecture-and-roadmap.md) | System design, data model, API table |
| [`audit-remediation-plan.md`](./audit-remediation-plan.md) | Completed audit phases 0–22 |
| [`future-features.md`](./future-features.md) | Post-audit feature ideas with Cursor prompts |
| [`next-session-handoff.md`](./next-session-handoff.md) | Stripe/Google setup quick reference (partially superseded) |
| `CLAUDE.md` | AI assistant conventions |

---

*Last reviewed against working tree on 2026-07-06.*
