# SimplyBook vs one booking platform — cost comparison

One-page reference for studio owners comparing **two SimplyBook subscriptions** (e.g. Japanese + English programs) against **one integrated platform** like this app.

---

## The problem studios hit with SimplyBook

Many language studios run **separate SimplyBook accounts** per program or location:

- Japanese lessons on one SimplyBook site
- English / other subjects on another

Each account is a **separate subscription**, separate admin login, separate student lists, and **no shared membership** across subjects unless you wire it manually outside SimplyBook.

---

## Monthly cost snapshot (2025–2026 typical pricing)

| Approach | What you pay | Rough monthly range |
|----------|--------------|---------------------|
| **2 × SimplyBook** | Two paid plans (Standard or Premium tier each) | **~$50–160/mo** depending on tier and add-ons |
| **This platform (showcase)** | Supabase free + Render free | **$0/mo** demo tier |
| **This platform (small studio prod)** | Supabase Pro or Render paid + domain | **~$25–45/mo** |

SimplyBook pricing varies by plan and region; check [simplybook.me/pricing](https://simplybook.me/pricing) for current numbers. The point is **duplication**: two products = two bills + double admin work.

---

## What you get with one platform instead

| Capability | 2 × SimplyBook | One platform |
|------------|----------------|--------------|
| Single student login | No (two sites) | Yes |
| Membership + ticket packs per subject | Per account only | One account, multiple plans |
| Teacher schedule + availability | Per account | Shared studio calendar |
| Session feedback + progress charts | External tools | Built in |
| Homework / file exchange | External tools | Built in |
| Staff dashboard + alerts | Limited | Built in |
| Custom branding / domain | Per SimplyBook site | One deploy, your domain |
| API / data ownership | SimplyBook export | Your Postgres (Supabase) |

---

## Hidden costs of two SimplyBook accounts

- **Staff time** — two calendars, two reminder setups, two payment configs
- **Student confusion** — “Which link do I use for Japanese vs English?”
- **No cross-subject view** — progress and membership live in silos
- **Integrations twice** — Stripe, Zoom, email templates duplicated
- **Migration later** — importing two histories into one system is harder than starting unified

---

## When SimplyBook still makes sense

- Solo teacher, one subject, no custom software budget
- Need booking **today** with zero dev time
- No plans for membership tickets, homework, or multi-teacher studio ops

---

## When one platform wins

- Multi-subject studio (Japanese + English + more)
- Membership / ticket packs and class requests
- Teachers write session notes; students see progress
- You want **one URL**, one admin, one database — and optional custom features over time

---

## Talking points for a 5-minute demo

1. Log in as **demo_student** — home shows membership, next lesson, tickets.
2. **Book a lesson** from open sessions; cancel from Upcoming tab.
3. **Progress + homework** — not available in standard SimplyBook without add-ons.
4. **Staff view** — alerts for signups and payments (demo_staff).
5. Close with: *“Two SimplyBook bills and two admin worlds — or one platform from about $25/mo when you outgrow free hosting.”*

Full walkthrough: [`demo-script.md`](demo-script.md).

---

## Disclaimer

This document compares **generic SaaS patterns**, not a formal quote. SimplyBook features and prices change; use their site for exact figures. This app is a **portfolio / custom-build example**, not a hosted SimplyBook competitor product.
