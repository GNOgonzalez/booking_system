# Audit remediation log

Resolved items from `docs/audit-remediation-plan.md` (Part A).

| Date | Phase | Item |
|------|-------|------|
| 2026-07-05 | 1 | Fixed missing `update_session` / `cancel_session` imports |
| 2026-07-05 | 2 | `IsActiveUser` + JWT `CHECK_USER_IS_ACTIVE` |
| 2026-07-05 | 3 | Mock payments blocked when `DEBUG=False` |
| 2026-07-05 | 4 | Homework download auth tests; media privacy docs |
| 2026-07-05 | 5 | CSP middleware, shorter JWT refresh in prod, `docs/security.md` |
| 2026-07-05 | 6 | Login/token refresh rate limits |
| 2026-07-05 | 7 | N+1 fix for session `confirmed_count` |
| 2026-07-05 | 8 | IDOR & permission regression tests |
| 2026-07-06 | 9 | GitHub Actions CI (tests, ruff, frontend build, npm audit) |
| 2026-07-06 | 10 | Ruff config + lint fixes |
| 2026-07-06 | 11 | LLM key masking + outbound URL allowlist |
| 2026-07-06 | 12 | React.lazy route splitting |
| 2026-07-06 | 13 | `progress/api/` package split |
| 2026-07-06 | 15 | Part A final verification (75 tests, ruff clean, frontend build) |
| 2026-07-06 | 16 | Cross-teacher session history + privacy API, services, student toggle |
| 2026-07-06 | 17 | Stripe webhook test + E2E setup documented (manual: stripe listen) |
| 2026-07-06 | 18 | Profile theme (light/dark/system) + CSS variables |
| 2026-07-06 | 19 | Onboarding checklist API + home UI |
| 2026-07-06 | 21 | Part B verify — 79 tests, build OK (Phase 20/22 deferred to Fable) |
| 2026-07-06 | 16 (UI) | Teacher peer-history panel + own-session hide toggle; staff hidden badges |
| 2026-07-06 | 20 | Google OAuth (`GoogleCredential`, connect/callback/status/disconnect) + real Meet links via Calendar API |
| 2026-07-06 | 22 | `render_safe_markdown` (markdown + bleach), preview API, blog + journal preview UI |

## Phase 20 notes

- Signed OAuth `state` (TimestampSigner, 10-min expiry) identifies the user at the
  browser callback — no JWT needed there.
- Refresh tokens are kept across reconnects (Google only sends them on first consent).
- `create_meet_link` degrades to the deterministic placeholder if the teacher has
  not connected Google, the token refresh fails, or the Calendar call errors.
- Setup: Google Cloud → Calendar API + OAuth web client; redirect URI
  `http://127.0.0.1:8000/integrations/google/callback/`; set `GOOGLE_CLIENT_ID` /
  `GOOGLE_CLIENT_SECRET` in `.env`. Teachers connect from **Profile & settings**.

## Phase 22 notes

- One pipeline: `scheduling/services/markdown.py` — Markdown (`fenced_code`, `nl2br`)
  → bleach allowlist (p/br/strong/em/a/lists/blockquote/code/pre/h1–h3/hr) →
  `linkify` with `nofollow` + `target_blank`.
- Storage unchanged — Markdown source stays in the existing TextFields.
- `POST /api/markdown/preview/` renders previews server-side so preview = publish.
- Rendered on: blog feed (`body_html`), homework/journal entries (`body_html`).

## Legacy notes (Phase 14)

- **Primary UI:** React SPA at `:5173` (JWT). Django HTML templates at `:8000` remain for bootstrap/demo but are not the product target.
- **`ClassType`:** Legacy model; use **`ClassOffering`** for all new work.
- **Staff homework POST:** `/api/progress/staff/teachers/<id>/homework/` intentionally bypasses the teacher `assign_homework` permission — staff may assign on behalf of any teacher.
