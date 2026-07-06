# Next session handoff (personal account)

**Created:** 2026-07-03  
**Updated:** 2026-07-05 — **master plan moved to `docs/audit-remediation-plan.md`**

Use **`docs/audit-remediation-plan.md`** for tomorrow’s full schedule:

- **Part A (Phases 0–15):** audit remediation  
- **Part B (Phases 16–21):** session history privacy, Stripe, themes, onboarding, Google  
- **Part C (Phase 22):** Markdown preview for blog + journal

This file remains a quick reference for Part B tasks. Paste the prompt below only if you want the original handoff wording; prefer the master prompt in the remediation plan.

---

## Repo state (what’s already built)

| Area | Status |
|------|--------|
| **Stripe Checkout + webhook** | Implemented — `integrations/stripe/`, `POST /api/membership/checkout/`, webhook at `/api/payments/stripe/webhook/`. Mock mode when keys unset. |
| **Google Meet** | Scaffold only — `integrations/google/meet.py` returns placeholder URLs. Needs OAuth + Calendar API. |
| **Sign-in branding** | Staff can set name + logo (`/staff/branding`, `StudioBranding`, `GET /api/branding/`). |
| **Blog, class requests, homework, reports** | In place from prior sessions. |
| **Themes** | Not built — single light blue palette in `frontend/src/index.css` (`:root` CSS variables). |
| **Onboarding** | Not built — home page has role-specific intro cards only; no first-run wizard or checklist. |

**Start servers:**

```bash
cd ~/repos/booking_scheduling_app
source .venv/bin/activate
python manage.py migrate
python manage.py bootstrap_sandbox --demo   # demo_staff / demo_teacher / demo_student · demo1234
python manage.py runserver                  # :8000

cd frontend && npm run dev                  # :5173
```

---

## Task 1 — Stripe (personal testing)

**Goal:** Pay for a membership with a real test card on your machine.

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
   Put the printed `whsec_...` in `.env` as `STRIPE_WEBHOOK_SECRET`.
4. Restart Django after `.env` changes.

### Test

1. React → log in as `demo_student` / `demo1234`.
2. **Membership** → **Pay with Stripe** (should appear when keys are set).
3. Card: `4242 4242 4242 4242`, any future expiry, any CVC.
4. Confirm webhook fires and membership becomes active (`GET /api/membership/`).

### Key files

- `integrations/stripe/checkout.py`, `webhooks.py`, `client.py`
- `scheduling/services/payments.py` — `fulfill_payment`, `create_checkout_session`
- `frontend/src/pages/MembershipPage.jsx`
- `scheduling/tests.py` — `StripePaymentTests`

### If something breaks

- 400 on checkout → check plan exists (`Staff → Memberships` or bootstrap).
- Webhook 400 → `STRIPE_WEBHOOK_SECRET` mismatch; restart `stripe listen`.
- Still mock mode → `STRIPE_SECRET_KEY` empty or server not restarted.

---

## Task 2 — Google integration (real Meet links)

**Goal:** When a teacher creates a session, store a real Google Meet URL (not placeholder).

### What exists

- `config/settings.py` — `GOOGLE.CLIENT_ID`, `GOOGLE.CLIENT_SECRET`, `ENABLED`
- `integrations/google/meet.py` — TODO for Calendar API
- `scheduling/services/meetings.py` — calls `create_meet_link(session)` on session create
- Session model: `meeting_provider`, `meeting_url`

### What to build (suggested order)

1. **Google Cloud project**
   - Enable **Google Calendar API**.
   - OAuth consent screen (External / Testing is fine for personal use).
   - OAuth client: Web application.
   - Redirect URI: `http://127.0.0.1:8000/integrations/google/callback/` (adjust to your route).
   - Add to `.env`: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`.

2. **OAuth flow (teacher connects Google)**
   - Model: `GoogleCredential` (or fields on `Profile`): `user`, `refresh_token`, `access_token`, `expires_at`.
   - Routes: `GET /api/integrations/google/connect/`, callback view exchanges code for tokens.
   - UI: **Profile** or **Teacher settings** — “Connect Google Calendar”.

3. **Create Meet link on session create**
   - In `integrations/google/meet.py`: use teacher’s stored token → Calendar `events.insert` with `conferenceData` → read `hangoutLink` or `entryPoints`.
   - Degrade gracefully if teacher hasn’t connected Google (keep placeholder or empty + UI hint).

4. **Optional later:** attach `.ics` with real Meet link; sync cancellations to Calendar.

### Key files to touch

- `integrations/google/meet.py` (main implementation)
- New: `integrations/google/oauth.py`, `scheduling/api/google_views.py`, `scheduling/api/urls.py`
- `scheduling/models.py` — token storage
- `frontend/src/pages/ProfilePage.jsx` or teacher settings page

### Personal test checklist

- [ ] Teacher connects Google once
- [ ] Create session with `meeting_provider: google_meet`
- [ ] `meeting_url` is a real `meet.google.com/...` link
- [ ] Student booking shows working link

---

## Task 3 — Initial onboarding

**Goal:** First-time users see a short guided setup instead of a generic home card.

### Suggested scope (MVP)

Track completion per user (DB or `Profile` flags), show a **onboarding checklist** until done or dismissed.

| Role | Steps (examples) |
|------|------------------|
| **Student** | Set display name → view membership / buy tickets → book or request a class → open progress |
| **Teacher** | Set availability → add a class → create first session (or review class requests) |
| **Staff** | Set branding → create membership plan → invite/add a teacher → skim dashboard |

### Implementation sketch

1. **Backend**
   - `Profile.onboarding_completed_at` or JSON `onboarding_state` `{ "dismissed": false, "steps": {...} }`.
   - `GET/PATCH /api/me/onboarding/` — return checklist + mark steps complete.
   - Optionally auto-complete steps when actions happen (first booking, first availability block, etc.) in existing services.

2. **Frontend**
   - `OnboardingChecklist.jsx` on home page (or modal on first login).
   - `useOnboarding()` hook; hide when complete/dismissed.
   - Deep links to relevant pages (`/sessions`, `/teacher/availability`, `/staff/branding`, etc.).

3. **Don’t duplicate business logic** — checklist reads state from API; services mark progress.

### Key files

- `scheduling/models.py` — `Profile`
- `scheduling/api/views.py` — `MeView` or new onboarding view
- `frontend/src/App.jsx` — `HomePage`
- `frontend/src/pages/StudentHomeDashboard.jsx` — extend for students

---

## Task 4 — User theme preferences

**Goal:** Each user can switch appearance (e.g. light / dark / high contrast); persists across sessions.

### Suggested approach

1. **CSS**
   - Refactor `frontend/src/index.css`: keep tokens in `:root` (light default).
   - Add `[data-theme="dark"]` (and optional `"contrast"`) overrides for `--bg`, `--surface`, `--ink`, `--blue-*`, etc.
   - Avoid duplicating component rules — only override variables.

2. **Storage**
   - `Profile.theme` — `CharField` choices: `light`, `dark`, `system` (default `system`).
   - Include in `serialize_me` / `PATCH /api/me/`.
   - Apply on load: read `getMe()` → `document.documentElement.dataset.theme = ...`
   - For `system`: `matchMedia('(prefers-color-scheme: dark)')`.

3. **UI**
   - **Profile & settings** — theme selector (radio or select).
   - Optional: quick toggle in sidebar footer.
   - Sign-in page: respect `system` only (no user yet) or last-used `localStorage` preview.

4. **Tests**
   - API: PATCH theme persists.
   - Manual: sidebar, cards, calendar, auth screen readable in dark mode.

### Key files

- `frontend/src/index.css`
- `scheduling/models.py` — `Profile.theme`
- `scheduling/api/serializers.py` — `serialize_me`, `MeUpdateSerializer`
- `frontend/src/pages/ProfilePage.jsx`
- New: `frontend/src/hooks/useTheme.js` — apply + listen for system changes

---

## Suggested work order (tomorrow)

**See `docs/audit-remediation-plan.md` — Part B order:**

1. **Phase 16** — Cross-teacher session history privacy (~3–4 hr)
2. **Phase 17** — Stripe env + CLI + test purchase (~30 min)
3. **Phase 18** — Themes (~2–3 hr)
4. **Phase 19** — Onboarding checklist (~3–4 hr)
5. **Phase 20** — Google OAuth + Calendar (~4–8 hr)
6. **Phase 22** — Markdown preview for blog + journal (~2–3 hr)

Complete **Part A Phases 0–8** (audit fixes) before starting Part B unless you consciously defer.

---

## Cursor prompt (copy-paste tomorrow)

**Prefer the master prompt in `docs/audit-remediation-plan.md`.** Or:

```
Read docs/audit-remediation-plan.md and docs/cursor_ruleset.md first.

Continue from the next unchecked phase in the progress table (Part A or Part B).

Part B includes: session history privacy (16), Stripe (17), themes (18), onboarding (19), Google Meet (20). Part C: Markdown preview (22).

Follow repo rules: business logic in services/, minimal scope, propose before apply. Run migrate and tests when done. Don't commit unless I ask.
```

---

## Management / SaaS note (optional context)

If you pitch or productize later: multi-tenant `Organization` model, production media (S3), and Stripe Billing for *your* subscription are still future work. This session focuses on **personal integration testing** and **UX polish** (onboarding + themes).

---

## Quick reference

| Doc | Purpose |
|-----|---------|
| **`docs/audit-remediation-plan.md`** | **Master plan** — audit + features (Phases 0–22) |
| `README.md` | Quickstart + Stripe testing |
| `CLAUDE.md` | Agent/repo conventions |
| `docs/architecture-and-roadmap.md` | Full architecture |
| `TICKETS.md` | Bug tracker |

Demo users after `bootstrap_sandbox --demo`: `demo_staff`, `demo_teacher`, `demo_student` / `demo1234`
