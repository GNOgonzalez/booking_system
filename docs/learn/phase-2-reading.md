# Phase 2 — Reading & Concepts

Study material for the core booking slice: models, services, forms, book/cancel flow.

Read in order for a narrative, or jump to sections that feel unclear.

---

## 0. Progress tracker (update as you go)

| Step | Status | Notes |
|------|--------|-------|
| Phase 2 docs read | ✅ | `phase-2-in-plain-english.md`, `phase-2-reading.md` |
| `Session` model + migrate | ✅ | Named `Session` in code (docs say `ClassSession` — same idea) |
| `Booking` model + migrate | ✅ | `student` + `session` FKs; no student on `Session` |
| Register in admin | ✅ | `Session`, `Booking` in `admin.py` |
| `services/booking.py` — `can_book` | ✅ | Nested `if`; shell-tested |
| `services/booking.py` — `create_booking` | ✅ | Calls `can_book` first |
| `services/booking.py` — `can_cancel` | ✅ | Lives in **service** (not model) — your choice |
| `services/booking.py` — `cancel_booking` | ✅ | Updates one row + `save()` |
| Shell testing | ✅ | Use real usernames (`kuma`), not `'your_student'` |
| Teacher `SessionForm` + `teacher_create_session` | ✅ | `forms.py`, view, `create_session.html`, URL |
| Student book POST (practice view) | 🟡 | `student_book_session` started — **fix `session_id` bug** (see §0c) |
| Student session list (proper UI) | ⬜ | Replace hardcoded `session 1` button |
| Student my bookings + cancel POST | ⬜ | |
| Mock `has_active_membership` in `can_book` | ⬜ | Optional stub when views work |

**Checkpoint not done yet:** explain `create_booking()` without notes; book/cancel reliably from the **browser**; session list instead of test button.

---

## 0b. Concepts you learned (2026-06-20 session)

- Model fields → Postgres columns; FK stores another row's `id`
- `choices` = fixed enum on one column; another table → `ForeignKey` + dropdown
- Many students per session = many `Booking` rows, same `session_id`
- `related_name` = Python nickname for reverse SQL (`WHERE teacher_id = ?`) — **no extra table**
- `session.bookings.filter(...)` — dot chain: object → related rows → filter → count
- `self` only inside model methods; service functions use `booking`, `user`, `session` params
- Service functions need **no** `settings.py` registration — just `import` in views
- New model habit: model → `check` → `makemigrations` → `migrate` → admin → shell

**Shell reminders:**

```bash
# from project root (not scheduling/services/)
python manage.py shell
```

```python
exit()                          # leave shell
import importlib; import scheduling.services.booking as b; importlib.reload(b)  # after editing booking.py
User.objects.values_list('username', flat=True)   # find real usernames
```

---

## 0c. Concepts you learned (forms + views session)

### Django forms

- **`class Meta`** on `ModelForm` — inner config Django reads (`model`, `fields`); not called by you
- **`fields = [...]`** — whitelist of columns on the HTML form; omit `teacher`, `status` (view sets those)
- **`SessionForm(request.POST)`** — bind whole POST dict, not field-by-field args
- **`form.is_valid()`** — field validation only; no DB write yet
- **`form.save(commit=False)`** — returns model instance; set `teacher` / `status`; then `session.save()`
- **`widgets`** + `datetime-local` — browser sends `2026-06-20T15:30`; use `format='%Y-%m-%dT%H:%M'`

### Views — teacher create session

- **GET** = open URL in browser → empty form (`else: form = SessionForm()`)
- **POST** = submit → `SessionForm(request.POST)` → validate → save → **redirect**
- One URL, two methods — branch on `request.method`
- Template path in `render()` must **match filename**: `scheduling/create_session.html`

### Views — student book (POST-only action)

- **No ModelForm** — call `create_booking(request.user, session)` from service
- **`@require_POST`** — book/cancel must not be GET links
- **`get_object_or_404(Session, pk=session_id)`** — session id from URL, not `request.session`
- **Two `if`s, two jobs:** (1) student group = authorization (2) `create_booking` True/False = business rules
- **Import service:** `from scheduling.services.booking import create_booking`
- Template: small POST form — `action="{% url 'student_book_session' session.id %}"` + csrf, no `{{ form.as_p }}`

### Fix before book view works

```python
# ❌ wrong
def student_book_session(request):
    session = get_object_or_404(Session, pk=request.session_id)

# ✅ correct — session_id comes from URL pattern <int:session_id>
def student_book_session(request, session_id):
    session = get_object_or_404(Session, pk=session_id)
```

Non-students should get **403**, not redirect to student dashboard.

### Files you added/changed (step 5 + practice)

| File | Purpose |
|------|---------|
| `scheduling/forms.py` | `SessionForm` |
| `scheduling/views.py` | `teacher_create_session`, `student_book_session` |
| `scheduling/templates/scheduling/create_session.html` | Teacher form page |
| `scheduling/templates/scheduling/student_dashboard.html` | Test book button (session id `1`) |
| `config/urls.py` | `teacher_create_session`, `student_book_session` |

---

## 1. The big picture — what Phase 2 adds

**What you're building:**

```text
Teacher POST  →  ClassSession row
Student POST  →  services/booking.py  →  Booking row
Student POST  →  cancel path  →  Booking.status = cancelled
```

**Read (local):**

- [phase-2-in-plain-english.md](./phase-2-in-plain-english.md) — start here
- [architecture-and-roadmap.md](./architecture-and-roadmap.md) — sections 5–6 (permissions + booking flow diagram)
- [django-vs-crud-project.md](./django-vs-crud-project.md) — `crud.py` → `services/` map

**Why:** Phase 2 is your first **domain** work — data that represents the product, not just auth scaffolding.

---

## 2. Models — `Session` and `Booking`

> **Naming:** Your code uses `Session`; architecture docs say `ClassSession`. Same role — avoid clashing with Django's session *cookies* later if you rename.

**Concepts:**

- `ForeignKey` — link rows across tables (`teacher`, `student`, `session`)
- `DateTimeField` — real datetimes in Postgres (not strings)
- `choices` / status field — `open`, `confirmed`, `cancelled`
- Django auto `id` — you define relationships, not primary keys

**Read:**

- [Django models](https://docs.djangoproject.com/en/5.2/topics/db/models/)
- [Model field reference — DateTimeField](https://docs.djangoproject.com/en/5.2/ref/models/fields/#datetimefield)
- [ForeignKey](https://docs.djangoproject.com/en/5.2/ref/models/fields/#foreignkey)
- [Choices](https://docs.djangoproject.com/en/5.2/ref/models/fields/#choices)

**Practice:**

```bash
python manage.py makemigrations
python manage.py migrate
```

Register models in `admin.py` before building custom pages — fastest way to sanity-check schema.

---

## 3. Migrations (again, with real domain tables)

**What changes:** two new tables, foreign keys, maybe indexes later.

**Read:**

- [Django migrations overview](https://docs.djangoproject.com/en/5.2/topics/migrations/)
- [Migration operations](https://docs.djangoproject.com/en/5.2/ref/migration-operations/) — skim

**Habit:** model change → `makemigrations` → `migrate` → verify in admin or shell.

---

## 4. Service layer — `scheduling/services/booking.py`

**Concept:** one module owns booking rules. Views call it; templates never decide.

| Function | Lives in | When |
|----------|----------|------|
| `can_book(user, session)` | service | Before Booking exists |
| `create_booking(user, session)` | service | Student clicks Book |
| `cancel_booking(...)` | service | Student clicks Cancel |
| `can_cancel(user, booking)` | service | Check on existing row — you kept it in `booking.py` |

**Read (local):**

- [architecture-and-roadmap.md](./architecture-and-roadmap.md) — section 9 (decisions: `can_book`, `create_booking`)
- [postgres-roles-membership-inheritance.md](./postgres-roles-membership-inheritance.md) — app membership vs Postgres roles

**Read (general):**

- [Django design philosophies — loose coupling](https://docs.djangoproject.com/en/5.2/misc/design-philosophies/#loose-coupling) — why not stuff logic in templates

**Why:** When you add React in Phase 5, the API calls the same `services/` — rules aren't duplicated.

---

## 5. Querysets — listing and filtering

**You'll write queries like:**

- Open sessions: `status='open'`, `starts_at__gt=now`
- My bookings: `Booking.objects.filter(student=request.user, status='confirmed')`
- Count seats taken: `session.bookings.filter(status='confirmed').count()` (`related_name='bookings'`)

**Read:**

- [Making queries](https://docs.djangoproject.com/en/5.2/topics/db/queries/)
- [QuerySet API — field lookups](https://docs.djangoproject.com/en/5.2/ref/models/querysets/#field-lookups) — `__gt`, `__lte`, etc.
- [Related objects](https://docs.djangoproject.com/en/5.2/topics/db/queries/#following-relationships-forward)

---

## 6. Django Forms — teacher creates a session

**Concept:** `ModelForm` maps HTML fields → model fields → validation → save.

**Flow:**

```text
GET  → empty form
POST → form.is_valid()? → save(commit=False) → set teacher/status → session.save() → redirect
```

**You built:** `SessionForm`, `teacher_create_session`, `create_session.html`.

**`class Meta` cheat sheet:**

| Key | Meaning |
|-----|---------|
| `model = Session` | Which table this form maps to |
| `fields = [...]` | Which columns appear as inputs |
| `widgets = {...}` | HTML input types (e.g. `datetime-local`) |

**Read:**

- [Django forms](https://docs.djangoproject.com/en/5.2/topics/forms/)
- [Model forms](https://docs.djangoproject.com/en/5.2/topics/forms/modelforms/)
- [Working with form templates](https://docs.djangoproject.com/en/5.2/topics/forms/#rendering-fields-manually) — `{{ form.as_p }}` is fine for now

**Security:** CSRF token in every POST form — Django template: `{% csrf_token %}`.

---

## 7. POST actions — book and cancel

**Concept:** GET loads pages; POST changes data.

| Action | Method |
|--------|--------|
| List sessions | GET |
| Book session | POST |
| Cancel booking | POST |
| Create session | POST |

**Read:**

- [Django CSRF](https://docs.djangoproject.com/en/5.2/ref/csrf/)
- [Request and response objects](https://docs.djangoproject.com/en/5.2/ref/request-response/)

**Habit:** Book/cancel as small POST forms (button + `{% csrf_token %}`), not GET links — avoids accidental actions and matches logout pattern from Phase 1.

**You started:** `student_book_session` + test button on student dashboard.

**Calling a service from a view:**

```python
from scheduling.services.booking import create_booking

success = create_booking(request.user, session)  # user + Session object, not id
```

**URL captures id → view argument:**

```python
# urls.py
path('student/sessions/<int:session_id>/book/', ...)

# views.py
def student_book_session(request, session_id):
    ...
```

---

## 8. Transactions and race conditions (intro)

**Concept:** two students click Book when one seat remains — without care, both might succeed.

**Phase 2 goal:** understand why `create_booking()` is one function; optionally wrap save in `transaction.atomic()`.

**Read:**

- [Database transactions](https://docs.djangoproject.com/en/5.2/topics/db/transactions/)
- Skim: `select_for_update()` — you'll use more in polish phase

**Don't panic:** get the happy path working first; add transaction hardening when tests reveal double-book edge cases.

---

## 9. Mock membership gate

**Concept:** `can_book()` calls `has_active_membership(user)` — Phase 2 returns `True` or checks a stub field. Phase 4 swaps the implementation.

**Read (local):**

- [glossary.md](./glossary.md) — "membership" disambiguation
- [architecture-and-roadmap.md](./architecture-and-roadmap.md) — Membership in ER diagram (planned)

---

## 10. Security habits (Phase 2)

1. **Group check in view** — student routes reject teachers (same as Phase 1)
2. **Business rules in service** — never only hide Book button in template
3. **`create_booking` is the only create path** — no stray `Booking.objects.create` in views
4. **Cancel checks ownership** — `can_cancel(user, booking)` in service, then `cancel_booking`
5. **POST for mutations** — book, cancel, create session

---

## 11. Suggested build order (reading ↔ doing)

| Step | Build | Read section | Status |
|------|-------|--------------|--------|
| 1 | `Session` model | §2, §3 | ✅ |
| 2 | `Booking` model | §2, §3 | ✅ |
| 3 | `services/booking.py` | §4, §8 | ✅ |
| 4 | Shell test `create_booking` / `cancel_booking` | §4, §5 | ✅ |
| 5 | Teacher `ModelForm` + view + template | §6 | ✅ |
| 6 | Student book POST view | §7, §0c | 🟡 fix `session_id` |
| 7 | Student session list (real UI) | §5, §7 | ⬜ **start here** |
| 8 | Student my bookings + cancel POST | §4, §7 | ⬜ |
| 9 | Mock membership in `can_book` | §9 | ⬜ |

### Next session (read §5, §7, §0c)

1. **Fix** `student_book_session(request, session_id)` — use `pk=session_id`; 403 for non-students
2. **Student session list** — GET open future sessions; Book button per row (not hardcoded id `1`)
3. **`student_cancel_booking`** — POST → `cancel_booking(request.user, booking)`
4. **My bookings page** — list confirmed bookings + Cancel buttons
5. Optional: Django **messages** for “Booked!” / “Session full”
6. Optional: link on teacher dashboard → create session

---

## 12. Self-check questions

1. What's the difference between `ClassSession` and `Booking`?
2. Why does `can_book` live in `services/` but `can_cancel` live in your service?
3. Why should views call `create_booking()` instead of creating a `Booking` directly?
4. What checks belong in `can_book` vs in the view?
5. Why use POST for book/cancel instead of a GET link?
6. What is mock membership preparing you for in Phase 4?
7. What happens when capacity is 1 and two students book at once? (Even a hand-wavy answer counts.)
8. What is `class Meta` on a ModelForm?
9. Why `form.save(commit=False)` before setting `teacher`?
10. What's the difference between `request.session` and `session_id` in the book URL?
11. Why two different `if` checks in `student_book_session` (group vs `create_booking`)?

---

## 13. Local docs

- [phase-2-in-plain-english.md](./phase-2-in-plain-english.md) — ADHD-friendly recap
- [phase-1-in-plain-english.md](./phase-1-in-plain-english.md) — auth + groups (prerequisite)
- [glossary.md](./glossary.md) — terms (FK, membership, POST)
- [architecture-and-roadmap.md](./architecture-and-roadmap.md) — roadmap + diagrams
- [LEARNING_PATH.md](../LEARNING_PATH.md) — checklists (local, not in git)

---

## 14. New model checklist (every time)

1. Write model in `scheduling/models.py` (`related_name` if 2+ FKs to same table)
2. `python manage.py check`
3. `python manage.py makemigrations` → `migrate`
4. Register in `scheduling/admin.py`
5. Smoke test in `/admin/` and `python manage.py shell`

---

## 15. Optional deeper reads (not required for Phase 2)

- [Django admin — customizing](https://docs.djangoproject.com/en/5.2/ref/contrib/admin/) — list filters on ClassSession
- [Time zones in Django](https://docs.djangoproject.com/en/5.2/topics/i18n/timezones/) — when you display local times (Phase 3+)
- [Class-based views](https://docs.djangoproject.com/en/5.2/topics/class-based-views/) — stick with function views until comfortable
