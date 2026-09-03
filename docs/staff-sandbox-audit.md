# Staff sandbox audit

**Goal:** the role hierarchy is **staff > teacher > student**, and staff can run the whole studio
from the app itself — no Django admin, no shell, no `.env` edits for day-to-day work.

Audited against `scheduling/api/urls.py`, `progress/api_urls.py`, and `frontend/src/App.jsx`.
Last updated 2026-08-27 (Phases 1–4 complete; TICKET-008/009 closed).

---

## 1. Role hierarchy rules

| Rule | Where it lives | Status |
|------|----------------|--------|
| Staff bypasses per-teacher capability checks | `teacher_permissions.teacher_can()` returns `True` for staff | Enforced |
| Staff acts *as* a teacher via `staff/teachers/<id>/…` mirrors of every teacher route | `StaffTeacherMixin` | Enforced |
| Staff cannot edit other staff accounts through the app | `users.update_user_account()` rejects staff targets | Enforced |
| Teachers cannot reach any `staff/` route | `IsStaff` permission class | Enforced (tested) |
| Students cannot reach teacher or staff routes | `IsStudent` / `IsTeacher` | Enforced (tested) |
| Staff does **not** need Django superuser | group membership only; no code reads `is_staff` / `is_superuser` | Enforced (Phase 1) |

`demo_staff` is seeded **without** `is_staff` / `is_superuser`, so a public demo does not expose
`/admin/`. Pass `--staff-superuser` to `bootstrap_sandbox` when you want admin access locally.

---

## 2. Capability matrix

Legend: **Yes** = staff can do it in the React app · **API** = endpoint exists, no UI yet ·
**No** = gap (ticketed below).

### Users

| Capability | Staff | Notes |
|------------|-------|-------|
| List teachers / students | Yes | Staff dashboard, `/staff/students` |
| Create teacher | Yes | `POST /api/staff/teachers/`, form on staff dashboard |
| Create student | Yes | `POST /api/staff/students/` for in-person signups |
| Rename (display name) | Yes | Both roles |
| Deactivate / reactivate | Yes | Both roles; blocks login |
| Reset a user's password | Yes | `POST /api/staff/{teachers,students}/<id>/password/`; staff targets refused |
| Delete a user | No | Intentional — deactivate instead, keeps history |
| Grant / revoke teacher capabilities | Yes | `/staff/teachers/<id>/permissions` |

### Scheduling

| Capability | Staff | Notes |
|------------|-------|-------|
| Studio-wide schedule | Yes | `/staff/schedule` |
| Create / edit / cancel any teacher's sessions | Yes | Teacher-scoped mirror routes |
| Manage any teacher's availability + special availability | Yes | |
| View a session roster | Yes | |
| Approve / deny / delete class requests | Yes | Per teacher, plus studio-wide queue at `/staff/requests` |
| Cancel a student's booking on their behalf | Yes | `POST /api/staff/bookings/<id>/cancel/` with a refund choice |

### Catalog

| Capability | Staff | Notes |
|------------|-------|-------|
| Add subject / level / focus / topics | Yes | `/staff/class-catalog` |
| Rename a roadmap entry | Yes | Phase 1 — also renames matching classes so the two stay in sync |
| Hide (deactivate) a roadmap entry | Yes | Phase 1 — drops out of teacher pickers, history intact |
| Delete a roadmap entry | Yes | Phase 1 — blocked while any class (or membership plan) still uses it |
| Create a class for any teacher | Yes | `/staff/classes/new` |
| Edit / deactivate any teacher's class | Yes | Teacher-scoped mirror routes |

### Money

| Capability | Staff | Notes |
|------------|-------|-------|
| Create / edit / delete membership plans | Yes | Delete blocked once a plan has members |
| Financial + booking reports | Yes | `/staff/reports` |
| Comp a membership | Yes | `/staff/students/<id>` — amount 0 |
| Record a cash / transfer sale | Yes | Same form with the amount collected; `Payment.provider = staff` |
| Add or remove tickets | Yes | Clamped to 0–999, logged with a reason |
| Extend, cancel, or reactivate a membership | Yes | `PATCH …/membership/<id>/` |
| See payment mode + Stripe status | Yes | `/staff/payments` — read-only, secret key masked |
| Edit Stripe keys | No | Env vars only, by design (would mean storing secrets in the DB) |
| Refund a payment | No | Stripe dashboard only |

### Studio settings

| Capability | Staff | Notes |
|------------|-------|-------|
| Glossary (rename student/class/session/…) | Yes | |
| Sign-in branding (name + logo) | Yes | |
| Score dimensions / metric names | Yes | |
| AI provider config + connection test | Yes | `/staff/ai` |
| Email + Google status | Yes | `/staff/integrations` — read-only, no secrets |
| Email + Google status | Yes | `/staff/integrations` — read-only, no secrets |
| Blog posts | Yes | |
| Audit trail of staff overrides | Yes | `/staff/activity` |
| Per-teacher feedback + homework oversight | API | Endpoints exist; no staff-facing screens |

---

## 3. Audit trail

Every staff override writes a `StaffActionLog` row: who acted, on whom, a human-readable
summary, a structured `detail` blob, and an optional reason staff typed at the time. Logged
actions are `user_created`, `password_reset`, `membership_granted`, `membership_updated`,
`tickets_adjusted`, and `booking_cancelled`.

Two views: the whole studio at `/staff/activity`, and the last ten entries for one student
inline on their panel. The log is append-only — nothing in the app edits or deletes rows.

`StaffAlert` is a different thing and stays separate: alerts are *inbound* notifications
(a student signed up, a payment landed), while this is a record of what staff *did*.

---

## 4. Remaining gaps

The four phases are done — no day-to-day studio operation requires Django admin or a shell.
What's left is convenience and consistency rather than missing power. TICKET-008
(studio-wide request queue) and TICKET-009 (multi-role home) are closed.

Deliberately **not** built: deleting users (deactivate instead, so history survives), editing
Stripe keys from the UI (they would have to live in the database), and refunding payments
(belongs in the Stripe dashboard, which has the real ledger).

Tickets are tracked in `docs/learn/TICKETS.md`.

---

## 5. Deleting vs hiding

The roadmap (`CatalogSubject` → `CatalogLevel` → `CatalogFocus` → `CatalogTopic`) is a *picker*,
while a teacher's `ClassOffering` stores subject/level/focus as plain text. That means:

- **Hide** is always safe: the entry disappears from teacher dropdowns, existing classes and past
  sessions are untouched.
- **Rename** cascades into matching classes (and class topics) so the picker and the classes never
  drift apart.
- **Delete** is only allowed when nothing references the entry — no class, and for subjects, no
  membership plan scoped to it. Otherwise the API returns a 400 telling staff to hide it instead.

Deleting a subject cascades to its levels, focuses, and topics, so the UI confirms with the number
of entries that will go with it.
