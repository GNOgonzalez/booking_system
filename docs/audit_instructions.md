# Full-Stack Code Audit Instructions

Structured guidelines for auditing **booking_scheduling_app**. Use for manual reviews, Cursor/LLM audits, or future CI/CD setup.

**Companion docs:** `CLAUDE.md` (architecture rules), `docs/cursor_ruleset.md` (audit trigger + approval workflow), `docs/architecture-and-roadmap.md` (feature map).

Audits run **only when explicitly requested**. See `docs/cursor_ruleset.md` §1.

---

## 0. Project context (read first)

### Stack (actual — not aspirational)

| Layer | Technology | Notes |
|-------|------------|--------|
| Backend | Django 5.2, DRF, simplejwt | Python 3.14 |
| Database | PostgreSQL 16 (SQLite in tests) | |
| Frontend | React 19 + Vite | **JavaScript (`.jsx`)** — not TypeScript |
| Auth | Django Groups + JWT (React) / sessions (HTML) | Groups: `student`, `teacher`, `staff` |
| Deploy | Docker, gunicorn, WhiteNoise | Media **not** served by WhiteNoise |
| Tests | `python manage.py test` | No pytest, no frontend test runner yet |

### Apps & scope

| Path | Audit focus |
|------|-------------|
| `scheduling/` | Booking, sessions, membership, staff API, integrations entry |
| `scheduling/services/` | **Primary business logic** — must be source of truth |
| `scheduling/api/` | DRF views, serializers, permissions, staff_views |
| `progress/` | Feedback, homework, score dimensions, student dashboard |
| `integrations/` | Stripe, Google Meet, Zoom, LLM client |
| `frontend/src/` | React SPA — display + API calls only |
| `scheduling/views/` + templates | Legacy HTML UI — parity with services |
| `config/` | Settings, security, CORS, JWT, env-driven integrations |

### Architecture rules to enforce

1. Business rules live in `scheduling/services/` and `progress/services.py` / `progress/homework_services.py`.
2. DRF views and HTML views call services — **never duplicate logic** in React or templates.
3. **POST** for writes; **GET** for lists.
4. Integrations **degrade gracefully** when env credentials are missing — no crashes.

---

## 1. Audit process

### 1.1 Before starting

1. Confirm scope (full repo vs single app vs pre-deploy).
2. Run tooling baseline (§7) and record what exists vs missing.
3. Read `TICKETS.md` for known issues — don’t duplicate unless verifying fix.

### 1.2 During the audit

- Trace **critical flows** end-to-end: book session, cancel, membership purchase, class request approve/deny, homework upload, staff permission change.
- For each finding: **location**, **severity**, **risk**, **recommendation**.
- Double-check suggested fixes and note **edge cases** before reporting (per `docs/cursor_ruleset.md` §2).

### 1.3 Severity levels

| Level | Meaning | Example |
|-------|---------|---------|
| **Critical** | Exploitable or data loss in prod | IDOR on bookings, webhook without signature check |
| **High** | Security weakness or broken core flow | JWT in localStorage + XSS vector; ticket double-spend |
| **Medium** | Correctness, perf, or maintainability | N+1 in list endpoints; logic duplicated in view; unclear naming; missing tests for core rule |
| **Low** | Polish, docs, optional hardening | Missing index; no lazy routes; verbose file could be split |

### 1.4 Report template

Deliver findings in this format:

```markdown
## Audit summary
- **Scope:** …
- **Date:** …
- **Tooling run:** …
- **Counts:** Critical N | High N | Medium N | Low N

## Findings

### [SEVERITY] Short title
- **Location:** `path/to/file.py` (lines or symbol)
- **Risk:** …
- **Recommendation:** …
- **Fix before prod?** Yes / No

## Passed checks
- …

## Maintainability & readability notes
- **Strengths:** …
- **Tech debt / clarity gaps:** …

## Recommended next steps (prioritized)
1. …
```

### 1.5 “Pass” criteria before major feature work

Minimum bar (adjust if scope is narrower):

- No **Critical** findings open.
- **High** findings documented with owner/decision.
- Core flows manually verified or covered by tests.
- Prod deploy checklist (§6) reviewed if deploying.

---

## 2. Frontend audit (React / JavaScript)

### 2.1 Code quality & conventions

- **Hooks:** Audit `useEffect`, `useCallback`, `useMemo` for missing dependencies, stale closures, infinite loops. (`eslint-plugin-react-hooks` is **not yet configured** — review manually.)
- **State:** Local state for UI; Context for shared data (`useGlossary`, `useBranding`, `useTeacherScope`). Flag unnecessary global state or deeply nested state.
- **Architecture:** Pages thin; heavy logic in hooks (`frontend/src/hooks/`). Components presentational where possible.
- **API layer:** All HTTP via `frontend/src/api.js` — no scattered `fetch` with duplicated auth/error handling.
- **Business logic:** React must **not** implement booking rules, ticket math, or permission logic beyond UX guards — server is authoritative.

### 2.2 Security

- **`npm audit`** — run and triage (record severity).
- **XSS:** No `dangerouslySetInnerHTML` without sanitization. User content (blog body, homework) rendered safely.
- **Secrets:** No API keys in frontend; only `VITE_*` public vars if any.
- **JWT storage:** Tokens in `localStorage` (`api.js`) — flag XSS → token theft risk; note mitigations (CSP, short access token, httpOnly cookie alternative).
- **Auth headers:** Token refresh on 401 — verify no race leaks tokens to wrong requests.

### 2.3 Performance

- **Code splitting:** Route-level `React.lazy()` for large pages (optional improvement).
- **Bundle:** Check for heavy imports (e.g. full chart libraries on every page).
- **Re-renders:** Expensive filters (session lists, calendars) — memoization where measured problems exist.

### 2.4 Maintainability & readability

Auditors should explicitly review whether the frontend is easy for a future developer (or future you) to change safely.

**Naming & consistency**

- Component and page files match their export (`StudentSessionsPage.jsx` → default export name).
- Hooks prefixed with `use`; API helpers live in `api.js` with clear names (`apiFetch`, `apiUpload`).
- Prop and state names describe domain concepts (`ticketsRemaining`, not `tr`).
- UI labels use glossary hooks where studio terminology is customizable — avoid hardcoded role jargon in many places when `useGlossary()` exists.

**Structure & size**

- Pages stay thin; multi-step flows split into components (e.g. calendar panels, thread views).
- Flag pages or components **> ~250 lines** — candidate for extraction unless cohesive.
- Repeated form patterns (field + label + error) — note if a shared primitive would reduce drift.

**DRY (within reason)**

- Duplicated `fetch`/auth/error handling must not spread beyond `api.js`.
- Duplicated date formatting, session labels, or filter logic — candidate for small shared helpers (not premature abstraction).
- Copy-pasted JSX blocks across pages — note for consolidation.

**Readability**

- `useEffect` blocks: clear dependency arrays; comment only when the *why* is non-obvious (e.g. intentional empty deps).
- Avoid deep nesting in JSX — early returns and subcomponents improve scanability.
- User-facing error/success messages: complete sentences, consistent tone (`error` / `success` classes).

**Dead code & drift**

- Unused imports, unreachable routes, commented-out blocks — flag for removal.
- Legacy UI paths still imported but unused — note.
- Frontend behavior documented in `CLAUDE.md` or handoff docs should match actual routes in `App.jsx`.

**Tests as maintainability signal**

- No frontend test runner yet — record as gap. Critical client paths (login, book, upload) rely on manual smoke (§9) until tests exist.

---

## 3. Backend audit (Django / Python)

### 3.1 Code quality & conventions

- **Ruff** (recommended; not yet in `requirements.txt`): `ruff check .` and `ruff format --check .`
- **Services layer:** Every write path in DRF/HTML views delegates to `services/`. Flag inline business logic in views/serializers.
- **ORM:** Models match migrations; no drift. Prefer ORM over raw SQL.
- **Imports & structure:** Consistent patterns across `scheduling/api/` and `progress/api.py`.

### 3.2 Security (SAST & config)

Run when possible:

```bash
pip install bandit pip-audit   # one-off if not in requirements
bandit -r scheduling progress integrations config -ll
pip-audit
```

- **Django production settings:** `DEBUG=False`, `SECRET_KEY` from env, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`.
- **Security headers:** `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, HSTS when deployed.
- **Admin exposure:** `/admin/` access model understood.
- **No secrets in repo:** `.env` gitignored; `.env.example` has placeholders only.

### 3.3 Performance & database

- **N+1 queries:** List views and serializers use `.select_related()` / `.prefetch_related()` for FKs and M2M.
- **Profiling (local):** Django Debug Toolbar or Silk on hot endpoints (`sessions/open/`, staff schedule, progress dashboard).
- **Indexing:** Fields used in `filter()`, `order_by()`, and foreign keys — `db_index=True` or composite indexes where needed.

### 3.4 Maintainability & readability

Auditors should explicitly review whether backend code is easy to extend (new endpoints, new rules) without breaking existing flows.

**Naming & conventions**

- Services: verb-led functions (`create_booking`, `can_book`, `approve_class_request`) in the correct module (`booking.py`, not scattered).
- Models: singular PascalCase; fields match domain language used in API serializers and frontend.
- DRF views: `*ListView`, `*DetailView`, or clear `APIView` names; staff variants in `staff_views.py`.
- Permission keys in `TEACHER_PERMISSION_DEFS` match usage in `teacher_can()` checks.

**Structure & size**

- Business logic in `services/` — views/serializers orchestrate only (validate → call service → serialize).
- Flag service functions or views **> ~80 lines** — consider splitting by responsibility.
- Flag serializers with heavy `create`/`update` overrides that duplicate service rules.

**DRY (within reason)**

- Duplicated queryset filtering (teacher scoping, active user checks) — candidate for shared helpers.
- HTML views and DRF endpoints doing the same thing must call the **same** service function.
- Repeated serializer fields across list/detail — note `SerializerMethodField` duplication vs a shared mixin.

**Readability**

- Comments explain *why* (business rules, edge cases), not *what* the next line does.
- Docstrings on non-obvious service entry points (ticket hold/refund, class request approval).
- Exceptions and API `detail` messages: clear for clients, no internal stack leakage in prod.

**Legacy & consistency**

- `ClassType` vs `ClassOffering` — note remaining legacy paths; prefer catalog model in new code.
- Integration scaffolds (`integrations/google/meet.py`) clearly marked TODO vs production behavior.
- `TICKETS.md`, `CLAUDE.md`, and `docs/architecture-and-roadmap.md` should not contradict implemented behavior — flag drift.

**Dead code & hygiene**

- Unused imports, unreachable URL routes, admin registrations for deprecated models.
- Migrations: no orphaned models; naming follows app sequence.

**Tests as maintainability signal**

- Core flows should have service- or API-level tests (`scheduling/tests.py`, progress tests if present).
- Missing tests for ticket rules, IDOR, or payment webhooks — **Medium** maintainability/risk finding.
- Test names describe behavior (`test_cancel_approved_request_booking_does_not_refund`), not implementation.

---

## 4. DRF, API & authorization

### 4.1 Authentication

- JWT obtain/refresh endpoints (`simplejwt`) configured safely.
- Token lifetime and rotation policy documented in settings.
- Session auth for browsable API / HTML — no accidental open write endpoints.

### 4.2 Permission classes

Verify each endpoint uses correct permission:

| Class | Intended use |
|-------|----------------|
| `IsStudent` | Student-only routes |
| `IsTeacher` | Teacher self-service |
| `IsStaff` | Studio admin |
| `IsTeacherOrStaff` | Shared teacher/staff routes |
| `IsAuthenticated` | Read-only shared resources |

### 4.3 Object-level authorization (IDOR)

Manually or via tests, confirm users **cannot**:

- Cancel or view another user’s booking.
- Edit another teacher’s session/class/availability.
- Access another student’s homework, progress, or files.
- Approve/deny class requests for another teacher’s queue (unless staff scoped correctly).
- Download homework attachments without thread participation.
- PATCH staff routes to act on arbitrary `teacher_id` without staff group.

**Rule:** Queryset filtering and service checks must use `request.user`, not client-supplied IDs alone.

### 4.4 Serializers & validation

- Write serializers validate FK ownership (e.g. class topic belongs to offering).
- Mass-assignment: no writable fields that bypass business rules (e.g. `tickets_remaining` on Membership via API).
- Error responses do not leak stack traces or secrets in production.

### 4.5 Dual UI parity

For each critical operation, confirm **HTML view** and **DRF endpoint** call the **same service** with equivalent rules:

- Book / cancel session
- Membership purchase
- Teacher permission gates
- Homework create/reply

---

## 5. Domain-specific business rules

Verify implementation matches intended behavior in services + tests.

### 5.1 Booking & tickets

- `can_book` / `create_booking` / `cancel_booking` in `scheduling/services/booking.py`.
- Ticket spend/refund via `scheduling/services/tickets.py`.
- Membership class restrictions (`membership_for_booking`).
- Cancelled session when last booking removed (unless other students remain — class-request flow).

### 5.2 Class requests

- `scheduling/services/class_requests.py`: hold tickets on request, spend on approve, refund on deny/delete.
- Approved booking cancel: **no ticket refund** (`Booking.class_request` link).
- Slot overlap and availability validation.

### 5.3 Teacher permissions

- `teacher_can(user, key)` enforced on gated API writes.
- Staff bypass documented and intentional.

### 5.4 Homework & files

- `progress/homework_services.py` + `scheduling/services/uploads.py`: size/extension limits.
- Download authorization on `/api/progress/homework/entries/<id>/download/`.
- Purge command: `python manage.py purge_expired_homework` — document cron need for prod.

### 5.5 Membership & payments

- Mock path when Stripe disabled; checkout when enabled.
- `integrations/stripe/webhooks.py`: signature verification.
- Idempotent fulfillment (duplicate webhook events).
- Payment records align with membership state.

### 5.6 Studio configuration

- `StudioGlossary`, `StudioBranding`, `StudioLLMConfig` — staff-only writes.
- Public branding endpoint (`GET /api/branding/`) exposes only safe fields.

### 5.7 Integrations graceful degradation

- Google / Zoom / Stripe / LLM: no uncaught exceptions when keys missing.
- Placeholder Meet links acceptable; document as known limitation until OAuth built.

---

## 6. Uploads, media & deploy

### 6.1 File uploads

- Homework, blog images, branding logos — validated size/type.
- Upload paths not user-controlled for directory traversal.
- `DATA_UPLOAD_MAX_MEMORY_SIZE` / `FILE_UPLOAD_MAX_MEMORY_SIZE` aligned with app limits.

### 6.2 Production media

- **WhiteNoise serves static only** — homework and logos need volume mount or S3/R2 + signed URLs in prod.
- `MEDIA_URL` not accidentally public beyond authenticated download routes where required.

### 6.3 Deploy checklist

- [ ] `DEBUG=False`, strong `SECRET_KEY`
- [ ] Postgres backups configured
- [ ] Media storage plan
- [ ] SMTP or transactional email provider
- [ ] Stripe webhook URL + secret in prod
- [ ] CORS limited to frontend origin(s)
- [ ] Homework purge scheduled
- [ ] `python manage.py check --deploy` passes

---

## 7. Tooling — what to run today

### Currently available

```bash
# Backend tests
source .venv/bin/activate
python manage.py test

# Django deploy check
python manage.py check --deploy

# Frontend build (catches import/syntax errors)
cd frontend && npm run build

# Dependency audits (install tools ad hoc)
pip install pip-audit bandit ruff
pip-audit
bandit -r scheduling progress integrations -ll
ruff check .

npm audit --prefix frontend
```

### Not yet configured (note as gaps; optional recommendations)

| Tool | Status |
|------|--------|
| ESLint + react-hooks | Not in `frontend/package.json` |
| Vitest / Jest | No frontend tests |
| pytest | Uses Django `TestCase` instead |
| Ruff in requirements / pre-commit | Documented in learning notes only |
| GitHub Actions CI | No `.github/workflows` |
| husky / pre-commit hooks | Not present |

Auditors should **record which commands were run** and treat missing tooling as **Low** findings unless blocking security.

---

## 8. Automation roadmap (future CI/CD)

When ready, pipeline should run:

1. `ruff check .` + `ruff format --check .`
2. ESLint on `frontend/src` (after added)
3. `pip-audit` + `npm audit` (allowlist documented)
4. `python manage.py test`
5. `cd frontend && npm run build`
6. Optional: `bandit` on backend

Pre-commit via `pre-commit` or husky recommended before team scale.

---

## 9. Manual smoke scenarios

Execute or trace these flows during a full audit:

| # | Actor | Flow |
|---|--------|------|
| 1 | Student | Login → browse open sessions → book → see booking → cancel |
| 2 | Student | Request class during availability → cancel pending request (tickets return) |
| 3 | Teacher | Approve class request → student booking live → student cancel (no refund) |
| 4 | Student | Membership mock purchase; with Stripe keys: checkout + webhook |
| 5 | Teacher | Create session outside availability (should fail) |
| 6 | Teacher | Homework file upload at size limit boundary |
| 7 | Staff | Deactivate student → student cannot book |
| 8 | Staff | Revoke teacher permission → gated action returns 403 |
| 9 | Wrong user | Attempt IDOR on booking/homework/session IDs (must 404/403) |
| 10 | Anonymous | `GET /api/branding/` works; protected routes 401 |

---

## 10. Quick reference

| Doc | Purpose |
|-----|---------|
| `CLAUDE.md` | Stack, commands, API map, architecture rules |
| `docs/cursor_ruleset.md` | When to audit; approval before complex fixes |
| `docs/next-session-handoff.md` | Planned Stripe, Google, onboarding, themes |
| `TICKETS.md` | Known bugs |
| `docs/architecture-and-roadmap.md` | Deep architecture history |
| `docs/learn/` | CS50P / Django self-study materials |

**Demo users:** `demo_student`, `demo_teacher`, `demo_staff` / `demo1234` (after `bootstrap_sandbox --demo`).
