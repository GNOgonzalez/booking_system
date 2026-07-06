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

_(move closed tickets here)_
