# Future features

Potential product work **after** core studio functionality, security, and UX polish.

**Current priority order** (see [`session-progress-and-roadmap.md`](./session-progress-and-roadmap.md) Part 4):

1. **Functionality** — staff > teacher > student; staff sandbox permission  
2. **Security** — hardening before expanding staff powers  
3. **UI/UX** — polish  
4. **Then** — items in this file (markup, S3, availability refactor, SaaS, etc.)

Each section below includes a **Cursor prompt** you can paste when ready to implement.

**Before any feature:** read `CLAUDE.md`, `docs/cursor_ruleset.md`, and `docs/architecture-and-roadmap.md`. Business logic stays in `scheduling/services/` and `progress/` services — not in React or DRF views.

**Conventions for prompts below**

- Propose the plan first; say **proceed** when you want files changed.
- Run `python manage.py test` and `cd frontend && npm run build` before finishing.
- Do not commit unless you ask.

---

## Priority overview

| # | Feature | Effort | iPad-friendly |
|---|---------|--------|---------------|
| 1 | [Homework PDF/image markup](#1-homework-pdfimage-markup-overlay) | Medium → High | Yes |
| 2 | [Production media (S3)](#2-production-homework-media-s3) | Medium | — |
| 3 | [Availability-driven booking](#3-availability-driven-booking-refactor) | High | — |
| 4 | [Real Zoom meetings](#4-real-zoom-meetings) | Medium | — |
| 5 | [Google Calendar sync (cancel + ICS)](#5-google-calendar-sync-cancel--ics) | Low–Medium | — |
| 6 | [Staff: restrict hidden session history](#6-staff-permission-hidden-session-history) | Low | — |
| 7 | [High-contrast theme](#7-high-contrast-theme) | Low | — |
| 8 | [Frontend Vitest + ESLint CI](#8-frontend-vitest--eslint-in-ci) | Medium | — |
| 9 | [httpOnly cookie auth (BFF)](#9-httponly-cookie-auth-bff) | High | — |
| 10 | [Multi-tenant Organization](#10-multi-tenant-organization-saas) | Very high | — |
| 11 | [Stripe Billing (studio SaaS)](#11-stripe-billing-for-your-saas) | High | — |
| 12 | [Split `accounts` app](#12-split-accounts-app) | Medium | — |
| 13 | [Student badges / stats](#13-student-badges--engagement-stats) | Medium | — |

---

## 1. Homework PDF/image markup overlay

**Goal:** Teacher views a student’s uploaded **PDF or image**, draws on a **transparent overlay** (pen, highlighter, text boxes), **flattens** to a single PDF, and sends it back in the homework thread. Student can **download/export** the marked PDF.

**Not in scope:** Freeform infinite whiteboard, real-time collaboration, or editing the original file in place.

### Product flow

```text
Student uploads PDF/image → thread entry
Teacher opens “Mark homework”
  → bottom layer: PDF (pdf.js) or image
  → top layer: transparent canvas (pen / highlighter / text box)
Teacher saves → flatten page(s) + overlay → new PDF
  → new teacher HomeworkEntry with attachment
Student downloads marked PDF from thread (existing auth-gated download)
```

### Suggested phases

| Phase | Scope |
|-------|--------|
| **v1** | **Images only** (`.png`, `.jpg`, `.webp`) — best iPad + Apple Pencil ROI |
| **v2** | **Single-page PDF** via pdf.js; page-by-page for multi-page |
| **v3** | Undo/redo, zoom/pan, link marked entry to original (`marks_entry_id`) |

### Technical notes

- Reuse existing `HomeworkEntry` upload path (`progress/homework_services.py`, `HomeworkThread.jsx`).
- Flatten client-side: canvas + background → PNG → embed in PDF (`pdf-lib`) or upload flattened PNG/PDF.
- **7-day file TTL:** ensure original is still available when marking; marked copy gets its own expiry (same or longer).
- **10 MB upload cap** — compress or cap export resolution on iPad.
- iPad Safari: full-screen canvas, `touch-action: none`, Pointer Events for Apple Pencil.

### Key files

- `frontend/src/components/HomeworkThread.jsx` — “Mark” button, open markup modal
- New: `frontend/src/components/HomeworkMarkupEditor.jsx`
- `progress/homework_services.py` — optional `marks_entry_id` FK on `HomeworkEntry`
- `progress/models.py` — migration if linking original ↔ marked
- `scheduling/services/uploads.py` — already allows `.pdf` and images

### Cursor prompt

```
Read CLAUDE.md, docs/cursor_ruleset.md, and docs/future-features.md §1.

Implement homework markup v1: overlay annotations on student-uploaded IMAGES only (not PDF yet).

Flow:
- Teacher with assign_homework sees "Mark" on file-exchange entries that have an active image attachment.
- Full-screen editor: student image as background, transparent canvas on top.
- Tools: pen, highlighter (semi-transparent), text box (typed comment).
- iPad-friendly: pointer events, no scroll while drawing, reasonable default stroke width.
- Save: flatten to PNG or PDF, upload as new teacher HomeworkEntry on same assignment (optional body text).
- Student sees marked file in thread and downloads via existing /api/progress/homework/entries/<id>/download/.

Optional model: HomeworkEntry.marks_entry_id (FK self, null) linking marked reply to original.

Business logic in progress/homework_services.py. Propose plan first, then implement after I say proceed.
Run python manage.py test and npm run build. Don't commit unless I ask.
```

### Cursor prompt (v2 — PDF)

```
Read docs/future-features.md §1. Extend homework markup to PDFs.

Use pdf.js to render one page at a time as the background layer; same transparent canvas overlay as v1.
Flatten: composite PDF page + canvas → export PDF (pdf-lib or canvas→image→PDF).
Multi-page: next/prev controls; flatten current page or all pages (propose UX first).

Propose before apply. Tests for download auth unchanged. Don't commit unless I ask.
```

---

## 2. Production homework media (S3)

**Goal:** Homework and blog uploads survive deploy — not lost on ephemeral disks. WhiteNoise serves static only; `MEDIA_ROOT` needs a volume or S3.

### Key files

- `config/settings.py` — `STORAGES`, `AWS_*` env vars
- `.env.example`, `README.md` deploy section
- Optional: `django-storages` or custom storage backend

### Cursor prompt

```
Read docs/future-features.md §2 and README deploy section.

Add optional S3 media storage for production: when AWS_STORAGE_BUCKET_NAME is set, use S3 for FileField uploads (homework, blog, branding logo); local MEDIA_ROOT when unset (dev/tests unchanged).

Document env vars in .env.example. Keep homework download auth-gated API — do not make buckets public.

Propose storage backend choice and settings diff first. Minimal scope. Don't commit unless I ask.
```

---

## 3. Availability-driven booking refactor

**Goal:** Move toward **target product flow** (see `docs/architecture-and-roadmap.md` §11): teacher sets availability + class catalog → student picks slot → session created on first booking (optional), instead of teacher pre-creating every open session.

### Key files

- `scheduling/services/availability.py`, `scheduling/services/booking.py`
- `scheduling/models.py` — `Session`, `AvailabilityBlock`
- Student/teacher React booking pages

### Cursor prompt

```
Read docs/architecture-and-roadmap.md §11 and docs/future-features.md §3.

Propose a minimal "Option A" refactor: student books an availability slot + ClassOffering; create Session on first confirmed booking. Keep existing teacher-created sessions working (dual path during transition).

Business rules in scheduling/services/booking.py only. Propose schema/API changes before implementing. Don't commit unless I ask.
```

---

## 4. Real Zoom meetings

**Goal:** Replace placeholder Zoom links in `integrations/zoom/meetings.py` with real API-created meetings when `ZOOM_*` env creds are set — same pattern as Google Meet.

### Key files

- `integrations/zoom/meetings.py`
- `scheduling/services/meetings.py`
- `config/settings.py` — `ZOOM` dict

### Cursor prompt

```
Read docs/future-features.md §4 and integrations/google/meet.py (real Meet pattern).

Implement Zoom Server-to-Server OAuth meeting creation when ZOOM_ACCOUNT_ID, ZOOM_CLIENT_ID, ZOOM_CLIENT_SECRET are set. Degrade to placeholder URL when unset. Never crash without creds.

Propose first, then implement. Add tests with mocked HTTP. Don't commit unless I ask.
```

---

## 5. Google Calendar sync (cancel + ICS)

**Goal:** Extend Phase 20 Google OAuth: sync session **cancellations** to Calendar; attach real Meet link in **`.ics`** downloads for bookings.

**Note:** OAuth + real Meet on session create is already implemented (Phase 20).

### Key files

- `integrations/google/meet.py`, `integrations/google/oauth.py`
- `scheduling/services/notifications.py` or calendar invite builder
- Booking cancel flow in `scheduling/services/booking.py`

### Cursor prompt

```
Read docs/future-features.md §5. Google OAuth already exists.

Add: (1) when session cancelled, delete/patch Calendar event if teacher connected Google; (2) student booking .ics includes real meeting_url when present.

Graceful degrade if no credential. Propose before apply. Don't commit unless I ask.
```

---

## 6. Staff permission: hidden session history

**Goal:** Today all `staff` see hidden sessions (Phase 16). Optional tightening: junior front-desk staff cannot see student-hidden sessions; only owners/superusers or staff with `view_hidden_session_history`.

### Key files

- `scheduling/models.py` — `TeacherPermission` or new staff permission flag
- `progress/session_history.py`
- Staff UI badges on history views

### Cursor prompt

```
Read docs/audit-remediation-plan.md Phase 16 "Future tightening" and progress/session_history.py.

Add staff permission view_hidden_session_history (default True for existing staff or opt-in). Peer hide rules unchanged; staff without permission behave like peer teachers for hidden sessions.

Propose permission model first. Don't commit unless I ask.
```

---

## 7. High-contrast theme

**Goal:** Third theme option beyond light/dark/system for accessibility (`Profile.theme = contrast`). Phase 18 added light/dark/system.

### Key files

- `scheduling/models.py` — `Profile.THEME_CHOICES`
- `frontend/src/index.css` — `[data-theme="contrast"]` variables
- `frontend/src/pages/ProfilePage.jsx`

### Cursor prompt

```
Read docs/future-features.md §7. Themes already exist (light/dark/system).

Add high-contrast theme: stronger ink/background contrast, visible focus rings, WCAG-friendly link colors. Persist via PATCH /api/me/ like other themes.

Propose CSS token overrides only (no duplicate component rules). Don't commit unless I ask.
```

---

## 8. Frontend Vitest + ESLint in CI

**Goal:** Catch React regressions in CI — component tests for critical flows; `eslint-plugin-react-hooks` in `.github/workflows/ci.yml`.

### Key files

- `frontend/package.json`, `frontend/eslint.config.js`
- `.github/workflows/ci.yml`

### Cursor prompt

```
Read docs/future-features.md §8 and .github/workflows/ci.yml.

Add Vitest + @testing-library/react with 2–3 smoke tests (LoginPage, HomeworkThread render). Add ESLint flat config with react-hooks plugin. Extend CI frontend job to run npm test and npm run lint.

Minimal config; don't refactor all pages. Propose first. Don't commit unless I ask.
```

---

## 9. httpOnly cookie auth (BFF)

**Goal:** Move JWT out of `localStorage` to reduce XSS token theft risk. Documented deferral in `docs/security.md`.

**Approach sketch:** Backend-for-frontend sets httpOnly cookies; React uses credentials; or short-lived access in memory + refresh cookie.

### Key files

- `config/settings.py`, DRF JWT settings
- `scheduling/api/auth_views.py`
- `frontend/src/api.js`

### Cursor prompt

```
Read docs/security.md and docs/future-features.md §9.

Propose httpOnly cookie auth migration for the React SPA: refresh token in httpOnly cookie, access token strategy (cookie vs memory), CSRF for cookie POSTs, CORS/credentials. Do NOT implement in one shot — deliver a phased plan and Phase 1 only if I approve.

Fable-level security review mindset. Don't commit unless I ask.
```

---

## 10. Multi-tenant Organization (SaaS)

**Goal:** If productizing: each studio is an `Organization`; users belong to one org; data scoped by org FK.

### Cursor prompt

```
Read docs/future-features.md §10 and docs/next-session-handoff.md SaaS note.

Propose multi-tenant Organization model: schema (Organization, membership), migration strategy for single-studio data, query scoping middleware, staff signup flow. Planning doc + spike only unless I say implement Phase 1.

Don't commit unless I ask.
```

---

## 11. Stripe Billing for your SaaS

**Goal:** Distinct from **student membership checkout** (Phase 17). Billing *you* charge studios monthly for using the platform.

### Cursor prompt

```
Read docs/future-features.md §11. Student Stripe checkout already exists.

Propose Stripe Billing integration for platform subscription (studio pays you): Customer per org, Subscription, webhook for invoice.paid/failed. Out of scope: changing student membership flow.

Planning + env scaffold only unless I ask to build. Don't commit unless I ask.
```

---

## 12. Split `accounts` app

**Goal:** Move `Profile`, `/api/me/`, password change into a dedicated `accounts` app (see `docs/learn/TICKETS.md` TICKET-001 pattern).

### Cursor prompt

```
Read docs/learn/TICKETS.md (accounts split) and docs/future-features.md §12.

Extract Profile and me/password API into new accounts app without behavior changes. Update imports and urls. Run full test suite.

Propose file moves first. Don't commit unless I ask.
```

---

## 13. Student badges / engagement stats

**Goal:** Optional gamification from original progress spec — streaks, badges, “sessions this month” on student dashboard.

### Key files

- `progress/services.py` — `student_dashboard`
- `frontend/src/pages/StudentHomeDashboard.jsx`

### Cursor prompt

```
Read docs/learn/future-student-progress-app.md (badges section) and docs/future-features.md §13.

Add read-only engagement stats on student home: sessions attended this month, feedback count, optional simple streak. Compute in progress/services.py from existing Booking/SessionFeedback — no new models unless necessary.

Minimal UI on StudentHomeDashboard. Propose first. Don't commit unless I ask.
```

---

## Explicitly out of scope (for now)

| Item | Why | Track |
|------|-----|--------|
| Shared upcoming calendar (peer teacher slots) | Different product from session *history* | `TICKETS.md` |
| Freeform whiteboard | Homework markup overlay covers the need | this doc §1 |
| WYSIWYG HTML editor | XSS risk; use Markdown + bleach | — |

---

## Related docs

| File | Purpose |
|------|---------|
| [`audit-remediation-plan.md`](./audit-remediation-plan.md) | Completed / in-flight phased work (0–22) |
| [`architecture-and-roadmap.md`](./architecture-and-roadmap.md) | System design |
| [`cursor_ruleset.md`](./cursor_ruleset.md) | Propose before apply |
| [`TICKETS.md`](../TICKETS.md) | Bugs and small polish |
| [`CLAUDE.md`](../CLAUDE.md) | Stack, commands, API map |

---

## One-liner to start any feature

```
Read docs/future-features.md §<N>, CLAUDE.md, and docs/cursor_ruleset.md.
Implement the feature described there. Propose plan first; wait for my proceed.
Run tests and frontend build. Don't commit unless I ask.
```

Replace `<N>` with the section number (e.g. `§1` for homework markup).
