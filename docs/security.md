# Security notes

**Last updated:** 2026-07-06 (audit remediation Phase 5)

Current posture, known trade-offs, and the plan for tightening them. Companion to
`docs/audit-remediation-plan.md`.

---

## Auth model

| Surface | Auth | Notes |
|---------|------|-------|
| React SPA (`:5173`) | JWT (simplejwt) | Access 60 min, refresh 7 days dev / 1 day prod (env-tunable via `JWT_ACCESS_MINUTES`, `JWT_REFRESH_DAYS`) |
| Django templates (`:8000`) | Session cookie | Legacy UI; `SESSION_COOKIE_SECURE` in prod |
| Deactivated users | Blocked at **two layers** | simplejwt `CHECK_USER_IS_ACTIVE` + `IsActiveUser` permission (Phase 2) |

---

## Known trade-off: JWT in localStorage

`frontend/src/api.js` stores access + refresh tokens in `localStorage`.

**Risk:** any XSS that executes in the SPA can read both tokens and act as the user
until expiry. This is the main reason XSS protections below matter.

**Current mitigations**

- All user content renders as **plain text** in React (no `dangerouslySetInnerHTML`
  anywhere — verified this phase).
- Short token lifetimes in production (refresh 1 day by default).
- CSP on all Django-served pages when `DEBUG=False`.
- Tokens never appear in URLs or logs; sent only via `Authorization` header.

**Planned (deferred — large refactor)**

Move to httpOnly cookie auth (or a BFF pattern):

1. Backend issues `httpOnly` + `Secure` + `SameSite` cookies instead of JSON tokens.
2. CSRF protection on state-changing requests (double-submit or Django CSRF).
3. Remove `localStorage` usage from `api.js`; rely on `credentials: 'include'`.
4. CORS: switch from bearer-token model to cookie model (`Access-Control-Allow-Credentials`).

Tracked in `docs/audit-remediation-plan.md` → Explicit deferrals.

---

## Content-Security-Policy

`config/middleware.py::ContentSecurityPolicyMiddleware` adds a CSP header to every
Django response when `DEBUG=False` (skipped in DEBUG — Vite and Django debug pages
need inline scripts).

Default policy (override with `CSP_POLICY` env var):

```text
default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';
img-src 'self' data: blob:; font-src 'self'; connect-src 'self';
frame-ancestors 'none'; base-uri 'self'; form-action 'self'
```

- `style-src 'unsafe-inline'` is required by Django admin + DRF browsable API.
- `frame-ancestors 'none'` also acts as clickjacking protection.
- **The React SPA is served separately** (Vite dev / static host). When you deploy it,
  set an equivalent CSP at that layer (nginx header, hosting platform config, or meta
  tag) — Django's header does not cover a separately-hosted frontend.

---

## XSS rules for user content

Blog posts, journal entries, homework messages, and session notes are stored as plain
text and rendered as text nodes in React.

- **Never** introduce `dangerouslySetInnerHTML` on user content without a sanitizer.
- The planned Markdown feature (Phase 22) must render through one shared
  markdown → bleach pipeline; preview and final display use the same rules.

---

## Other protections in place

| Protection | Where |
|------------|-------|
| Mock payments blocked in prod | `purchase_membership()` + `ALLOW_MOCK_PAYMENTS` (Phase 3) |
| Homework media private, API-only | `HomeworkAttachmentDownloadView` + docs (Phase 4) |
| HTTPS redirect, HSTS, secure cookies | `config/settings.py` prod block |
| Upload validation (size + extension) | `scheduling/services/uploads.py` |
| Stripe webhook signature check | `integrations/stripe/webhooks.py` |
| Auth rate limits | `LoginRateThrottle` 10/min, `TokenRefreshRateThrottle` 30/min (Phase 6) |

| IDOR/permission test suite | `IdorPermissionTests` in `scheduling/tests.py` (Phase 8) |

## Pending (later phases)

| Item | Phase |
|------|-------|
| LLM key redaction + URL allowlist | 11 |
