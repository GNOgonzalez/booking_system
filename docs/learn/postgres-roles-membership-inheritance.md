# PostgreSQL: Roles, Membership, and Inheritance

A reference for concepts that often get mixed up — especially when you're also building a booking app with **student/teacher roles** and **memberships**.

---

## The confusion (read this first)

Three different worlds use similar words:

| Word | In PostgreSQL | In your booking app (Django) |
|------|---------------|------------------------------|
| **Role** | Database login + permissions | Student vs teacher (who can do what in the app) |
| **Membership** | Role A can "be a member of" role B (permission grouping) | Student pays for access to classes |
| **Inheritance** | Child **tables** inherit parent **tables** (SQL feature) | Not something you need for Phase 0–2 |

The Postgres tutorial talks about **database security and table design**. Your product docs talk about **users and business rules**. Same vocabulary, different layers.

```text
┌─────────────────────────────────────────┐
│  Your app (Django)                      │
│  student / teacher / membership         │  ← business logic, models, views
├─────────────────────────────────────────┤
│  PostgreSQL                             │
│  roles, grants, (optional) inheritance  │  ← who can connect & touch tables
└─────────────────────────────────────────┘
```

---

## 1. Roles (PostgreSQL)

### What a role is

In PostgreSQL, a **role** is an identity that can:

- **Log in** to the database (like `booking_user`)
- **Own** objects (tables, databases)
- **Hold permissions** (SELECT, INSERT, CREATE, etc.)

`CREATE USER` and `CREATE ROLE` are almost the same in Postgres. Internally, Postgres calls everyone a **role**. `CREATE USER` is just `CREATE ROLE` with `LOGIN` allowed.

You already created one:

```sql
CREATE USER booking_user WITH PASSWORD 'devpassword123';
```

That's a **database role** — the account Django uses to connect.

Your Mac user `gnogo` is also a role when you run `psql postgres` without `-U`.

### What roles are NOT

- Not "student" or "teacher" in your app
- Not Django's `User` model
- Not something your end users think about

**Analogy:** A Postgres role is like a **building key card**. Django's worker (`booking_user`) has a card that lets it into the `booking_dev` database. Students and teachers are **people inside the building** — modeled in Django later.

### Permissions you used: `GRANT`

```sql
GRANT ALL PRIVILEGES ON DATABASE booking_dev TO booking_user;
GRANT ALL ON SCHEMA public TO booking_user;
```

**Translation:**

| Statement | Meaning |
|-----------|---------|
| `GRANT ... ON DATABASE` | `booking_user` may connect to and use `booking_dev` |
| `GRANT ... ON SCHEMA public` | May use the default `public` schema (where tables live) |
| `GRANT CREATE ON SCHEMA public` | May create tables there (Django migrations need this) |

Postgres is **deny by default** for new roles. Without `GRANT`, `booking_user` couldn't do much even with the right password.

### Role attributes (skim for later)

Roles can have flags like:

- `LOGIN` — may connect (users have this)
- `SUPERUSER` — full admin (your Mac user often has this locally)
- `CREATEDB` — may create databases

You don't need to memorize these for Phase 0.

### Official reading

- [PostgreSQL — Database roles](https://www.postgresql.org/docs/current/user-manag.html)
- [PostgreSQL — Privileges](https://www.postgresql.org/docs/current/ddl-priv.html)

---

## 2. Membership (PostgreSQL)

### What membership means in Postgres

**Role membership** means: role A is a **member of** role B, so A **inherits B's permissions**.

```sql
-- Example only — you did NOT need this for Phase 0
CREATE ROLE app_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_readonly;

CREATE USER report_bot WITH PASSWORD 'secret';
GRANT app_readonly TO report_bot;
```

Now `report_bot` gets SELECT permission **because it's a member of** `app_readonly`.

Postgres docs describe this as:

```text
role_membership → one role inherits another role's privileges
```

### Membership vs `GRANT` directly

| Approach | When it's used |
|----------|----------------|
| `GRANT ... TO booking_user` | Give permission directly to one role |
| `GRANT role_b TO role_a` | `role_a` is a **member of** `role_b` and picks up its permissions |

Membership is for **grouping permissions** — like "all analysts get the `analyst` role."

### What membership is NOT (in your app)

**Student membership** (paying to access classes) is a **business concept**. You will model it in Django, e.g.:

```text
Membership model → student, active_until, plan_name, ...
```

That data lives in a **table** Postgres stores. It is not Postgres "role membership."

| Postgres membership | App membership |
|---------------------|----------------|
| Security / permissions | Product / billing / access rules |
| `GRANT role TO role` | `Membership.active == True` |
| DBA configures | You build in Python |

For your dev setup, you only need **one** database role (`booking_user`). Student/teacher/membership are **Django models** in Phase 1–2.

---

## 3. Inheritance (PostgreSQL)

### What table inheritance is

PostgreSQL can make a **child table** inherit columns from a **parent table**:

```sql
-- Tutorial-style example — NOT for your booking app
CREATE TABLE cities (
    name text,
    population float
);

CREATE TABLE capitals (
    state char(2)
) INHERITS (cities);
```

`capitals` automatically has `name` and `population` **plus** `state`. Queries can target parent, child, or both.

This is **table structure inheritance** — a SQL design pattern. It is rare in Django projects.

### What inheritance is NOT

| People think… | Reality |
|---------------|---------|
| OOP class inheritance | Different idea — Python `class Child(Parent)` is Django/Python |
| "Student inherits from User" | You'd use a ForeignKey or profile model, not Postgres INHERITS |
| Django model inheritance | Django has [model inheritance](https://docs.djangoproject.com/en/5.2/topics/db/models/#model-inheritance) — still not Postgres `INHERITS` |

### Do you need Postgres table inheritance?

**No** for your booking app. Use normal tables:

```text
auth_user (Django built-in)
student_profile → FK to user
teacher_profile → FK to user
class_session
booking
membership
```

Clear foreign keys beat Postgres `INHERITS` for what you're building.

### When Postgres inheritance appears

- Advanced Postgres docs and tutorials
- Some legacy or analytics schemas
- Almost never in beginner Django tutorials

**Safe approach:** Understand it exists, skip using it. If the tutorial has an inheritance section, read it as "one way to structure tables" and move on.

### Official reading

- [PostgreSQL — Inheritance](https://www.postgresql.org/docs/current/ddl-inherit.html) (skim)

---

## 4. How this maps to your project

### What you already did (Postgres layer)

```text
PostgreSQL server
  └── database: booking_dev
        └── role: booking_user (LOGIN, password)
              └── GRANT: can use public schema, create tables
                    └── Django migrate → creates django_* and auth_* tables
```

One DB user. Django owns the schema. End users don't get Postgres logins.

### What you'll build later (app layer)

```text
Django User (auth_user table)
  ├── StudentProfile (role = student)
  ├── TeacherProfile (role = teacher)
  └── Membership (active? paid until? can_book?)
        └── can_book() / can_cancel() in Python services
```

Students never run `psql`. They log in through Django. **Authorization** (can this student book?) is Python + Django, not `GRANT` in Postgres.

---

## 5. Cheat sheet

| Term | Layer | You need it now? |
|------|-------|------------------|
| Postgres **role** | Database | Yes — `booking_user` |
| Postgres **GRANT** | Database | Yes — done in Step 2 |
| Postgres **role membership** | Database | No — single app user is enough for dev |
| Postgres **table inheritance** | Database | No — skip for this project |
| App **student/teacher role** | Django | Phase 1 |
| App **membership** | Django | Phase 2+ (mock boolean first) |
| Django **model inheritance** | Django | Optional later; not Postgres INHERITS |

---

## 6. Questions to unstick yourself

After reading the Postgres tutorial section on roles, ask:

1. **Is this about who can connect to the database, or who can book a class?**  
   → Database = Postgres roles. Booking = Django.

2. **Is "membership" about `GRANT role TO role` or a paying student?**  
   → `GRANT` = Postgres. Paying student = your `Membership` model later.

3. **Does inheritance mean tables or Python classes?**  
   → In Postgres docs: tables. In Django docs later: models. Different chapters.

---

## 7. When you're ready in Django (not Postgres)

- **Student vs teacher:** [Django auth groups](https://docs.djangoproject.com/en/5.2/topics/auth/default/#groups) or a `role` field on a Profile model
- **Membership:** your own `Membership` model with `is_active` or `valid_until`
- **can_book / can_cancel:** methods on a service module, not in templates

See `LEARNING_PATH.md` Phase 1–2 for when to implement these.
