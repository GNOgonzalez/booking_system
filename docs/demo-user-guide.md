# Try the booking demo

**Live app:** [https://booking-frontend-a6i2.onrender.com/login](https://booking-frontend-a6i2.onrender.com/login)

A language-school-style booking system: students buy memberships and book lessons, teachers manage schedules and write progress reports, and staff run the studio from one dashboard.

This is a **sandbox prototype** on Render’s free tier. Data may reset, and the API can take up to a minute to wake up after idle time.

---

## Before you start

| Note | What it means |
|------|----------------|
| **Cold start** | The first click after idle time may spin for ~30–60 seconds while the API wakes up. Refresh once if a page stays blank. |
| **Mock payments** | Membership purchases are simulated — no real card charges. |
| **Shared demo** | Anyone can log in and change data. The database may reset when the server restarts. |
| **No real email** | Confirmation emails are not sent in this environment. |
| **Meeting links** | Video links are placeholders, not real Google Meet rooms. |

---

## Demo logins

All accounts use password **`demo1234`**.

| Role | Username | Best for trying… |
|------|----------|------------------|
| **Student** | `demo_student` | Booking, membership, progress, homework |
| **Teacher** | `demo_teacher` | Schedule, class requests, reports, homework |
| **Staff** | `demo_staff` | Studio-wide admin, plans, branding, metrics |

You can also **create your own student account** from the sign-in page → **Create a student account**.

---

## What each role does

### Student

Students browse open lesson slots, book with **tickets** from a membership, request custom times, track skill progress, and complete homework.

**Main areas in the sidebar:**

| Page | What you can do |
|------|-----------------|
| **Home** | Studio announcements, onboarding checklist, quick links |
| **Book a lesson** | Calendar of open sessions — filter by subject, teacher, or time |
| **Request a class** | Ask for a specific time; teacher must approve before it’s confirmed |
| **My bookings** | View and cancel upcoming lessons |
| **Membership** | Buy a mock subscription or ticket pack (Japanese or English plans) |
| **My progress** | Charts and session history with teacher feedback |
| **Homework** | View assignments and reply to journal prompts |
| **Inbox** | Messages from teachers |
| **Curriculum** | Published studio learning content |
| **Profile** | Display name, timezone, theme, password |

### Teacher

Teachers own a **class catalog**, publish **availability**, open **sessions** for students to book, approve **class requests**, and write **session reports** and **homework**.

**Main areas:**

| Page | What you can do |
|------|-----------------|
| **My sessions** | Calendar of all your lessons; see who’s enrolled |
| **Class requests** | Approve or deny student-requested times |
| **New session** | Open a slot on the calendar (must fall in your availability) |
| **Classes** | Your teachable offerings (subject, level, topic) |
| **Availability** | Weekly recurring hours + special one-off days |
| **Student reports** | Rate skills and leave notes after a lesson |
| **Homework** | Assign file uploads or journal prompts |
| **Blog posts** | Publish announcements on the home feed |

### Staff

Staff manage the whole studio: all teachers, membership **plans**, student accounts, branding, glossary labels, and reports.

**Highlights:**

| Page | What you can do |
|------|-----------------|
| **Staff dashboard** | List teachers; jump to their schedule or permissions |
| **Studio schedule** | Every teacher on one calendar |
| **Class roadmap** | Master catalog of subjects, levels, and topics |
| **Students** | Activate or deactivate accounts |
| **Memberships** | Edit plan prices and ticket allowances |
| **Reports** | Bookings and activity overview |
| **Glossary** | Rename terms app-wide (e.g. “Student” → “Client”) |
| **Sign-in branding** | Logo and studio name on the login page |
| **Metrics** | Customize progress chart dimensions |

---

## Recommended walkthrough (~10 minutes)

### 1. Student — buy membership and book a lesson

1. Sign in as **`demo_student`** / `demo1234`.
2. Open **Membership** → choose **Japanese** or **English** → click **Purchase subscription (mock)**.
3. Go to **Book a lesson** → pick an open session on the calendar → **Book**.
4. Open **My bookings** to confirm the reservation.

`demo_student` starts without a membership so you can try the purchase flow. Upcoming open slots are left unbooked for you; past sessions are pre-seeded for progress charts.

### 2. Student — request a custom time

1. Still as `demo_student` (with tickets remaining).
2. **Request a class** → choose `demo_teacher` and a class → pick a time from the availability grid → submit.
3. Tickets are **held** until the teacher responds.

### 3. Teacher — approve the request

1. Sign out → sign in as **`demo_teacher`** / `demo1234`.
2. Open **Class requests** → review the pending request → **Approve** (or edit time/class first).
3. The student’s booking is confirmed and tickets are spent.

### 4. Teacher — reports and homework

1. **Student reports** → open a past session → add skill ratings and notes.
2. **Homework** → assign a journal prompt or file task to a student.

### 5. Student — progress and homework

1. Sign back in as **`demo_student`**.
2. **My progress** — view charts seeded from earlier demo lessons.
3. **Homework** — read assignments and post a reply.

### 6. Staff — studio overview

1. Sign in as **`demo_staff`** / `demo1234`.
2. **Staff dashboard** — see teachers and open **Permissions** to toggle what each teacher can do.
3. **Studio schedule** — all sessions in one view.
4. **Memberships** — see how plans and ticket packs are configured.

---

## Key concepts

| Term | Meaning |
|------|---------|
| **Class** | A teachable offering (e.g. “English Conversation · Intermediate”) |
| **Session** | A specific time slot on the calendar |
| **Booking** | A student’s reserved seat in a session |
| **Ticket** | Currency used to book; comes from membership |
| **Class request** | Student asks for a custom time; teacher must approve |
| **Membership** | Subscription or ticket pack tied to a subject (Japanese / English) |

---

## Troubleshooting

| Problem | Try this |
|---------|----------|
| Login spins forever | Wait up to 60s for the API cold start, then retry |
| “Login failed” | Use exact usernames: `demo_student`, `demo_teacher`, or `demo_staff` — password `demo1234` |
| Can’t book | Buy a mock membership first (**Membership** page) |
| No open sessions | Sign in as `demo_teacher` → **New session** to add a slot |
| Data looks wrong | Demo data may have been reset — run through the walkthrough again |

---

## Technical notes (for reviewers)

- **Stack:** Django REST API + React SPA + PostgreSQL
- **Source:** [github.com/GNOgonzalez/booking_system](https://github.com/GNOgonzalez/booking_system)
- **Deploy:** Render (API + DB + static frontend)

Questions or feedback: see the portfolio site contact section.
