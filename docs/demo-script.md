# 5-minute portfolio demo script

Use the **frontend** URL (Render static site), not the API URL.

**Login:** `demo_student` / `demo1234` (showcase seed — membership + next lesson)

---

## Before you start (~30 seconds)

- Mention cold start: first click may take ~50s on free Render.
- Frame: *"This is a custom booking platform for multi-subject studios — one login, membership tickets, teachers, progress, and staff tools."*

---

## 1. Student home (45 sec)

**Path:** `/` after login

Point out:

- **Next lesson** card (date, teacher, join link if shown)
- **Membership** stats — tickets remaining, active plans
- **Low-ticket warning** if applicable (or explain it appears at ≤2 tickets)
- Quick links to Progress, Homework, Inbox

*"Unlike two separate SimplyBook sites, the student sees everything in one place."*

---

## 2. Book a lesson (60 sec)

**Path:** Sessions (`/sessions`)

- Show calendar + filters (class, time, teacher)
- Click an open session → panel → confirm book
- Or mention **Request custom time** (`/sessions/request`) for availability-based requests

*"Tickets deduct from the right subject membership automatically."*

---

## 3. My bookings (30 sec)

**Path:** Bookings (`/bookings`)

- **Upcoming** vs **Past** tabs
- Click upcoming session → cancel flow (optional — skip if you want to keep the showcase booking)

---

## 4. Progress & homework (45 sec)

**Path:** Progress (`/progress`)

- Subject tabs, chart history from past sessions
- **Homework** (`/homework`) — open assignment + journal entry

*"SimplyBook stops at scheduling; this keeps learning context in the same app."*

---

## 5. Staff snapshot (30 sec, optional)

**Logout → login:** `demo_staff` / `demo1234`

**Path:** Staff dashboard

- Alert columns: users, membership, financial
- *"Studio ops without living in Django admin."*

Avoid `/admin/` on a public demo URL.

---

## 6. Close — cost story (30 sec)

Open [`simplybook-cost-comparison.md`](simplybook-cost-comparison.md) or summarize:

- Two SimplyBook subscriptions ≈ **$50–160/mo** + duplicated admin
- Showcase hosting ≈ **$0/mo**; small production ≈ **$25–45/mo**
- One platform, one database, your domain when you're ready

---

## Portfolio link

Set on Vercel portfolio:

```text
PUBLIC_BOOKING_DEMO_URL=https://booking-frontend-xxxx.onrender.com
```

Deploy steps: [`portfolio-demo-deploy.md`](portfolio-demo-deploy.md).

---

## Reset showcase data

If a visitor books/cancels and you want a clean slate:

```bash
DATABASE_URL='...' python manage.py bootstrap_sandbox --demo --reset --showcase
```

Or temporarily set `DEMO_RESET_ON_START=true` on the API service and redeploy.

---

## Backup demo accounts

| Role | Login | Password |
|------|--------|----------|
| Student (empty) | Re-seed without `--showcase` for live purchase demo | |
| Teacher | `demo_teacher` | `demo1234` |
| Staff | `demo_staff` | `demo1234` |
