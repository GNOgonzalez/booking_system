# Audit remediation plan

**Created:** 2026-07-05  
**Source:** Full-stack audit (see chat / findings summary)  
**Use with:** Cursor + **Fable 5** (or your preferred agent), following `docs/cursor_ruleset.md`

---

## How to use this tomorrow

1. Open the repo in Cursor on your **personal account**.
2. Tell the agent: **“Follow `docs/cursor_ruleset.md` and `docs/audit-remediation-plan.md`. We are on Phase N.”**
3. For each phase: agent **proposes** the plan → you reply **“proceed”** → agent implements → you run **Verify** commands.
4. Check off phases in the progress table as you go.
5. **Part A (Phases 0–15):** audit remediation — finish **Phase 0–8** minimum before Part B.
6. **Part B (Phases 16–21):** planned features — session history privacy, Stripe, themes, onboarding, Google.
7. **Part C (Phase 22):** Markdown preview for blog + journal (after Part B or when ready).
8. `docs/next-session-handoff.md` is a short reference; **this file is the master plan**.

### Master prompt (paste at start of session)

```
Read docs/cursor_ruleset.md, docs/audit-remediation-plan.md, and CLAUDE.md.

Part A: fix audit findings (Phases 0–15). Part B: planned features (Phases 16–21). Part C: Phase 22 (Markdown preview).
Start with Phase 0, then Phase 1. Do not skip to Part B until Phase 0–8 are done or I say defer.

Rules:
- Propose changes before applying (per cursor_ruleset).
- Business logic stays in services/.
- Minimal focused diffs; match repo conventions.
- Run tests after each phase; fix regressions before continuing.
- Do not commit unless I ask.

Begin with Phase 0: confirm current branch state and run baseline tests.
```

---

## Progress tracker

| Phase | Topic | Priority | Done |
|-------|--------|----------|------|
| 0 | Baseline & branch | — | ☑ |
| 1 | Teacher session PATCH/DELETE crash | High | ☑ |
| 2 | Inactive users blocked on API | High | ☑ |
| 3 | Mock payments blocked in prod | High | ☑ |
| 4 | Media & homework privacy | High | ☑ |
| 5 | JWT / XSS hardening (pragmatic) | High | ☑ |
| 6 | Rate limiting on auth | Medium | ☑ |
| 7 | N+1 session `confirmed_count` | Medium | ☑ |
| 8 | IDOR & permission tests | Medium | ☑ |
| 9 | CI pipeline | Medium | ☑ |
| 10 | Ruff + lint hygiene | Low | ☑ |
| 11 | LLM key handling + URL allowlist | Medium | ☑ |
| 12 | Frontend bundle splitting | Medium | ☑ |
| 13 | Split `progress/api.py` | Medium | ☑ |
| 14 | Docs & legacy cleanup | Low | ☑ |
| 15 | Final verification (Part A) | — | ☑ |
| **Part B — planned features** | | | |
| 16 | Cross-teacher session history privacy | Feature | ☑ |
| 17 | Stripe E2E verification | Feature | ☑ |
| 18 | User theme preferences | Feature | ☑ |
| 19 | Initial onboarding checklist | Feature | ☑ |
| 20 | Google OAuth + Meet links | Feature | ☑ |
| 21 | Final verification (Part B) | — | ☑ |
| **Part C — content formatting** | | | |
| 22 | Markdown preview (blog + journal) | Feature | ☑ |

---

## Model selection (save Fable tokens)

Use **Fable 5** only where judgment errors are costly; use **Composer / fast model** for everything else. Start each phase on Fast with *“Propose only”*; switch to Fable before **proceed** on Fable phases.

| Tier | Cursor pick |
|------|-------------|
| **Fable 5** | Security, privacy, auth, OAuth |
| **Fast** | Spec’d fixes, CI, docs, verify-only |

### Part A — Audit (Phases 0–15)

| Phase | Topic | Model |
|-------|--------|-------|
| 0 | Baseline | Fast |
| 1 | Session PATCH/DELETE imports | Fast |
| 2 | Inactive users blocked | **Fable 5** |
| 3 | Mock payments blocked in prod | Fast |
| 4 | Media & homework privacy | **Fable 5** |
| 5 | JWT / XSS / CSP | **Fable 5** |
| 6 | Rate limiting on auth | Fast |
| 7 | N+1 `confirmed_count` | Fast |
| 8 | IDOR & permission tests | **Fable 5** (after Phase 2) |
| 9 | CI pipeline | Fast |
| 10 | Ruff / lint | Fast |
| 11 | LLM key + URL allowlist | **Fable 5** |
| 12 | Frontend bundle splitting | Fast |
| 13 | Split `progress/api.py` | Fast |
| 14 | Docs & legacy cleanup | Fast |
| 15 | Final verification (Part A) | Fast |

### Part B — Features (Phases 16–21)

| Phase | Topic | Model |
|-------|--------|-------|
| 16 | Cross-teacher session history | **Fable 5** |
| 17 | Stripe E2E verify | Fast |
| 18 | User themes | Fast |
| 19 | Onboarding checklist | Fast |
| 20 | Google OAuth + Meet | **Fable 5** |
| 21 | Final verification (Part B) | Fast |

### Part C — Content (Phase 22)

| Phase | Topic | Model |
|-------|--------|-------|
| 22 | Markdown preview + sanitize | **Fable 5** |

### Summary (Phases 0–22 in order)

| Model | Phases | Count |
|-------|--------|-------|
| **Fable 5** | 2, 4, 5, 8, 11, 16, 20, 22 | 8 of 23 |
| **Fast** | 0, 1, 3, 6, 7, 9, 10, 12, 13, 14, 15, 17, 18, 19, 21 | 15 of 23 |

```text
Fable 5:  2, 4, 5, 8, 11, 16, 20, 22
Fast:     0, 1, 3, 6, 7, 9, 10, 12, 13, 14, 15, 17, 18, 19, 21
```

**Token-saving tips:** Run Phases 15 & 21 yourself when possible. Phase 17 is mostly manual Stripe CLI. If Fast fails a non-Fable phase, retry once on Fast before escalating to Fable.

---

## Phase 0 — Baseline

**Goal:** Know you’re starting clean.

```bash
cd ~/repos/booking_scheduling_app
source .venv/bin/activate
python manage.py test
cd frontend && npm run build && cd ..
```

**Checklist**

- [ ] 33+ tests pass
- [ ] Frontend build succeeds
- [ ] Note any pre-existing failures in `TICKETS.md`

**Prompt**

```
Phase 0 only: run baseline tests and npm build. Report results. No code changes.
```

---

## Phase 1 — Teacher session PATCH/DELETE crash

**Audit ref:** HIGH — missing `update_session` / `cancel_session` imports  
**Files:** `scheduling/api/views.py`, `scheduling/tests.py`

**Fix**

1. Add: `from scheduling.services.sessions import cancel_session, update_session`
2. Add API test: teacher with `manage_schedule` can PATCH session capacity; DELETE cancels session.

**Verify**

```bash
python manage.py test scheduling.tests -k session
# Manual: PATCH /api/teacher/sessions/<id>/ as demo_teacher
```

**Prompt**

```
Phase 1 from docs/audit-remediation-plan.md:

Fix missing imports for update_session and cancel_session in scheduling/api/views.py TeacherSessionDetailView.

Add test(s) covering teacher PATCH and DELETE on /api/teacher/sessions/<id>/.

Propose first, then implement after I say proceed.
```

---

## Phase 2 — Block inactive users on API

**Audit ref:** HIGH — deactivated users keep JWT access  
**Files:** `scheduling/api/permissions.py` (new class), `config/settings.py` (optional default permission)

**Recommended approach**

1. Add `IsActiveUser` permission: `request.user.is_authenticated and request.user.is_active`
2. Combine with existing role checks OR set as default in `REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES']` alongside `IsAuthenticated`
3. Ensure **login** still returns clear error for inactive users (simplejwt may already reject at token obtain — verify; block on all authenticated routes regardless)
4. Add test: staff deactivates student → student JWT GET `/api/bookings/` → **403**

**Edge cases**

- Staff deactivating themselves mid-session
- Inactive teacher’s past sessions still visible to staff (read-only) — OK

**Verify**

```bash
python manage.py test scheduling.tests -k inactive
```

**Prompt**

```
Phase 2 from docs/audit-remediation-plan.md:

Implement IsActiveUser (or equivalent) so deactivated users cannot use JWT API until token expires.

Add tests. Propose approach before implementing.
```

---

## Phase 3 — Block mock payments in production

**Audit ref:** HIGH — free memberships if Stripe unset in prod  
**Files:** `scheduling/services/payments.py`, `config/settings.py`, `scheduling/tests.py`

**Fix**

1. In `purchase_membership()`: if `not settings.DEBUG` and Stripe not enabled, return error unless explicit env `ALLOW_MOCK_PAYMENTS=true` (default false)
2. Document in `.env.example` and README
3. Test: with `DEBUG=False` and no Stripe keys, POST `/api/membership/` returns 400

**Verify**

```bash
python manage.py test scheduling.tests.StripePaymentTests scheduling.tests -k mock
```

**Prompt**

```
Phase 3: prevent mock membership purchases in production unless ALLOW_MOCK_PAYMENTS is explicitly set. Add tests with override_settings(DEBUG=False).
```

---

## Phase 4 — Media & homework privacy

**Audit ref:** HIGH — production media not configured safely  
**Files:** `config/settings.py`, `config/urls.py`, `README.md`, optional `docs/deploy-media.md`

**Fix (minimal, secure-by-default)**

1. **Document:** homework must only be served via authenticated `HomeworkAttachmentDownloadView` — never public `/media/` for `homework/`
2. **Prod settings:** do not add `static(MEDIA_URL)` when `DEBUG=False` (already the case — confirm)
3. **Blog/branding images:** OK to be public URLs if served from CDN later; for now document that `/media/branding/` and `/media/blog/` may be public if nginx maps `/media/` — optional: serve branding via dedicated public view only
4. **Optional code:** add `MEDIA_SERVE_IN_DEBUG_ONLY = True` comment block in settings + deploy checklist in README

**Stretch (if time)**

- Add env `AWS_S3_*` scaffold comments for future S3 (no full impl required tomorrow)

**Verify**

- Confirm `config/urls.py` only mounts media when `DEBUG`
- Grep: no homework path served without auth check

**Prompt**

```
Phase 4: secure media strategy per audit. Confirm homework files are never publicly served in production; update README deploy section and .env.example. Propose before writing.
```

---

## Phase 5 — JWT / XSS hardening (pragmatic)

**Audit ref:** HIGH — JWT in localStorage  
**Files:** `config/settings.py`, `frontend/index.html` or Django middleware for CSP, `docs/security.md` (short)

**Pragmatic scope for tomorrow** (full httpOnly cookie auth is a multi-day project — defer to later)

1. **Shorten refresh token lifetime** in prod via env (e.g. 1 day) — optional
2. **Add CSP headers** when `DEBUG=False` (restrict `script-src 'self'`; allow Vite inline only in dev)
3. **Document** localStorage risk and future cookie/BFF migration in `docs/security.md`
4. **Frontend:** ensure blog `body` stays text-only render (no `dangerouslySetInnerHTML`) — verify

**Defer (note in docs)**

- httpOnly cookie + CSRF for SPA auth refactor

**Verify**

- Review `frontend/src/api.js` — no tokens in URLs/logs
- `python manage.py check --deploy` with `DEBUG=False` in `.env` test

**Prompt**

```
Phase 5 pragmatic JWT/XSS hardening: CSP for production, document localStorage token risk, verify no dangerouslySetInnerHTML. Do NOT rewrite entire auth to cookies in this phase.
```

---

## Phase 6 — Rate limiting on auth endpoints

**Audit ref:** MEDIUM — brute force on `/api/auth/token/`  
**Files:** `config/settings.py`, optional `scheduling/api/throttling.py`

**Fix (DRF built-in — minimal)**

```python
REST_FRAMEWORK = {
    ...
    'DEFAULT_THROTTLE_CLASSES': [...],  # optional global
    'DEFAULT_THROTTLE_RATES': {
        'login': '10/minute',
    },
}
```

Apply `AnonRateThrottle` + custom scope on token obtain view (subclass `TokenObtainPairView` or wrap in throttled APIView).

**Verify**

- Test or manual: 11th rapid login attempt returns 429

**Prompt**

```
Phase 6: add DRF rate limiting to JWT obtain (and optionally refresh). Keep scope minimal.
```

---

## Phase 7 — N+1 `confirmed_count` on session lists

**Audit ref:** MEDIUM  
**Files:** `scheduling/api/serializers.py`, `scheduling/api/views.py`, `scheduling/api/staff_views.py`

**Fix**

1. Create queryset helper or annotate in `OpenSessionListView`, `TeacherSessionListCreateView`, `StaffOverallScheduleView`:

```python
from django.db.models import Count, Q
Session.objects.annotate(
    confirmed_count=Count('bookings', filter=Q(bookings__status='confirmed'))
)
```

2. Update `SessionSerializer.get_confirmed_count` to use `getattr(obj, 'confirmed_count', None)` or fallback for detail views

**Verify**

```bash
# Django Debug Toolbar or assertNumQueries in test
python manage.py test scheduling.tests
```

**Prompt**

```
Phase 7: fix N+1 on SessionSerializer confirmed_count using queryset annotation on list views.
```

---

## Phase 8 — IDOR & permission tests

**Audit ref:** MEDIUM — limited coverage  
**Files:** new `scheduling/tests/test_permissions.py` or extend `scheduling/tests.py`

**Minimum tests to add**

| Test | Expect |
|------|--------|
| Student A cannot GET student B homework detail | 404 |
| Student cannot POST cancel student B booking | 404 |
| Non-staff cannot GET `/api/staff/teachers/` | 403 |
| Teacher cannot PATCH another teacher’s session | 404 |
| Homework download without access | 404 |
| Inactive user with valid JWT | 403 (after Phase 2) |

**Verify**

```bash
python manage.py test scheduling.tests progress  # add progress tests if in scheduling only
```

**Prompt**

```
Phase 8: add IDOR and permission tests per audit-remediation-plan.md table. Use APIClient + JWT tokens.
```

---

## Phase 9 — CI pipeline

**Audit ref:** MEDIUM — no GitHub Actions  
**Files:** `.github/workflows/ci.yml`

**Minimal workflow**

```yaml
on: [push, pull_request]
jobs:
  backend:
    - pip install -r requirements.txt ruff
    - python manage.py test
    - ruff check scheduling progress integrations config
  frontend:
    - cd frontend && npm ci && npm run build && npm audit --audit-level=high
```

**Optional:** `pip-audit` step (allow failure initially with comment)

**Verify**

- Push branch; CI green locally with `act` optional

**Prompt**

```
Phase 9: add .github/workflows/ci.yml running Django tests, ruff check, frontend build, npm audit.
```

---

## Phase 10 — Ruff & lint hygiene

**Audit ref:** LOW — 13 ruff issues  
**Files:** `requirements-dev.txt` or `requirements.txt`, `pyproject.toml` or `ruff.toml`, fix flagged files

**Fix**

1. Add `ruff` to dev requirements
2. Run `ruff check --fix` on `scheduling/ progress/ integrations/ config/`
3. Fix remaining manually (e.g. unused `labels` in `glossary.py`)

**Frontend (optional tomorrow)**

- Add ESLint + `eslint-plugin-react-hooks` to `frontend/` — separate small PR if time

**Verify**

```bash
ruff check .
python manage.py test
```

**Prompt**

```
Phase 10: add Ruff config, fix all current ruff issues, add ruff to CI if not already in Phase 9.
```

---

## Phase 11 — LLM key handling + URL allowlist

**Audit ref:** MEDIUM  
**Files:** `scheduling/api/llm_views.py`, `scheduling/api/serializers.py`, `integrations/llm/client.py`

**Fix**

1. Ensure staff LLM GET never returns raw `api_key` (mask or omit)
2. Allowlist `base_url` hosts in LLM client (reject `file://`, private IPs if feasible)
3. Document: prefer env `STUDIO_LLM_API_KEY` for prod later — optional stub in `.env.example`

**Verify**

- GET `/api/staff/llm/` as staff — response has no full key
- bandit B310 mitigated or `# nosec` with comment only if allowlist enforced

**Prompt**

```
Phase 11: redact LLM api_key in API responses; allowlist LLM base_url in integrations/llm/client.py.
```

---

## Phase 12 — Frontend bundle splitting

**Audit ref:** MEDIUM — 796 KB bundle  
**Files:** `frontend/src/App.jsx`

**Fix**

1. `React.lazy()` for heavy routes: `StaffReportsPage`, `StudentProgressPage`, `StaffMetricsPage`, `MembershipPage`, etc.
2. Wrap `<Routes>` in `<Suspense fallback={...}>`

**Verify**

```bash
cd frontend && npm run build
# Compare dist/assets/*.js chunk sizes — main chunk should shrink
```

**Prompt**

```
Phase 12: add React.lazy code splitting for heavy pages in App.jsx. Keep UX simple loading fallback.
```

---

## Phase 13 — Split `progress/api.py`

**Audit ref:** MEDIUM — ~637 line monolith  
**Files:** `progress/api/` package

**Target structure**

```text
progress/api/
  __init__.py      # re-export views for urls
  homework.py
  feedback.py
  dashboard.py
  staff.py
  score_dimensions.py
```

Update `progress/api_urls.py` imports only.

**Verify**

```bash
python manage.py test
# Smoke: homework + feedback in React UI
```

**Prompt**

```
Phase 13: split progress/api.py into progress/api/ package without behavior changes. Update api_urls imports. Run all tests.
```

---

## Phase 14 — Docs & legacy cleanup

**Audit ref:** LOW / maintainability  
**Files:** `CLAUDE.md`, `docs/architecture-and-roadmap.md`, `TICKETS.md`

**Tasks**

1. Document **HTML templates = legacy**; React SPA is primary UI
2. Document **`ClassType` = legacy**; use `ClassOffering`
3. Document staff homework POST bypasses `assign_homework` intentionally
4. Add resolved audit items to `TICKETS.md` or new `docs/audit-remediation-log.md` with dates

**Prompt**

```
Phase 14: documentation-only updates for dual UI, ClassType legacy, staff homework permission bypass. No behavior changes.
```

---

## Phase 15 — Final verification

**Goal:** Confirm all audit items addressed or explicitly deferred.

```bash
source .venv/bin/activate
python manage.py test
python manage.py check --deploy  # with DEBUG=False in .env temporarily
ruff check .
cd frontend && npm run build && npm audit && cd ..
```

**Manual smoke (from `docs/audit_instructions.md` §9)**

- [ ] Student book + cancel
- [ ] Class request approve/deny + no-refund cancel
- [ ] Inactive student blocked
- [ ] Mock purchase blocked with DEBUG=False
- [ ] Teacher session PATCH works
- [ ] Homework download auth
- [ ] Staff reports load (lazy route)

**Re-audit prompt**

```
Read docs/audit_instructions.md and re-run a focused audit on Phases 1–11 fixes only. Report any remaining High/Critical findings.
```

---

## Phase 16 — Cross-teacher session history privacy

**Goal:** Teachers who share a student can see **past lessons** with other teachers for continuity. Students or the teaching teacher can **hide** individual past sessions from **peer teachers**. Staff can still see hidden sessions for studio oversight (e.g. misconduct). Only peer teachers are blocked by hide flags.

**Context:** Students may take classes from more than one teacher. Today only the **student** sees full history on **My progress**; teachers see only their own sessions when writing reports. This phase adds peer history with opt-out privacy — **not** shared upcoming calendar slots.

### Product rules

| Rule | Detail |
|------|--------|
| **Scope** | **Past only** — `session.end_time <= now`, confirmed booking |
| **Default** | Visible to peer teachers who **share the student** (≥1 confirmed booking or session feedback between viewer and student) |
| **Hide** | **Student** or **session teacher** can hide per session; if **either** hides → hidden from **peer teachers only** |
| **Conflict** | **Hidden wins** for peers — student hide cannot be overridden by teaching teacher |
| **Peer sees** | Date, title, class/topic, teaching teacher, report status, **feedback scores + class notes** when shared |
| **Peer does not see** | Meeting links, homework threads, edit/delete on others’ feedback |
| **Teaching teacher** | Always sees own sessions (including when hidden from peers) |
| **Student** | Always sees own full history |
| **Staff (`staff` group)** | **Always sees all sessions, including hidden** — hide does not apply to staff |
| **Django admin / superuser** | Same as staff; use admin for deep investigation if needed |

### Staff oversight (misconduct & disputes)

Hide is **collaboration privacy**, not **legal privilege**. Studio staff must be able to review the full record when investigating teacher or student misconduct, billing disputes, or safety concerns.

| Viewer | Hidden sessions |
|--------|-----------------|
| Peer teacher | **Not visible** |
| Session teacher | Visible (they taught it) |
| Student | Visible (their history) |
| **Staff** | **Visible** — show badge: “Hidden from other teachers” + who hid (student / teacher / both) |
| Django superuser | Visible (admin + API) |

**UI for staff:** When viewing student history, hidden sessions appear in the timeline with a muted badge (e.g. “Hidden from teachers — hidden by student”). Staff must **not** be able to “un-hide on behalf of” a student without audit trail; they only **view** for oversight. Optional later: staff-only note field on `SessionHistoryPrivacy` for internal investigation refs.

**Future tightening (defer unless needed):** If you hire junior front-desk staff who should *not* see hidden sessions, add a staff permission (e.g. `view_hidden_session_history`) or restrict override to `is_superuser` only. For Phase 16 MVP, **all `staff` group members** bypass hide — matches `demo_staff` / studio-owner use case.

**Transparency copy (student + teacher toggles):**  
“Other teachers won’t see this lesson. Studio staff may still access records for safety and policy reasons.”

### Data model

Add `SessionHistoryPrivacy` (OneToOne → `Session`):

```text
hidden_by_student   bool  default False
hidden_by_teacher   bool  default False
```

Missing row = visible. `is_hidden_from_peers = hidden_by_student OR hidden_by_teacher`.

### Services

New module `progress/session_history.py` (or extend `progress/services.py`):

```text
teacher_shares_student(viewer, student) → bool
peer_can_view_session(viewer, session, student) → bool   # False if hidden AND viewer is peer teacher
staff_can_view_session(viewer, session) → bool           # True for staff group regardless of hide
student_history_for_teacher(viewer, student) → dashboard-shaped payload, filtered
student_history_for_staff(viewer, student) → full payload + privacy flags on each session
set_session_history_privacy(actor, session, *, hidden_by_student=None, hidden_by_teacher=None)
```

### API

| Method | Path | Role |
|--------|------|------|
| GET | `/api/teacher/students/<id>/history/` | Teacher with shared student |
| PATCH | `/api/teacher/sessions/<id>/history-privacy/` | Session teacher toggles `hidden_by_teacher` |
| PATCH | `/api/progress/sessions/<id>/history-privacy/` | Student toggles `hidden_by_student` |
| GET | `/api/staff/teachers/<tid>/students/<sid>/history/` | Staff — **includes hidden** sessions + `privacy` metadata |

### UI

1. **Teacher** — student history view (timeline like **My progress**, read-only for peer sessions; toggle on own past sessions).
2. **Student — My progress** — per past session: “Hide from other teachers” (with staff oversight disclaimer).
3. **Teacher — feedback / session detail** — same toggle after a lesson.
4. **Staff — student history** — full timeline including hidden sessions with badge + hider attribution.

### Files (expected)

- `progress/models.py` — `SessionHistoryPrivacy`
- `progress/migrations/` — new migration
- `progress/session_history.py` — visibility rules
- `progress/api.py` (or split package from Phase 13) — views
- `progress/api_urls.py`, `scheduling/api/urls.py` if needed
- `frontend/src/pages/` — teacher student history + privacy toggles on `StudentProgressPage.jsx`
- `scheduling/tests.py` or `progress/tests.py` — permission + hide tests

### Verify

```bash
python manage.py test progress scheduling.tests -k history
```

**Manual smoke**

- [ ] Teacher A and B both taught student S; B sees A’s past session on S’s history
- [ ] Student hides session → B no longer sees it; A still does
- [ ] Teacher A hides session → B no longer sees it
- [ ] Peer view has no meeting URL or homework links
- [ ] **Staff sees hidden session** with “Hidden from teachers” badge and who hid it
- [ ] Student/teacher toggle copy mentions staff may still access for policy/safety

**Prompt**

```
Phase 16 from docs/audit-remediation-plan.md:

Implement cross-teacher past session history with per-session privacy (student or teaching teacher can hide; hidden wins).

Follow product rules in Phase 16. Business logic in progress/session_history.py. Propose first, then implement after I say proceed.
```

---

## Phase 17 — Stripe E2E verification

**Goal:** Confirm real test-mode checkout + webhook + active membership on your machine.

**Prereq:** Phase 3 (mock payments blocked in prod) should be done first.

### Setup

1. Copy `.env.example` → `.env` if needed.
2. [Stripe Dashboard → Test API keys](https://dashboard.stripe.com/test/apikeys):
   ```bash
   STRIPE_SECRET_KEY=sk_test_...
   STRIPE_PUBLISHABLE_KEY=pk_test_...
   ```
3. Install [Stripe CLI](https://stripe.com/docs/stripe-cli):
   ```bash
   stripe listen --forward-to http://127.0.0.1:8000/api/payments/stripe/webhook/
   ```
   Put printed `whsec_...` in `.env` as `STRIPE_WEBHOOK_SECRET`.
4. Restart Django after `.env` changes.

### Test

1. React → `demo_student` / `demo1234` → **Membership** → **Pay with Stripe**.
2. Card `4242 4242 4242 4242`, any future expiry/CVC.
3. Webhook fires; `GET /api/membership/` shows active membership.

### Key files

- `integrations/stripe/checkout.py`, `webhooks.py`, `client.py`
- `scheduling/services/payments.py`
- `frontend/src/pages/MembershipPage.jsx`
- `scheduling/tests.py` — `StripePaymentTests`

### If something breaks

- 400 on checkout → plan missing (`Staff → Memberships` or bootstrap).
- Webhook 400 → `STRIPE_WEBHOOK_SECRET` mismatch; restart `stripe listen`.
- Still mock mode → `STRIPE_SECRET_KEY` empty or server not restarted.

**Prompt**

```
Phase 17: help me verify Stripe test mode end-to-end (checkout + webhook + membership active). Walk through .env setup and smoke test; fix any bugs found. No scope creep.
```

---

## Phase 18 — User theme preferences

**Goal:** Each user switches light / dark / system; persists on `Profile`.

### Approach

1. **CSS** — `frontend/src/index.css`: keep tokens in `:root`; add `[data-theme="dark"]` (optional `"contrast"`) overrides for `--bg`, `--surface`, `--ink`, `--blue-*`, etc.
2. **Backend** — `Profile.theme` — choices `light`, `dark`, `system` (default `system`); include in `serialize_me` / `PATCH /api/me/`.
3. **Frontend** — `useTheme.js`: apply from `getMe()`; `matchMedia` for `system`. Selector on **Profile & settings**; optional sidebar toggle.
4. **Sign-in** — respect `system` only (no user yet) or optional `localStorage` preview.

### Key files

- `scheduling/models.py`, migration
- `scheduling/api/serializers.py` — `serialize_me`, `MeUpdateSerializer`
- `frontend/src/index.css`, `ProfilePage.jsx`, `hooks/useTheme.js`

### Verify

- PATCH theme persists; manual: sidebar, cards, calendar, auth readable in dark mode.

**Prompt**

```
Phase 18: implement user theme preference (light/dark/system) on Profile, CSS variable themes, selector on Profile page. Minimal scope. Run migrate and tests.
```

---

## Phase 19 — Initial onboarding checklist

**Goal:** First-time users see a short guided checklist on home until complete or dismissed.

### MVP scope

| Role | Example steps |
|------|----------------|
| **Student** | Display name → membership/tickets → book or request class → open progress |
| **Teacher** | Availability → add class → first session (or class requests) |
| **Staff** | Branding → membership plan → add teacher → skim dashboard |

### Implementation

1. **Backend** — `Profile.onboarding_completed_at` or JSON `onboarding_state`; `GET/PATCH /api/me/onboarding/`; auto-complete steps in existing services when actions happen (first booking, first availability, etc.).
2. **Frontend** — `OnboardingChecklist.jsx` on home; `useOnboarding()`; deep links to relevant routes; dismissible.

### Key files

- `scheduling/models.py`, `scheduling/api/views.py`, `frontend/src/App.jsx`, `StudentHomeDashboard.jsx`

**Prompt**

```
Phase 19: add initial onboarding checklist for student/teacher/staff (first-run on home, dismissible, tracked on Profile/API). Don't duplicate business logic — services mark progress.
```

---

## Phase 20 — Google OAuth + real Meet links

**Goal:** Teacher-created sessions get real `meet.google.com/...` URLs instead of placeholders.

### What exists

- `config/settings.py` — `GOOGLE.CLIENT_ID`, `GOOGLE.CLIENT_SECRET`, `ENABLED`
- `integrations/google/meet.py` — placeholder
- `scheduling/services/meetings.py` — `create_meet_link(session)` on session create

### Build order

1. **Google Cloud** — Calendar API; OAuth consent (Testing OK); Web client; redirect `http://127.0.0.1:8000/integrations/google/callback/`; `.env` keys.
2. **OAuth** — `GoogleCredential` model (user, tokens, expires_at); `GET /api/integrations/google/connect/` + callback; UI “Connect Google Calendar” on Profile or teacher settings.
3. **Meet on session create** — Calendar `events.insert` with `conferenceData` in `integrations/google/meet.py`; degrade if teacher not connected.
4. **Optional later:** `.ics` with real link; cancel sync to Calendar.

### Key files

- `integrations/google/meet.py`, new `oauth.py`
- `scheduling/api/google_views.py`, `scheduling/models.py`, `ProfilePage.jsx`

### Verify

- [ ] Teacher connects Google once
- [ ] Create session with `google_meet` → real Meet URL
- [ ] Student booking shows working link

**Prompt**

```
Phase 20: implement Google OAuth + Calendar Meet links for teachers (replace placeholder in integrations/google/meet.py). Graceful degrade if not connected. Propose OAuth model and routes first.
```

---

## Phase 21 — Final verification (Part B)

**Goal:** Confirm feature work from Phases 16–20.

```bash
source .venv/bin/activate
python manage.py migrate
python manage.py test
cd frontend && npm run build && cd ..
```

**Manual smoke**

- [ ] Cross-teacher history + hide toggles (Phase 16)
- [ ] Stripe test purchase + webhook (Phase 17)
- [ ] Theme light/dark/system persists (Phase 18)
- [ ] Onboarding checklist shows and dismisses (Phase 19)
- [ ] Google Meet link on new session (Phase 20, if credentials set)

**Prompt**

```
Phase 21: run full test suite, migrate, frontend build. Smoke-test Phases 16–20 per audit-remediation-plan.md checklist. Report anything still broken.
```

---

## Phase 22 — Markdown preview (blog + journal)

**Goal:** Plain-text authoring with a **sanitized formatted preview** below the textarea — bold, links, lists, line breaks — without WYSIWYG or XSS risk.

**Context:** Blog posts and journal/homework messages are plain `<textarea>` today. Users want readable formatting; rendering raw HTML from user input would require strict XSS controls. Store **Markdown source**; render through one shared safe pipeline.

### Product rules

| Rule | Detail |
|------|--------|
| **Editor** | Keep `<textarea>`; add read-only **Preview** panel below (live as they type) |
| **Storage** | Same `TextField` columns — store Markdown/plain source, not HTML |
| **Render (public)** | Server: Markdown → **bleach** allowlist → safe HTML for display |
| **Preview = publish** | Same rules on client preview and server render (no mismatch) |
| **Scope v1** | `BlogPost.body`, `HomeworkEntry.body` (journal + file thread messages); optional: blog feed only first |
| **Out of scope** | Full WYSIWYG, arbitrary HTML paste, `dangerouslySetInnerHTML` without sanitization |

### Allowed formatting (suggested allowlist)

- Paragraphs, `**bold**`, `*italic*`, `[links](url)`, `-` lists, fenced code blocks (optional)
- Strip: `<script>`, `onerror=`, `javascript:` URLs, `<iframe>`, etc.

### Implementation

1. **Service** — `render_safe_markdown(text) -> str` in e.g. `scheduling/services/markdown.py` (used by blog + progress).
2. **API** — Optional `POST /api/markdown/preview/` with `{ body }` returns `{ html }` (bleached); or compute `body_html` on read in serializers.
3. **Frontend** — `BodyPreview.jsx`: textarea + preview; client lib + DOMPurify for live preview; trust server HTML on saved content display.
4. **Dependencies** — Python: `markdown`, `bleach`; npm: `marked` + `dompurify` (or preview via API only to avoid duplicate rules).

### Files (expected)

- `scheduling/services/markdown.py` (or shared under `progress/`)
- `scheduling/api/views.py` — preview endpoint (optional)
- `scheduling/api/serializers.py` — `body_html` on blog serializer
- `progress/api.py` — homework entry display field
- `frontend/src/components/BodyPreview.jsx`
- `BlogManagePage.jsx`, `BlogFeed.jsx`, `HomeworkThread.jsx`
- `requirements.txt` — `markdown`, `bleach`
- Tests: XSS payload stripped; benign Markdown renders

### Verify

```bash
python manage.py test scheduling.tests progress -k markdown
```

**Manual smoke**

- [ ] Type `**bold**` in blog — preview shows bold; feed shows bold
- [ ] Paste `<script>alert(1)</script>` — preview/feed show escaped or stripped text, no alert
- [ ] Journal entry preview matches saved display
- [ ] Newlines render correctly

**Prompt**

```
Phase 22 from docs/audit-remediation-plan.md:

Add Markdown authoring with sanitized preview for blog posts and homework/journal messages. Plain textarea + preview panel; store Markdown source; server markdown+bleach pipeline; shared render_safe_markdown(). Propose allowlist first, then implement after I say proceed.
```

---

## Explicit deferrals (after Part C)

| Item | Why defer | Track in |
|------|-----------|----------|
| Full httpOnly cookie auth | Large SPA auth refactor | `docs/security.md` / Phase 5 notes |
| S3 media production impl | Infra when deploying | README deploy section |
| Frontend Vitest suite | After CI stable | `TICKETS.md` |
| Split large JSX pages | Cosmetic maintainability | `TICKETS.md` |
| Shared upcoming calendar (peer slots) | Out of scope for session history | `TICKETS.md` |
| Multi-tenant `Organization` | SaaS later | `docs/next-session-handoff.md` |

---

## Suggested tomorrow schedule

### Part A — audit remediation

| Block | Phases | ~Time |
|-------|--------|-------|
| Morning 1 | 0 → 3 | 2–3 hr |
| Morning 2 | 4 → 6 | 2–3 hr |
| Afternoon 1 | 7 → 9 | 2–3 hr |
| Afternoon 2 | 10 → 11 | 1–2 hr |
| Evening | 12 → 15 | 2–4 hr (13 optional if tired) |

**Minimum before Part B:** Phases **0–8** (all High + core Medium security).

### Part B — planned features

| Block | Phases | ~Time |
|-------|--------|-------|
| Next session 1 | **16** (session history privacy) | 3–4 hr |
| Next session 2 | **17** (Stripe verify) | ~30 min |
| Next session 3 | **18** (themes) | 2–3 hr |
| Next session 4 | **19** (onboarding) | 3–4 hr |
| Next session 5 | **20** (Google OAuth + Meet) | 4–8 hr |
| Wrap-up | **21** | ~30 min |

**Suggested Part B order:** 16 → 17 → 18 → 19 → 20 (Stripe quick win after history; themes before onboarding; Google last — largest chunk).

### Part C — content formatting

| Block | Phases | ~Time |
|-------|--------|-------|
| When ready | **22** (Markdown preview) | 2–3 hr |

Can run after Phase 21 or in parallel with low-risk Part B items if you prefer blog/journal polish earlier.

---

## Related docs

| File | Purpose |
|------|---------|
| `docs/cursor_ruleset.md` | Agent behavior — propose before apply |
| `docs/audit_instructions.md` | Full audit checklist |
| `docs/next-session-handoff.md` | Short reference — **Phases 17–20 supersede this** |
| `docs/architecture-and-roadmap.md` | System design, XSS/Markdown notes (§14) |
| `docs/learn/` | CS50P / Django self-study (optional) |
| `CLAUDE.md` | Stack, commands, architecture |

---

## One-liner to resume any time

```
Continue from docs/audit-remediation-plan.md — next unchecked phase in the progress table (Part A, B, or C). Follow docs/cursor_ruleset.md.
```
