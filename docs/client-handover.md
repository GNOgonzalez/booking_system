# Client handover — booking & scheduling platform

**Audience:** You (the builder) and a studio owner who wants this kind of platform built or handed off.  
**Last updated:** 2026-07-28

Use this when someone asks you to **create, customize, deploy, or take over** a studio booking platform based on this codebase.

Related technical docs:

| Doc | Use for |
|-----|---------|
| [`operations-guide.md`](./operations-guide.md) | Day-to-day deploy and run |
| [`portfolio-demo-deploy.md`](./portfolio-demo-deploy.md) | Public demo on Render (free tier) |
| [`architecture-and-roadmap.md`](./architecture-and-roadmap.md) | How the system is structured |
| [`security.md`](./security.md) | Auth, CSP, production hardening |
| [`.env.example`](../.env.example) | Environment variable template |

---

## 1. What you are delivering

A **single-studio** web app:

| Piece | Technology |
|-------|------------|
| Student / teacher / staff UI | React SPA |
| API + business rules | Django 5.2 + DRF + JWT |
| Database | PostgreSQL 16 |
| Optional | Stripe payments, email, Google Meet/Calendar |

**One deployment = one studio** (separate database and config per customer). This is not multi-tenant SaaS unless you scope and build that separately.

### Roles

| Role | Typical use |
|------|-------------|
| **Student** | Book sessions, membership, homework, progress |
| **Teacher** | Schedule, availability, feedback, homework (permissions vary) |
| **Staff** | Users, plans, branding, glossary, reports |
| **Django superuser** | Break-glass `/admin/` only — not for daily studio work |

---

## 2. Before you start — discovery questions

Collect answers **in writing** (email or shared doc) before quoting or building.

### Business

- Studio name, logo, colors, timezone, default language?
- How do students pay today (membership, packs, per session)?
- Which class types / subjects / levels need to appear on day one?
- Who is staff vs teacher on launch day (names, emails)?
- Do they need real payments at launch, or mock/demo first?
- Do they need Google Meet links, or is a placeholder OK initially?

### Technical

- Custom domain(s)? e.g. `app.theirstudio.com`
- Who owns hosting accounts (you vs client)?
- Who pays monthly hosting (Render, email, Stripe fees)?
- Any compliance needs (FERPA, GDPR, data retention for homework files)?
- Expected number of teachers and students in year one?

### Scope boundaries (clarify early)

| Usually in scope | Usually extra scope |
|------------------|---------------------|
| Deploy one studio instance | Multi-tenant SaaS (many studios, one install) |
| Branding (name + logo) | Full custom design system |
| Demo or production seed data | Migration from Mindbody, Calendly, etc. |
| Stripe test → live switch | Custom mobile apps |
| Staff training walkthrough | 24/7 support retainer |
| Handover doc + credential transfer | Ongoing feature development without a new SOW |

---

## 3. What the client must provide

### Required for any launch

| Item | Why |
|------|-----|
| **Domain** (or subdomain) | Public URL for the app |
| **Hosting billing** | Card on Render, Railway, Fly.io, etc. |
| **PostgreSQL** | Managed DB (Render Postgres, Supabase, RDS, …) |
| **At least one staff contact email** | Account invites, password resets |
| **Decision-maker** | Approves branding, plans, go-live date |

### Required for production (not demo)

| Item | Why |
|------|-----|
| **Strong `SECRET_KEY`** | Django crypto; never reuse demo keys |
| **Private superuser** | Not `demo_staff` / `demo1234` |
| **`DEBUG=False`** | Security baseline |
| **HTTPS** | Enforced in production settings |
| **CORS + `VITE_API_BASE`** | React must call the correct API origin |
| **Persistent media storage** | Homework uploads need a disk or object store |
| **SMTP or transactional email** | Booking confirmations (console-only is dev-only) |

### Optional integrations (client or you creates accounts)

| Service | Client provides |
|---------|-----------------|
| **Stripe** | Business verification, live API keys, webhook endpoint |
| **Google Cloud** | OAuth client for Calendar/Meet (consent screen, redirect URIs) |
| **Email** | SendGrid, Postmark, Gmail app password, or studio SMTP |

---

## 4. Getting a domain (for clients who are not technical)

Most studio owners have never bought a domain or heard of DNS. Your job is to **get them an account they own**, pick a sensible web address, and **you** wire it to the app later. They should not need to understand deployment.

### Plain English — what you are asking them to buy

| Term | What it means to them |
|------|------------------------|
| **Domain** | The web address people type, e.g. `sunrise-piano.com` |
| **Registrar** | The company they pay yearly to rent that name (~$12–20/year) |
| **Hosting** | Where the app actually runs (Render, etc.) — **separate** from the domain |
| **DNS** | Settings that connect the domain to hosting — **you configure this** |

**Rule:** The **client** creates the registrar account and pays with **their** card. You can be added as a helper, but **they must be the account owner** so they are not locked in if you stop working together.

### Pick the address before they buy

Discuss on a call:

| Option | Example | When to use |
|--------|---------|-------------|
| **Subdomain for the app** | `app.sunrisepiano.com` | They already have a website at `sunrisepiano.com` (Wix, Squarespace, WordPress) |
| **Subdomain** | `book.sunrisepiano.com` | Same — keeps marketing site separate |
| **Root domain for the app** | `sunrisepiano.com` | No existing site, or they are OK replacing the homepage with the app |
| **New name** | `sunrise-piano-studio.com` | Their preferred `.com` is taken |

For this stack, **`app.theirdomain.com`** is a good default: students bookmark one clear URL; their brochure site can stay where it is.

They only need **one** domain purchase. You do not need them to buy separate domains for “API” and “app” on day one — you can use a single app URL and keep the API on a hosting URL behind the scenes.

### Recommended registrars (simple for non-technical clients)

Any of these is fine. Pick one you are comfortable with:

| Registrar | Why |
|-----------|-----|
| [Namecheap](https://www.namecheap.com) | Cheap, straightforward checkout |
| [Cloudflare Registrar](https://www.cloudflare.com/products/registrar/) | At-cost pricing; great DNS later |
| [Porkbun](https://porkbun.com) | Simple UI, fair pricing |
| [Google Squarespace Domains](https://domains.squarespace.com) | Familiar brand if they already use Squarespace |

Avoid: buying the domain **inside** Wix/Squarespace **website** bundles if they might leave that platform later — a standalone registrar is easier to hand off.

### Path A — Client creates the account (recommended)

**Send them this** (copy/paste email):

> **Subject: One-time setup — your studio web address**
>
> To put your booking platform on your own link (e.g. `app.yourstudio.com`), you’ll need to register your domain name. This takes about 15 minutes and costs roughly **$12–20 per year**.
>
> Please do the following:
>
> 1. Go to **[Namecheap.com](https://www.namecheap.com)** (or the registrar we discussed).
> 2. Click **Sign Up** and create an account with **your email** and a password you save in a password manager.
> 3. Use **your credit card** — the renewal should bill you directly each year.
> 4. Search for the domain name we agreed on (e.g. `sunrisepiano.com`).
> 5. Add it to cart and check out for **1 year** (skip extra upsells like email hosting or website builders unless you want them).
> 6. Reply to this email with: **“Domain is registered”** and the exact name you bought.
>
> You do **not** need to connect it to anything yourself. I’ll send a short call invite or ask for temporary access when it’s time to go live.
>
> Important: keep this login — it’s your property, like the keys to your studio.

**Your follow-up (screen share, 15 min):**

1. Confirm the domain shows in **their** dashboard.
2. Turn on **two-factor authentication** (2FA) on the registrar account — walk them through it.
3. If they already have email at `@theirdomain.com`, note it — changing DNS later can affect email; you may only add a subdomain record.
4. Do **not** change nameservers or DNS yet unless you are ready to connect hosting the same week.

### Path B — You sit with them on a call (same outcome)

If they will not do it alone:

1. Schedule a **video call**.
2. They share screen **or** you share screen with them dictating their email and card (they type card details — never yours).
3. They complete signup and checkout while you narrate.
4. They save the password; you do **not** store their registrar password long-term unless they explicitly want you on retainer.

### Path C — They already own a domain

Ask:

- “Where did you buy it?” (GoDaddy, Namecheap, Google, Wix, etc.)
- “Do you have the login?”

If they have a **website person**:

- Email that person: “Please add DNS record X when we go live” **or** ask for **temporary DNS access** / delegate a subdomain.

If login is lost:

- Recovery via registrar email is the only fix — budget time for that before promising a launch date.

### What you need from them to connect the app (later)

You do **not** need this on day one of the project. When hosting is ready:

| Approach | What the client does | What you do |
|----------|----------------------|-------------|
| **Temporary access** | Adds you as a team member on registrar/Cloudflare | Add CNAME records Render provides |
| **They paste records** | Copies 2–3 DNS lines you send into “Advanced DNS” | Verify with `dig` or Render dashboard |
| **Cloudflare in front** | Transfers DNS to Cloudflare (optional) | Manage SSL and caching |

**Client-facing instruction** when go-live is near:

> Log in to Namecheap → **Domain List** → **Manage** → **Advanced DNS**.  
> Add the records I sent in the email. Save. Changes can take up to an hour (usually much faster).

They do not need to understand CNAME vs A record — give them a **screenshot with arrows** or do it on a 10-minute call.

### If they have an existing website (very common)

```text
sunrisepiano.com          → existing Wix / brochure site (unchanged)
app.sunrisepiano.com      → your booking app (new DNS record only)
```

Their current site stays up. You only add one subdomain pointing to Render.

### Email on their domain (`hello@sunrisepiano.com`)

**Separate conversation.** Booking confirmations can use `no-reply@…` via SendGrid/Postmark without moving their whole email. If they use Google Workspace or Microsoft 365 for staff email, **do not** change MX records without their IT person. Use a subdomain for the app, or a transactional email provider.

### What to put in the contract

- Client **owns** domain and hosting accounts.
- You are granted **temporary** access to DNS/hosting for setup, revoked after handover unless on retainer.
- Annual domain renewal is **their** responsibility — remind them 30 days before expiry.
- If the domain expires, the app goes offline — not your bug.

### Checklist — domain ready for launch

- [ ] Domain registered in **client’s** name and email
- [ ] Client has login + 2FA saved
- [ ] Agreed URL documented (e.g. `https://app.sunrisepiano.com`)
- [ ] Existing website/email impact understood
- [ ] DNS records added (by you or their web person)
- [ ] HTTPS works in browser (padlock icon)
- [ ] Client can open the app URL without you on the call

---

## 5. Two delivery modes

### A. Portfolio / evaluation demo (low cost)

Purpose: “Try it” link on your portfolio or a sales call.

| Setting | Value |
|---------|--------|
| Hosting | Render free tier (API + static frontend + free Postgres) |
| `SEED_DEMO` | `true` |
| `DEMO_RESET_ON_START` | `true` (fresh demo data when API container restarts) |
| `ALLOW_MOCK_PAYMENTS` | `true` |
| Accounts | Public `demo_student` / `demo_teacher` / `demo_staff` — password `demo1234` |
| Data | Fake only — no real student PII |
| Admin risk | **Do not** treat as secure; anyone can vandalize demo data |

Step-by-step: [`portfolio-demo-deploy.md`](./portfolio-demo-deploy.md).

### B. Production studio instance

Purpose: Real teachers and students.

| Setting | Value |
|---------|--------|
| `DEBUG` | `False` |
| `SEED_DEMO` | `false` (or remove after one-time seed) |
| `DEMO_RESET_ON_START` | `false` |
| `ALLOW_MOCK_PAYMENTS` | `false` when Stripe is live |
| Accounts | Real users; superuser known only to client owner |
| Plan | Paid hosting tier if cold starts or cron jobs are unacceptable |
| Media | Volume mount or S3-compatible storage |
| Backups | Automated Postgres backups enabled |

Full runbook: [`operations-guide.md`](./operations-guide.md).

---

## 6. Handover checklist (sign-off)

Use this as a literal checklist when closing a project.

### Access transfer

- [ ] GitHub repo access (client org or export archive)
- [ ] Hosting dashboard (Render/etc.) — **client is owner**, you are collaborator if needed
- [ ] Postgres — connection string stored in client password manager
- [ ] Domain DNS — client registrar; document A/CNAME records
- [ ] Stripe — client Dashboard owner (you removed from live keys if applicable)
- [ ] Google Cloud project — client owns OAuth client
- [ ] Email provider — client owns SMTP/API keys

### Configuration record (store securely — not in git)

Deliver a **one-page secrets sheet** (1Password, Bitwarden, or encrypted PDF):

| Secret | Where used |
|--------|------------|
| `SECRET_KEY` | API env |
| `DATABASE_URL` | API env |
| Django superuser username + password | `/admin/` break-glass |
| Stripe `sk_live_…`, webhook secret | API env + Stripe Dashboard |
| Google client ID/secret | API env |
| SMTP credentials | API env |

### Application setup

- [ ] Migrations applied (`python manage.py migrate`)
- [ ] Auth groups exist (`python manage.py bootstrap_sandbox` without `--demo`)
- [ ] Staff superuser created (`createsuperuser` or agreed process)
- [ ] Studio branding set (name, logo) via staff UI
- [ ] Membership plans configured
- [ ] Teachers created + permissions set
- [ ] Class catalog / offerings seeded or entered
- [ ] `CORS_ALLOWED_ORIGINS` = production frontend URL
- [ ] `VITE_API_BASE` = production API URL (static site rebuild after change)
- [ ] Homework purge cron scheduled (`purge_expired_homework`) if using file uploads
- [ ] Smoke test: student books session, teacher sees it, staff sees report

### Documentation delivered to client

- [ ] This file (`client-handover.md`)
- [ ] Their production URLs (app + API if split)
- [ ] Login instructions for staff (not shared demo passwords)
- [ ] Who to contact for bugs vs new features
- [ ] Monthly cost estimate (hosting + Stripe fees + domain)

### Explicit “not included unless contracted”

- [ ] Source code warranty period and end date
- [ ] Whether you retain a license to reuse generic components
- [ ] Data export format if they leave the platform later

---

## 7. Environment variables (production reference)

Copy from [`.env.example`](../.env.example). Minimum production set:

| Variable | Example / notes |
|----------|-----------------|
| `SECRET_KEY` | Long random string |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | `app.studio.com,api.studio.com` |
| `DATABASE_URL` | Postgres connection string |
| `CORS_ALLOWED_ORIGINS` | `https://app.studio.com` |
| `VITE_API_BASE` | `https://api.studio.com` (frontend build-time) |
| `SECURE_SSL_REDIRECT` | `True` (or `false` behind platform TLS — see Render notes) |
| `DEFAULT_FROM_EMAIL` | `no-reply@studio.com` |
| `EMAIL_HOST`, … | Real SMTP |
| `STRIPE_*` | Live keys when taking money |
| `SEED_DEMO` | `false` |
| `DEMO_RESET_ON_START` | `false` |
| `ALLOW_MOCK_PAYMENTS` | `false` |

Demo-only additions: `SEED_DEMO=true`, `DEMO_RESET_ON_START=true`, `ALLOW_MOCK_PAYMENTS=true`.

---

## 8. URLs they should know

| URL | Who uses it |
|-----|-------------|
| `https://app…/` | Everyone — React login |
| `https://api…/api/` | Developers — browsable API (optional; lock down in prod) |
| `https://api…/admin/` | Owner only — Django admin break-glass |

**Do not** give clients the API URL as “the app” — legacy Django HTML login lives there.

---

## 9. Training outline (30–45 min call)

Suggested agenda for staff:

1. **Sign in** as staff — home dashboard
2. **Branding** — studio name and logo
3. **Teachers** — create account, set permissions
4. **Classes / catalog** — offerings students can request
5. **Membership plans** — tickets vs subscription (and Stripe if live)
6. **Sessions** — teacher creates; student books open sessions
7. **Homework & feedback** — teacher workflow; 7-day file retention
8. **Glossary** — studio terminology for students
9. **Where not to go** — `/admin/` unless break-glass; no shared demo passwords in prod

Record the call or provide [`learn-the-app.md`](./learn-the-app.md) as async reference.

---

## 10. Ongoing operations (set expectations)

| Task | Frequency | Who |
|------|-----------|-----|
| Postgres backups | Daily (managed provider) | Hosting |
| `purge_expired_homework` | Daily cron | Operator |
| Dependency / security updates | Monthly or quarterly | Developer (retainer) or client’s hire |
| Stripe webhook monitoring | As needed | Owner |
| Rotate `SECRET_KEY` | Rare; planned maintenance | Developer |
| Demo data reset | On container start (demo only) | Automatic |

**Free-tier Render:** API sleeps after inactivity (~50s cold start). Fine for portfolio; poor for paying studios.

---

## 11. Support & change requests

Define in the contract:

| Tier | Examples |
|------|----------|
| **Bug** | Login broken, bookings not saving, payments not crediting |
| **Small change** | Copy tweak, new glossary term, extra teacher |
| **Feature** | New payment model, mobile app, multi-location |
| **Infrastructure** | Move host, custom domain, scale-up |

Point clients at [`TICKETS.md`](../TICKETS.md) style tracking if you use it internally; give them email or a simple form for production issues.

---

## 12. Security talking points (for the client)

Say plainly:

1. **Demo passwords are public** — never use demo mode with real student data.
2. **`demo_staff` is a superuser** — fine for sandbox; remove superuser flag in production or delete demo users entirely.
3. **Homework files** auto-delete after 7 days — confirm that matches their policy.
4. **JWT in sessionStorage** — standard for this stack; XSS hardening matters (see [`security.md`](./security.md)).
5. **They own their data** — document how to export users/bookings if they switch vendors.

---

## 13. Rough monthly cost (order of magnitude)

Adjust for region and traffic; useful for proposals.

| Item | Demo (Render free) | Small production |
|------|--------------------|------------------|
| API + DB | $0–7 | $15–50+ |
| Static frontend | $0 | $0–7 |
| Domain | — | ~$12/year |
| Email (SendGrid etc.) | — | $0–20 |
| Stripe | — | 2.9% + 30¢ per charge |

---

## 14. Quick proposal blurb (copy/paste)

> I deploy a custom-branded booking and scheduling platform for your studio: students book classes, teachers manage availability and session notes, and staff run memberships and reporting. Each studio gets its own secure database and domain. Phase 1 covers launch on managed hosting with your branding and user accounts; Stripe and Google Meet can be added when you are ready. You receive full hosting ownership, credentials, and a handover guide so you are not locked in.

---

## 15. Builder pre-flight (your internal list)

Before telling a client “you’re live”:

1. Run `python manage.py test` on the release commit.
2. Confirm `DEBUG=False` and no demo seed flags in production.
3. Verify login, book, cancel, staff branding, and (if applicable) Stripe test payment.
4. Confirm backups and cron jobs exist on the paid plan if required.
5. Remove yourself from unnecessary admin accounts; revoke temporary API keys.
6. Send the handover checklist (section 6) completed.

---

*Questions about extending the product (multi-tenant, SimplyBook sync, AI features) → [`future-features.md`](./future-features.md).*
