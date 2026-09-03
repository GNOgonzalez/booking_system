# Tickets

Use this file like your crud_project ticket system when you debug and adjust the app after the initial build.

> Learning Django? Work through **`LEARN_DJANGO.md`** first — an ordered, offline-friendly
> course (LEARN-01 → LEARN-43) built on this app: Django fundamentals, app patterns, APIs/React/
> deploy, then a full **testing** week and a **DevOps / maintaining vibecoded apps** week. This
> file (`TICKETS.md`) is for real bugs.

## Format

```markdown
### TICKET-001 — Short title
**Status:** open | in-progress | done
**Area:** api | templates | services | frontend | auth
**Reported:** YYYY-MM-DD

**Expected:**
**Actual:**
**Steps:**
1.
2.

**Notes / fix:**
```

---

## Open

### TICKET-000 — Example (delete when you add real tickets)
**Status:** open  
**Area:** docs  
**Reported:** 2026-06-25  

**Expected:** You track bugs here while studying CS50.  
**Actual:** Sandbox build is complete; polish happens via tickets.  
**Steps:** Reproduce an issue, file a ticket, fix in a focused commit.

**Notes / fix:**

---

### TICKET-001 — (Someday) split out an `accounts` app
**Status:** open  
**Area:** architecture  
**Reported:** 2026-07-01  

**Expected:** User identity (Profile + profile/password API) lives in its own app, the textbook Django pattern.  
**Actual:** `Profile` and the `/api/me/` + `/api/me/password/` endpoints live inside `scheduling`.  
**Steps:** Only do this when the code hurts (e.g. `scheduling` has too many unrelated models, or you want to reuse accounts elsewhere). Not needed now.

**Notes / fix:** Lowest-risk candidate would be `accounts` (move `Profile`, profile/password serializers + views). Other future splits: `billing` (membership/payments), `messaging`, `curriculum`. Don't split preemptively.

---

## Done

### TICKET-008 — Staff cannot see a studio-wide pending class request queue
**Status:** done  
**Area:** frontend  
**Reported:** 2026-08-26 · **Closed:** 2026-08-27

**Notes / fix:** `pending_requests_studio()` returns every pending `ClassRequest` once (open-pool rows are not duplicated per matching teacher). `GET /api/staff/class-requests/` includes `candidate_teachers` so staff can claim an open request. Approve/deny reuse `/api/staff/teachers/<id>/class-requests/<pk>/…`. UI at `/staff/requests`. Covered by `StaffClassRequestQueueTests`.

---

### TICKET-009 — Multi-role users only see one dashboard
**Status:** done  
**Area:** frontend  
**Reported:** 2026-08-26 · **Closed:** 2026-08-27

**Notes / fix:** `HomePage` in `App.jsx` now stacks sections independently: student dashboard if `student`, staff tools if `staff`, teacher tools if `teacher`. Intro copy joins every role instead of picking one.

---

### TICKET-010 — Audit `IsTeacher` endpoints for missing `teacher_can` checks
**Status:** done  
**Area:** api  
**Reported:** 2026-08-26 · **Closed:** 2026-08-26

**Expected:** Every teacher write checks the staff-granted capability flag; staff bypasses it.  
**Actual:** Two gaps. `TeacherProgressListCreateView` (`progress/api/dashboard.py`) created `ProgressReport` rows with no `write_reports` check, while the equivalent `SessionFeedback` view did check. Separately, the class request approve / deny / delete views checked ownership but no capability at all — and approving *creates a Session*, so a teacher with `manage_schedule` switched off could still put lessons on the calendar by approving student requests.

**Notes / fix:** Added the `teacher_can('write_reports')` guard to `perform_create`, matching the pattern in `progress/api/feedback.py`. Added `teacher_can('manage_schedule')` to `TeacherClassRequestApproveView`, `…DenyView`, and `…DeleteView`. Those three check `request.user` rather than the resolved teacher, so staff acting on a teacher's behalf still pass (`teacher_can` returns `True` for staff).

Audited every other teacher view. The remaining ones without a `teacher_can` call are reads (student lists, availability preflight, scheduling slots, homework detail, own permission flags), so no flag applies.

**Why the first pass missed the class request views:** the audit grepped for `permission_classes = [IsTeacher]`, and those three views use `IsTeacherOrStaff`. Grep by capability, not by permission class — any endpoint that writes on a teacher's behalf needs a flag regardless of which permission class guards it.

Covered by `TeacherWriteReportsPermissionTests` (`progress/tests.py`) and `TeacherCapabilityEnforcementTests` (`scheduling/tests.py`), which revokes each of the five write capabilities in turn, asserts 403 and that nothing was persisted, and includes a positive control plus a staff-bypass case.

---

### TICKET-002 — Staff cannot grant or adjust a student's membership / tickets
**Status:** done  
**Area:** api  
**Reported:** 2026-08-26 · **Closed:** 2026-08-26

**Notes / fix:** Added `scheduling/services/membership_admin.py` (`student_membership_overview`, `grant_membership`, `adjust_tickets`, `update_membership`) behind `GET/POST /api/staff/students/<id>/membership/` and `PATCH …/<membership_id>/`, plus `StaffStudentMembershipPage`. Grants reuse `grant_plan_to_user()` so subscription vs ticket-pack logic is not duplicated, and record a `Payment` with the new `staff` provider — 0 for a comp, the collected amount for a cash sale. Ticket adjustments are clamped to 0…999 and every write logs a `StaffActionLog` row. Covered by `StaffMembershipAdminTests`.

---

### TICKET-003 — Staff cannot reset a user's password
**Status:** done  
**Area:** auth  
**Reported:** 2026-08-26 · **Closed:** 2026-08-26

**Notes / fix:** `staff_reset_password()` runs Django's validators and refuses staff targets; exposed at `POST /api/staff/teachers/<id>/password/` and `POST /api/staff/students/<id>/password/`. UI is inline on the staff dashboard (teachers) and the student panel. Covered by `StaffUserAdminTests`.

---

### TICKET-004 — Staff cannot create a student account
**Status:** done  
**Area:** api  
**Reported:** 2026-08-26 · **Closed:** 2026-08-26

**Notes / fix:** `POST /api/staff/students/` reuses `create_studio_user(role='student')` with an "Add student" form on `/staff/students`. Deliberately does not emit the "new student" alert that self-registration does — staff already know they just created the account.

---

### TICKET-005 — Staff cannot cancel a student's booking
**Status:** done  
**Area:** api  
**Reported:** 2026-08-26 · **Closed:** 2026-08-26

**Notes / fix:** `cancel_booking()` gained a keyword-only `refund` flag (defaults to `True`, so student self-cancel is unchanged); `staff_cancel_booking()` wraps it, logs the action, and reports whether the ticket came back. `POST /api/staff/bookings/<id>/cancel/` with `{"refund": true|false}`, surfaced as two buttons on the student panel. Covered by `StaffBookingOverrideTests`.

---

### TICKET-006 — No staff view of Stripe / payment configuration
**Status:** done  
**Area:** api  
**Reported:** 2026-08-26 · **Closed:** 2026-08-26

**Notes / fix:** `payment_settings_status()` reports mode, which env keys are set, the webhook URL to paste into Stripe, and completed totals per provider. The secret key is masked to `sk_test…mnop` and a test asserts the raw key never appears in the response. Read-only by design: editing keys from the UI would mean storing them in the database.

---

### TICKET-007 — No audit log of staff actions
**Status:** done  
**Area:** services  
**Reported:** 2026-08-26 · **Closed:** 2026-08-26

**Notes / fix:** New `StaffActionLog` model + `scheduling/services/staff_audit.py`. Written by user creation, password reset, membership grant/update, ticket adjustment, and booking cancellation, each with an optional staff-typed reason. Visible at `/staff/activity` (whole studio) and inline on the student panel (last 10 for that student).
