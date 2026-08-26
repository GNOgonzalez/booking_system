# Session progress & roadmap

**Branch:** `main`  
**Audience:** Owner / developer reference — what’s done and what’s next

**Last reviewed:** 2026-08-26 — roadmap reordered: **Functionality → Security → UI/UX**

Use this alongside [`architecture-and-roadmap.md`](./architecture-and-roadmap.md), [`audit-remediation-plan.md`](./audit-remediation-plan.md), and [`future-features.md`](./future-features.md).

**Priority order (current):**

1. **Functionality** — role hierarchy (`staff` > `teacher` > `student`); staff has full studio control (“sandbox permission”) without Django admin
2. **Security** — harden before widening staff powers or going fully public
3. **UI/UX** — polish after behavior and permissions are consistent

---

## Executive summary

You have a **full-featured studio booking app**: Django + DRF backend, React SPA as the primary UI, role-based access (student / teacher / staff), memberships & tickets, homework & progress tracking, staff admin, and optional integrations (Stripe, Google, email).

The **audit remediation plan (Phases 0–22) is marked complete** in project docs. Recent work includes Supabase + Render deploy (Gakko Studio), showcase seed, student home hub, booking UX polish, and staff dashboard alerts.

**Live demo:** Render API + static frontend; Supabase Postgres; `demo_student` / `demo1234` with `--showcase` seed.

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

## Part 4 — Roadmap (Functionality → Security → UI/UX)

### Tier 1 — Functionality (do first)

**Goal:** `staff` > `teacher` > `student` is consistent everywhere. Staff can run the whole studio from the React app — same power as the sandbox, without `/admin/`.

#### Role model (target)

```text
staff     → full studio control; bypasses teacher permission flags (teacher_can)
teacher   → scoped to own students/sessions; capabilities gated by staff-granted flags
student   → book, membership, progress, homework, own requests only
```

**Today:** Backend `teacher_can()` already returns `True` for staff. Gaps are missing APIs, missing staff UI, and a few flows that still require Django admin or env vars.

#### 1A — Staff “sandbox permission” audit

Full matrix: [`staff-sandbox-audit.md`](./staff-sandbox-audit.md). **All four phases are done** —
no day-to-day studio operation needs Django admin or a shell. TICKET-002 → TICKET-007 are closed
in [`learn/TICKETS.md`](./learn/TICKETS.md); TICKET-008 → TICKET-010 carry the leftovers.

| # | Task | Status |
|---|------|--------|
| 1 | **Role matrix doc + test pass** | **Done** — `staff-sandbox-audit.md` + `StaffSandboxAuditTests` |
| 2 | **Staff delete everywhere teachers can** | **Done** (via staff → teacher drill-down) |
| 3 | **Staff delete where only add exists** — class roadmap | **Done** — rename / hide / delete with in-use guards |
| 4 | **Staff cancel any booking** | **Done** — `POST staff/bookings/<id>/cancel/` with a refund choice |
| 5 | **Staff → Payments / Stripe** | **Done** — read-only `/staff/payments` (keys stay in env) |
| 6 | **Staff manage integrations** — Google + email status | Open — payments panel is the pattern to copy |
| 7 | **User lifecycle** | **Done** — staff create teachers *and* students, reset passwords, deactivate |
| 8 | **Remove Django admin dependency** | **Done** — `demo_staff` not superuser; password reset was the last admin-only flow |
| 9 | **Multi-role users** | Open — TICKET-009 |
| 10 | **Teacher permission enforcement** | Open — TICKET-010 |

**Money controls (Phase 2)** deliberately stop short of editing Stripe keys or issuing refunds:
keys would have to be stored in the database, and Stripe's dashboard owns the real ledger.
Cash and comped memberships are recorded as `Payment` rows with provider `staff` so reports
still balance, and every override lands in the `/staff/activity` audit log.

#### 1B — Teacher / student consistency

| # | Task | Notes |
|---|------|--------|
| 11 | Teacher denied actions show clear 403 + UI disable | Match staff-granted flags in nav (hide what they can’t do) |
| 12 | Class request history for students | Pending / approved / cancelled |
| 13 | Staff view of all pending requests studio-wide | Optional aggregate beyond per-teacher drill-down |

#### 1C — Integrations (functional, not polish)

| Integration | Functional next step |
|-------------|---------------------|
| **Stripe** | Staff UI + webhook URL display; students checkout when live |
| **Email** | Staff-visible mode (console / SMTP / provider) |
| **Google** | Studio OAuth status; teachers connect calendar |
| **Deploy** | Gakko Studio on Render + Supabase — **done**; document re-seed |

#### Deferred (after Tier 1 stable)

- Availability-first booking refactor (`future-features.md` §3)
- Homework PDF markup, S3 media, Zoom, multi-tenant SaaS — see [`future-features.md`](./future-features.md)

---

### Tier 2 — Security (after staff powers expand)

**Goal:** Safe to expose Gakko Studio publicly while staff has full sandbox control.

| # | Task | Why |
|---|------|-----|
| 1 | **`demo_staff` not superuser** on public demo | Superuser + public URL = admin risk |
| 2 | **IDOR re-audit** after new staff delete/cancel endpoints | Every new staff write gets a test |
| 3 | **Secrets hygiene** | Stripe/LLM keys: env preferred; if staff UI stores keys, encrypt + mask like LLM |
| 4 | **Public demo guardrails** | `ALLOW_MOCK_PAYMENTS=true` only on demo; document prod values |
| 5 | **CSP on frontend host** | Django CSP doesn’t cover Render static site |
| 6 | **Rate limits review** | Register, login, checkout, staff destructive actions |
| 7 | **JWT in sessionStorage** | Document trade-off; plan httpOnly cookies (`future-features.md` §9) when ready |
| 8 | **Supabase + Render** | SSL required, no secrets in git, rotate if password pasted in chat |
| 9 | **Upload / download auth** | Homework, blog — regression tests after changes |
| 10 | **Stripe webhook** | Signature verify; idempotent fulfillment (already implemented — verify on live URL) |

Reference: [`security.md`](./security.md), [`audit-remediation-plan.md`](./audit-remediation-plan.md).

---

### Tier 3 — UI/UX (after Tier 1–2)

Polish and delight — not permission or security fixes.

#### Done (showcase sprint)

- Student home hub (next lesson, low tickets, pending requests)
- Booking loading / empty states / upcoming vs past tabs
- `<Link>` fix, membership link when out of tickets
- Staff dashboard alerts (users / membership / financial)
- Mobile nav shell

#### Remaining UX backlog

| # | Task | Area |
|---|------|------|
| 1 | In-app confirm modals (replace `window.confirm`) | Global |
| 2 | Shared toast + loading skeleton component | Global |
| 3 | Class request status history + badges | Student |
| 4 | Teacher home widget (today’s sessions, pending requests) | Teacher |
| 5 | Nav badges (pending requests, unread alerts) | Teacher / staff |
| 6 | Mobile scroll-to-panel on calendar select | Calendar pages |
| 7 | Inbox, Profile, onboarding polish | Student / all |
| 8 | Teacher approve/deny confirm modals | Teacher |
| 9 | “Add to calendar” on booking success | Student |
| 10 | High-contrast theme | Profile / themes |

Detail: Part 5 below (audit table — treat **Done** rows as closed).

---

### Architecture direction (longer term — not current sprint)

Per [`architecture-and-roadmap.md` §11](./architecture-and-roadmap.md):

- **Today:** Teacher creates `Session` → student books.
- **Target:** Student picks class + availability slot → session created on first booking.

Groundwork exists (`scheduling_slots`, class requests). Defer until Tier 1 role/staff work is solid.

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

| Page / area | Gap | Status |
|-------------|-----|--------|
| `StudentSessionsPage` | Loading state | **Done** |
| `StudentBookingsPage` | Loading; empty CTA; upcoming vs past | **Done** |
| `StudentOpenSessionPanel` | Link to `/membership` when out of tickets | **Done** |
| `StudentSessionsPage` | `<Link>` for request-class | **Done** |
| `StudentHomeDashboard` | Next lesson + pending requests | **Done** |
| `TeacherSessionsPage` | No loading or empty-state CTA to create session | Open |
| `TeacherClassRequestsPage` | No loading; dense forms on mobile; approve without confirm | Open |
| `StudentRequestClassPage` | Pending-only list; no approved/cancelled history | Open (Tier 1) |
| `TeacherAvailabilityPage` | Delete with no confirmation; no success feedback after save | Open (Tier 3) |
| `InboxPage` | Minimal — no intro, loading, or polished empty state | Open (Tier 3) |
| `ProfilePage` | Form blank until load; free-text timezone field | Open (Tier 3) |
| `OnboardingChecklist` | Silent failure if API errors | Open (Tier 3) |
| **Global** | `window.confirm` on some flows vs polished modals elsewhere | Open (Tier 3) |

### Medium-term UX improvements

- **Staff dashboard alerts (done v1):** in-app users / membership / financial streams with per-staff unread; email later
- **Student home widget:** next lesson (time, teacher, join link), low-ticket warning
- **Bookings page:** upcoming vs past tabs; “starts in X hours” for today
- **Request history:** status badges + link to booking when approved
- **Teacher home widget:** today’s sessions, pending request count
- **Availability:** visual week grid (reuse slot calendar patterns)
- **Shared infrastructure:** `PageLoading` skeleton, toast notifications, in-app confirm dialog component
- **Nav badges:** pending class requests (teacher), optional unread inbox count / staff alert count
- **Multi-role users:** home page shows both student and teacher sections (today student-only dashboard is hidden if user is also teacher)

### Nice-to-haves

- Add to calendar (ICS / Google link) on booking success
- Waitlist when session full
- Agenda list view alternate to calendar
- Search sessions / teachers / classes
- Notification preferences in Profile
- Keyboard/a11y pass on modals (focus trap, screen reader announcements)
- Past booking archive with filters

### Suggested UX priority order (Tier 3 only — after Functionality + Security)

1. In-app confirm modals + shared toast component  
2. Class request status history (also tracked in Tier 1)  
3. Teacher home widget + nav badges  
4. Mobile scroll-to-panel on calendar selection  
5. Inbox / Profile / onboarding polish  
6. High-contrast theme  

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
| [`operations-guide.md`](./operations-guide.md) | Deploy, onboard a studio, maintain, IT handoff |
| [`learn-the-app.md`](./learn-the-app.md) | Plain-English tour; CS50-aligned study path |
| [`architecture-and-roadmap.md`](./architecture-and-roadmap.md) | System design, data model, API table |
| [`future-features.md`](./future-features.md) | Post-audit feature ideas with Cursor prompts |
| [`next-session-handoff.md`](./next-session-handoff.md) | Stripe/Google setup quick reference (partially superseded) |
| `CLAUDE.md` | AI assistant conventions |

---

*Last reviewed against working tree on 2026-08-26.*
