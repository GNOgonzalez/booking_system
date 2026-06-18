# Phase 1 — Reading & Concepts

Short reference after completing auth and role-gated dashboards.

---

## 1. Django auth (built-in)

**Read (skim):**

- [Django auth overview](https://docs.djangoproject.com/en/5.2/topics/auth/)
- [Login / logout views](https://docs.djangoproject.com/en/5.2/topics/auth/default/#module-django.contrib.auth.views) — what `django.contrib.auth.urls` gives you

**You used:**

- `User` model (`auth_user` table)
- `Group` model (`auth_group`, `auth_user_groups`)
- Session middleware (cookie after login)
- `@login_required` decorator

---

## 2. Profile pattern (1:1)

**Concept:** extend user data without replacing Django's User.

**Read:**

- [One-to-one relationships](https://docs.djangoproject.com/en/5.2/topics/db/examples/one_to_one/)
- `settings.AUTH_USER_MODEL` — why we use it instead of importing `User`

---

## 3. Groups vs permissions

**Groups** = labels you check in code (`user.groups.filter(name="teacher")`).

**Permissions** = fine-grained flags on models (defer until needed).

**Read:**

- [Django Groups](https://docs.djangoproject.com/en/5.2/topics/auth/default/#groups)

---

## 4. Views, URLs, templates

**Read:**

- [URL dispatcher](https://docs.djangoproject.com/en/5.2/topics/http/urls/)
- [Writing views](https://docs.djangoproject.com/en/5.2/topics/http/views/)
- [Templates](https://docs.djangoproject.com/en/5.2/topics/templates/)

**Flow:**

```text
urlpatterns  →  view function  →  render(template)
```

---

## 5. Redirects and settings

| Setting | Purpose |
|---------|---------|
| `LOGIN_REDIRECT_URL` | Where LoginView sends user after success |
| `LOGIN_URL` | Where `@login_required` sends guests (default `/accounts/login/`) |

**Read:**

- [Login redirect settings](https://docs.djangoproject.com/en/5.2/ref/settings/#login-redirect-url)

---

## 6. Security habits (Phase 1)

1. **Check roles in views** — not only hide links in templates
2. **Use `@login_required`** before role checks
3. **403** when user has no valid role at all
4. **Redirect** when user has a different valid role

---

## 7. Self-check questions

1. What's the difference between `User`, `Profile`, and `Group`?
2. Why is `LOGIN_REDIRECT_URL` in settings, not views?
3. What does `redirect("teacher_dashboard")` refer to?
4. Why can `gnogo` be in both `teacher` and `staff` groups?
5. What happens if a student visits `/teacher/dashboard/`?

---

## 8. Local docs

- [phase-1-in-plain-english.md](./phase-1-in-plain-english.md) — ADHD-friendly recap
- [architecture-and-roadmap.md](./architecture-and-roadmap.md) — diagrams + roadmap
- [LEARNING_PATH.md](../LEARNING_PATH.md) — checklists (local)
