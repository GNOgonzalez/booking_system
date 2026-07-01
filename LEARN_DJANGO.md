# Learn Django — a self-guided course built on *this* app

A 5-week, offline-friendly tutorial. Each **ticket** is a learning task done **in order**.
Your own `booking_scheduling_app` is the textbook: you'll read real code, understand it,
then extend it.

Weeks 1–3 teach Django itself (fundamentals → app patterns → APIs/React/deploy). Weeks 4–5
turn you into a *maintainer*: the different kinds of tests (Week 4) and DevOps + the skill of
safely fixing hastily built "vibecoded" apps (Week 5). The capstone ties it all together.

## How to use this file

Each ticket has the same shape:

- **Concept** — the one idea to learn, explained in depth.
- **Look at** — the exact files in this repo that demonstrate it.
- **Principles** — the rules and mental models to remember, with the *why* behind each.
- **Do** — a concrete hands-on task. Type it yourself; don't copy-paste.
- **Check yourself** — questions. If you can answer them out loud, move on.

Work through them top to bottom. Don't skip — later tickets assume earlier ones.

### The one command loop you'll repeat forever

```bash
cd ~/repos/booking_scheduling_app
source .venv/bin/activate
python manage.py runserver          # see the site at http://127.0.0.1:8000
python manage.py shell              # a Python REPL with Django loaded
python manage.py makemigrations     # after you change models.py
python manage.py migrate            # apply DB changes
python manage.py test               # run the tests
```

### Offline tip

You won't have the internet on the plane. Django ships its own docs as docstrings, and the
fastest offline reference is the shell:

```python
from django.db import models
help(models.CharField)      # prints the full documentation for CharField
```

Get in the habit of `help()`-ing anything you don't recognize. It's like having the docs
built into the language.

---

# WEEK 1 — The fundamentals (how Django thinks)

Goal for the week: understand the **request → response** cycle and the **MVT**
(Model–View–Template) pattern well enough to trace any page end to end.

---

### LEARN-01 — The big picture: trace one request end to end

**Concept:**
Everything a web framework does boils down to one sentence: *a request comes in, a response
goes out.* When you type a URL and hit enter, your browser opens a connection to the server and
sends an **HTTP request** — a small text message that says "GET me the page at `/student/dashboard/`,
here are my cookies." Django's entire job is to look at that request and hand back an **HTTP
response** — usually an HTML page, sometimes JSON, sometimes a redirect. Every single page in
this app, no matter how complex, is just one trip through this loop.

Django organizes the code that produces that response using a pattern called **MVT**:
*Model*, *View*, *Template*. The **Model** is your data (rows in the database, represented as
Python objects). The **View** is the function that runs when a URL is hit — it's the brain that
decides what to do: fetch some models, check permissions, and pick a template. The **Template**
is the HTML file with blanks that the view fills in. The request flows through these three in
order, and the response comes back out.

If you've heard "MVC" (Model-View-Controller) elsewhere, here's the translation that trips
everyone up: Django's **View** is what other frameworks call the *controller* (the logic), and
Django's **Template** is what they call the *view* (the display). It's just naming — don't let
it confuse you.

**Look at:** `config/urls.py`, `scheduling/views/dashboard.py`,
`scheduling/templates/scheduling/student_dashboard.html`.

**Principles:**
- **There is no magic — every URL you can visit is one line in a `urls.py`.** If a page exists,
  there is exactly one route that points at exactly one view. When something is broken, this is
  your starting thread to pull: find the URL, find the view, find the template.
- **The flow is always the same four steps:** (1) browser sends a request to a URL, (2) Django's
  URL resolver matches it and calls a view function, (3) the view gathers data from models and
  renders a template, (4) Django returns the resulting HTML as an HttpResponse. Memorize this;
  every ticket in Week 1 is just zooming into one of these steps.
- **Separation of concerns is the whole point.** The URL layer only knows about *routing*. The
  view only knows about *logic and coordination*. The template only knows about *display*. When
  each layer stays in its lane, you always know where to look for a given kind of change.
- **Debugging follows the data.** "Wrong data on the page" → check the view (it chose the data).
  "Right data, ugly layout" → check the template (it chose the presentation). Knowing which
  layer owns a problem saves you hours.

**Do:**
1. Start the server. Log in and open `http://127.0.0.1:8000/student/dashboard/`.
2. In `config/urls.py`, find the line that maps `student/dashboard/` to a view.
3. Open that view in `scheduling/views/dashboard.py`. Read what it does.
4. Open the template it renders. Find where the data from the view appears in the HTML.
5. Draw the flow on paper: URL line → view function → template file → what you saw on screen.

**Check yourself:**
- Which file decides *what URL* runs *what code*?
- Where does the HTML actually live?
- If a page shows the wrong data, would you look in the view or the template first? Why?

---

### LEARN-02 — The project skeleton & `manage.py`

**Concept:**
A Django codebase has two levels of organization: the **project** and its **apps**. The
*project* (your `config/` folder) represents the whole website — it holds the master settings,
the root URL map, and the entry points that a web server talks to. An **app** is a smaller,
self-contained slice of functionality that lives inside the project. You have two apps:
`scheduling` (sessions, bookings, memberships, messages, curriculum) and `progress` (skills and
progress reports). Each app bundles its *own* models, views, templates, and migrations, so it can
be reasoned about — and in principle reused — on its own.

The glue that makes an app "count" is `settings.py`, specifically the `INSTALLED_APPS` list.
Django only loads models, admin registrations, templates, and management commands from apps that
appear there. This is the single most common beginner trap: you build a whole app, nothing works,
and it's because you forgot to add it to `INSTALLED_APPS`.

`manage.py` is your remote control for the project. Every administrative action — starting the
dev server, creating database tables, opening a Python shell with Django loaded, running tests —
goes through it. It's a thin wrapper that sets the `DJANGO_SETTINGS_MODULE` environment variable
(so Django knows which settings to use) and then dispatches to Django's command system.

**Look at:** `config/settings.py`, `config/urls.py`, `manage.py`, the `scheduling/` folder,
the `progress/` folder.

**Principles:**
- **Project = the whole site; app = one feature area.** The project owns settings and root
  routing. Apps own the actual features. A project is useless without apps; an app is inert until
  a project installs it. This division is what lets big Django codebases stay navigable.
- **`INSTALLED_APPS` is the on/off switch for every app.** If it's not listed, Django won't find
  its models (so `makemigrations` ignores it), won't register its admin, and won't load its
  templates. Whenever "my new thing isn't being detected," check this list first.
- **`settings.py` is the single control panel.** Database connection, installed apps, middleware
  order, timezone, static files, third-party config (DRF, CORS, JWT) — it all lives here. Reading
  this file top to bottom tells you almost everything about how a Django project is wired.
- **`manage.py` is how you talk to Django.** You'll run it dozens of times a day. `python manage.py
  help` lists every available command, including ones apps add themselves (this app adds
  `bootstrap_sandbox` and `sync_simplybook` — you'll learn how in LEARN-11).

**Do:**
1. Open `config/settings.py` and find `INSTALLED_APPS`. Sort the entries in your head into three
   buckets: *your* apps (`scheduling`, `progress`), *Django's* built-ins (`django.contrib.*`),
   and *third-party* packages (`rest_framework`, `corsheaders`).
2. Run `python manage.py help` and skim the command list. Find `runserver`, `migrate`,
   `makemigrations`, `shell`, `test`, `createsuperuser`, and the two custom ones this app added.

**Check yourself:**
- What's the difference between a project and an app, in one sentence each?
- What are three specific things that break if an app isn't in `INSTALLED_APPS`?
- What is `manage.py` actually *for*?

---

### LEARN-03 — URLs & routing

**Concept:**
When a request arrives, the first real decision Django makes is "which piece of my code should
handle this?" That decision is made by the **URL configuration** — a list of patterns Django
checks *top to bottom* until one matches. The matching pattern names a view, and that view runs.
This is called **routing**, and `urls.py` is the routing table.

Each route is a `path()` call with three parts: the URL string to match, the view to call, and a
`name` used for reverse lookups. That third part is subtle but crucial. You never want to hardcode
a URL like `/student/sessions/` throughout your templates, because the day you rename that URL,
every hardcoded copy breaks. Instead you give the route a stable `name` and refer to it by name;
Django computes the actual URL for you. (The `NoReverseMatch` error you hit earlier in this
project was exactly this system complaining that a template asked for a name that had no matching
route.)

Two more routing ideas complete the picture. **URL parameters** let a single pattern match many
URLs by capturing part of the path — `<int:booking_id>` grabs a number and passes it to the view
as an argument, so one route handles booking 1, booking 2, booking 999. And **`include()`** lets
a project delegate a whole URL prefix to an app's own `urls.py`, so routing stays modular instead
of one giant file. This project delegates everything under `/api/` and `/progress/` that way.

**Look at:** `config/urls.py`, `scheduling/api/urls.py`, `progress/urls.py`.

**Principles:**
- **A route has three parts, and each matters:** the pattern (*what to match*), the view (*what
  to run*), and the `name` (*how other code refers to it*). Skipping the `name` is a mistake that
  bites you later.
- **Routes are matched in order, first match wins.** If two patterns could match the same URL, the
  earlier one takes it. This is why more specific routes generally come before more general ones.
- **Never hardcode URLs — use names.** In templates it's `{% url 'student_session_list' %}`; in
  Python it's `reverse('student_session_list')` or `redirect('student_session_list')`. This gives
  you one source of truth: change the path string once, every reference updates automatically. A
  `NoReverseMatch` almost always means a name/route mismatch, not a "cache" problem.
- **URL parameters turn one route into infinitely many.** `<int:booking_id>` both *captures* and
  *type-checks* (only integers match) and then hands the value to your view as a keyword argument.
  There are other converters too (`<str:...>`, `<slug:...>`, `<uuid:...>`).
- **`include()` keeps routing modular.** The project's `urls.py` shouldn't know every API endpoint;
  it just forwards `/api/` to the API app's own routing file. This mirrors the project/app split —
  each app owns its URLs.

**Do:**
1. In `config/urls.py`, list every URL that starts with `teacher/` and say what each does.
2. Add a brand-new route: `path('ping/', views.ping, name='ping')`. Don't create the view yet —
   save and load `/ping/`. Read the error carefully (it says the view attribute doesn't exist).
   Learning to *read* errors is half of debugging. Then remove the line; you'll build the real
   view in LEARN-04.

**Check yourself:**
- What are the three arguments to `path()`, and what is each for?
- How does the value in `<int:booking_id>` reach the view function?
- Explain why `{% url %}` is safer than typing the path, using the `NoReverseMatch` bug as an example.

---

### LEARN-04 — Views (the "V" — request in, response out)

**Concept:**
A **view** is the workhorse of Django: a plain Python function (this project uses function-based
views) that receives an `HttpRequest` object and must return an `HttpResponse` object. That's the
entire contract. Everything else — querying the database, checking who's logged in, deciding
which template to render — is stuff you choose to do *inside* that function. The `request` object
is a rich bag of information about the incoming call: the HTTP method (`request.method`), the
logged-in user (`request.user`), submitted form data (`request.POST`), query-string params
(`request.GET`), and more.

Because building a full HTML response by hand would be tedious, Django gives you the `render()`
shortcut. `render(request, "template.html", context)` loads a template, injects a `context`
dictionary of data into it, and returns a finished `HttpResponse`. This is the single most common
thing a view does: gather data, then `render` a template with it.

The other big idea in views is the distinction between **GET and POST**. These are HTTP *methods*,
and they carry meaning: **GET** means "show me something, don't change anything" (safe to refresh,
safe to bookmark), while **POST** means "here's data, change the server state" (creating a booking,
updating a profile). A well-behaved app uses GET for reads and POST for writes, and views branch
on `request.method` to handle each. This isn't just convention — browsers, caches, and search
engines all assume GET is side-effect-free.

Finally: keep views **thin**. A view should coordinate, not contain deep business rules. It
gathers inputs, calls a service function to do the real work (you'll learn this in LEARN-12), and
hands the result to a template. Fat views that mix routing, rules, and rendering become impossible
to test and reuse.

**Look at:** `scheduling/views/dashboard.py`, `scheduling/views/student.py`,
`scheduling/views/common.py`.

**Principles:**
- **Every view obeys one contract: take a `request`, return an `HttpResponse`.** If you remember
  nothing else, remember this. `render()`, `redirect()`, and `HttpResponse()` all *produce* that
  response object.
- **`render(request, template, context)` is your default move.** The `context` dict is the bridge
  between Python and HTML: keys become variables available inside the template.
- **GET reads, POST writes — always.** Never perform a database write in response to a GET (a
  crawler or a refresh could trigger it repeatedly). Views typically look like
  `if request.method == 'POST': ...do the write and redirect... else: ...show the form...`.
- **The `request` object is your source of truth about the caller.** `request.user`, `request.method`,
  `request.POST`, `request.GET` — get comfortable reaching into it.
- **Thin views, fat services.** The view's job is coordination and translation between HTTP and
  your domain. The actual rules ("can this student book?") belong in a service so multiple views
  (and the API) can share them.

**Do:**
1. Create a real `ping` view in `scheduling/views/common.py`:
   ```python
   from django.http import HttpResponse

   def ping(request):
       return HttpResponse("pong")
   ```
2. Export it so the `views` package exposes it: add `ping` to `scheduling/views/__init__.py`.
3. Wire it in `config/urls.py`: `path('ping/', views.ping, name='ping')`.
4. Visit `/ping/`. You should see "pong".
5. Make it dynamic: return `HttpResponse(f"pong from {request.user}")` and reload while logged in
   vs logged out. Notice how the *same* view produces different output from the *same* URL,
   because the request differs.

**Check yourself:**
- What two things does every view receive and return?
- Why must writes be POST and not GET?
- Why did adding `ping` require edits in *three* files, and what does each edit accomplish?

---

### LEARN-05 — Templates (the "T") & template inheritance

**Concept:**
A **template** is an HTML file with a small embedded language, the Django Template Language (DTL),
that lets you inject data and do light logic while rendering. The philosophy is deliberate:
templates are for *display only*. They should print values the view already computed and loop over
data the view already fetched — but they should not run database queries or make business
decisions. Keeping logic out of templates is what makes the display layer swappable and the logic
testable.

DTL has two kinds of syntax. `{{ something }}` **outputs a value** — it evaluates the expression
and prints it into the HTML (and, importantly, auto-escapes it to prevent injection attacks —
more in LEARN-25). `{% tag %}` **runs a template tag** — control-flow and utilities like
`{% if %}`, `{% for %}`, `{% url %}`, and `{% csrf_token %}`. A loop like
`{% for booking in bookings %} ... {% empty %} ... {% endfor %}` iterates a list and provides a
graceful fallback when it's empty — much cleaner than the manual "if empty" checks you'd write in
raw code.

The feature that makes a multi-page site maintainable is **template inheritance**. Instead of
copying the header, nav, and footer into every page, you define a `base.html` with named "holes"
(`{% block content %}{% endblock %}`), and each page `{% extends "scheduling/base.html" %}` and
fills only its block. Change the nav once in `base.html` and every page updates. This is the DRY
principle (Don't Repeat Yourself) applied to HTML.

**Look at:** `scheduling/templates/scheduling/base.html`,
`scheduling/templates/scheduling/student_booking_list.html`,
`scheduling/templates/scheduling/teacher_dashboard.html`.

**Principles:**
- **`{{ }}` prints, `{% %}` does.** Values go in double braces; logic and utilities go in
  brace-percent tags. Mixing them up is the most common template syntax error.
- **Templates are display-only — no queries, no rules.** If you find yourself wanting to compute a
  total or filter a list inside a template, stop: do it in the view and pass the result in via
  context. This keeps logic in one testable place and templates dumb-but-safe.
- **Inheritance eliminates duplication.** `base.html` holds the shared skeleton; children fill
  blocks. This is why every page in this app shares one navigation bar and one message area — they
  all extend the same base.
- **Always link via `{% url 'name' %}`, never a literal path.** Same reasoning as LEARN-03:
  hardcoded URLs rot. The `{% url %}` tag resolves names to paths at render time.
- **The context dict is the only data a template should see.** A template can't "reach out" and
  fetch more; it can only display what the view chose to pass. That constraint is a feature — it
  forces a clean boundary between logic and presentation.

**Do:**
1. In `student_booking_list.html`, find the loop that lists bookings.
2. Inside the loop, add a line that prints each booking's status next to its title.
3. Add an `{% empty %}` clause that says "You have no bookings yet." Test it by cancelling all
   your bookings, then rebooking one to see the loop populate again.

**Check yourself:**
- What's the difference between `{{ }}` and `{% %}`?
- What does `{% extends %}` do, and where exactly does a child template's content end up?
- Why is it a design *feature* that a template can only see the context the view passes it?

---

### LEARN-06 — Models (the "M") & your first migration

**Concept:**
A **model** is a Python class that represents a table in your database. Each class attribute is a
column, and each *instance* of the class is a row. Instead of writing SQL like `CREATE TABLE` and
`INSERT INTO`, you write a Python class and let Django translate. This is the heart of the ORM
(Object–Relational Mapper), which you'll query in LEARN-08. Right now the focus is *defining* the
shape of your data.

You declare fields by assigning field objects: `CharField` (short text, needs `max_length`),
`TextField` (long text), `IntegerField`/`PositiveIntegerField`, `BooleanField`, `DateTimeField`,
`DateField`, `URLField`, and relationship fields like `ForeignKey`. Each field type maps to a
database column type and also controls how forms and the admin render it. Field *options* refine
behavior: `default=` sets a value when none is given, `choices=` restricts to a fixed set,
`blank=True` makes it optional in forms, and `null=True` allows the database column to hold NULL.

Because your database already has tables full of data, you can't just change a class and expect the
database to reshape itself. That's what **migrations** are for: they are the version control of
your schema. The workflow is two steps. First, `makemigrations` inspects your models, compares them
to the last known state, and writes a migration file describing the change (add a column, create a
table, etc.). Second, `migrate` runs those migration files against the actual database. Migration
files live in each app's `migrations/` folder and are committed to git alongside the model change —
they are how every developer (and production) arrives at the same schema.

Two habits worth building now: always define a `__str__` method (it controls how objects appear in
the admin and shell — "Booking object (1)" is useless; "alex - Intro Math - confirmed" is
readable), and use `class Meta: ordering = [...]` to give queries a sensible default order.

**Look at:** `scheduling/models.py` — read the whole file. It is the complete data schema of the
app, and every other layer ultimately serves this data.

**Principles:**
- **A model is a table; an attribute is a column; an instance is a row.** Hold this mapping in your
  head and models stop feeling abstract.
- **Migrations are database version control — never skip them.** Edit `models.py`, then
  `makemigrations` (Django writes the change) then `migrate` (Django applies it). The generated
  file is real code you can (and should) read; it demystifies what Django is doing.
- **Commit the migration with the model change, in the same commit.** They're a matched pair.
  A model change without its migration will break every other environment.
- **`blank` and `null` are different axes.** `blank=True` is about *form/validation* ("this field
  may be left empty in a form"). `null=True` is about the *database* ("this column may store
  NULL"). For text fields Django convention is to use `blank=True` but *not* `null=True` (store an
  empty string, not NULL). For non-text optional fields you often need both.
- **Always define `__str__`, and set `Meta.ordering`.** The first makes debugging humane; the
  second means your lists come out in a predictable order without every query having to say so.
- **Field options are your validation and defaults layer.** `choices` gives you a dropdown and
  guards against typos; `default` prevents "missing value" errors; `max_length` protects the
  column. Choosing these well up front saves bugs later.

**Do:**
1. Add a field to `CurriculumItem`:
   ```python
   estimated_minutes = models.PositiveIntegerField(default=15)
   ```
2. Run `python manage.py makemigrations` and *open the generated file* in `scheduling/migrations/`.
   Read it — notice Django wrote an `AddField` operation for you.
3. Run `python manage.py migrate` to apply it.
4. Confirm in the shell:
   ```python
   from scheduling.models import CurriculumItem
   CurriculumItem._meta.get_field('estimated_minutes')
   ```

**Check yourself:**
- Describe the two-command flow after editing a model, and what each command does.
- Explain the difference between `blank=True` and `null=True` with an example of each.
- Why must migration files be committed to git along with the model change?

---

### LEARN-07 — The Django admin (free CRUD UI)

**Concept:**
One of Django's signature features is that it generates a complete administrative interface for
your data automatically. The moment you register a model in `admin.py`, you get a polished web UI
at `/admin/` to create, read, update, and delete rows of that model — no HTML, no forms, no views
to write. This is enormously useful during development: it's the fastest way to inspect what's
actually in your database, fix bad data by hand, and create test records.

It's important to understand *who the admin is for*. It is a **staff-facing** tool — for you, the
developer, and trusted internal users. It is emphatically **not** the interface your students and
teachers use; they use the templates and the React app you built. Access is gated by the `is_staff`
flag on a user, and you create your first admin account with `createsuperuser`.

The admin is also customizable. The bare `admin.site.register(Model)` gives you the defaults, but
you can register a `ModelAdmin` subclass to control the experience: `list_display` chooses which
columns show in the list view, `search_fields` adds a search box, and `list_filter` adds sidebar
filters. A few lines of `ModelAdmin` config can turn a barely-usable list into a genuinely
powerful data browser.

**Look at:** `scheduling/admin.py`, `progress/admin.py`.

**Principles:**
- **Registering a model unlocks full CRUD for free.** This is Django's "batteries included"
  philosophy at its best — you get a real back office without building one.
- **The admin is for staff, not end users.** Never point customers at `/admin/`. It exposes raw
  data and destructive operations; it assumes a trusted operator. End-user flows go through your
  own views and API.
- **`ModelAdmin` turns the default into a tool.** `list_display` (columns), `search_fields`
  (search box), and `list_filter` (sidebar filters) are the three you'll reach for constantly.
  Investing a few lines here makes managing data dramatically faster.
- **The admin respects your models.** `__str__`, `choices`, and field types all shape how the
  admin renders — another reason LEARN-06's habits pay off. A good `__str__` makes admin dropdowns
  and lists readable.

**Do:**
1. If you don't have a superuser yet: `python manage.py createsuperuser`.
2. Visit `/admin/`, open `Curriculum items`, and edit the `estimated_minutes` value you added in
   LEARN-06.
3. Upgrade the CurriculumItem registration in `scheduling/admin.py` to a `ModelAdmin`:
   ```python
   @admin.register(CurriculumItem)
   class CurriculumItemAdmin(admin.ModelAdmin):
       list_display = ('title', 'estimated_minutes', 'is_published')
       list_filter = ('is_published',)
       search_fields = ('title',)
   ```
   Reload the list page and try the new columns, filter, and search.

**Check yourself:**
- Who is the admin intended for, and who should *never* use it?
- What do `list_display`, `list_filter`, and `search_fields` each add?
- Why does a good `__str__` improve the admin experience specifically?

---

### LEARN-08 — The ORM: querying without SQL

**Concept:**
The **ORM** is the layer that lets you read and write the database using Python objects and method
calls instead of raw SQL. Where a database person writes `SELECT * FROM scheduling_session WHERE
status = 'open'`, you write `Session.objects.filter(status='open')`. The ORM translates your Python
into SQL, runs it, and hands back model instances. This keeps your code in one language, guards
against SQL injection automatically (LEARN-25), and works across database backends (this app uses
Postgres in dev and SQLite in tests without changing a line of query code).

Every model has a **manager**, accessed as `Model.objects`, which is your entry point for queries.
The core methods return **QuerySets** — lazy, chainable representations of a database query.
"Lazy" is a key word: `Session.objects.filter(status='open')` doesn't actually touch the database
yet. The query runs only when you *use* the result — iterate over it in a loop, call `len()`/`count()`,
index it, or convert it to a list. This laziness lets you build up complex queries by chaining
(`.filter(...).exclude(...).order_by(...)`) with only one database hit at the end.

Two ORM concepts unlock most real work. **Field lookups** use the double-underscore syntax to
express conditions beyond equality: `start_time__gte=now` means "start_time >= now,"
`title__icontains='math'` means "title contains 'math', case-insensitive." You can even traverse
relationships in a lookup: `filter(session__teacher=user)` filters bookings by the teacher of
their session. And **reverse relations via `related_name`**: because `Booking.session` is a
`ForeignKey(Session, related_name='bookings')`, you can navigate both directions —
`booking.session` gives you the session, and `session.bookings.all()` gives you every booking for
that session. The `related_name` is the label for that reverse trip.

**Look at:** `scheduling/services/booking.py` (real queries in context), and use
`python manage.py shell` to experiment live.

**Principles:**
- **`Model.objects` is the door to the database.** Learn the core methods cold: `.all()`,
  `.filter()`, `.exclude()`, `.get()`, `.first()`, `.count()`, `.exists()`, and `.create()`.
- **`.get()` vs `.filter().first()` is a real distinction.** `.get(pk=1)` returns exactly one
  object but *raises an exception* if it finds zero (`DoesNotExist`) or more than one
  (`MultipleObjectsReturned`). `.filter(...).first()` returns the first match or `None`, never
  raising. Use `.get()` when you're sure it exists and want the error otherwise; use
  `.filter().first()` when "not found" is a normal case you'll handle.
- **QuerySets are lazy — build now, hit the DB once, later.** Chaining filters doesn't run
  multiple queries; the SQL is assembled and executed only when the results are consumed. This is
  why you can pass QuerySets around and refine them cheaply.
- **`related_name` gives you the reverse relationship.** A `ForeignKey` connects two models; the
  `related_name` is how you traverse it backwards. `session.bookings.all()` exists *because* the
  FK declared `related_name='bookings'`. Design these names to read naturally.
- **The `__` (double underscore) is "reach into."** It expresses comparisons (`__gte`, `__lte`,
  `__icontains`, `__in`) and relationship traversal (`session__teacher`). Once this clicks, you can
  express almost any query without SQL.
- **`.exists()` and `.count()` are cheaper than loading objects.** When you only need to know
  "is there any?" or "how many?", use these instead of fetching full rows — the booking service
  uses exactly this pattern to check capacity and duplicates efficiently.

**Do (in `python manage.py shell`):**
1. ```python
   from scheduling.models import Session, Booking
   from django.utils import timezone
   Session.objects.count()
   Session.objects.filter(status='open').count()
   s = Session.objects.first()
   s.bookings.all()                          # reverse relation via related_name
   Session.objects.filter(start_time__gte=timezone.now())   # field lookup
   Booking.objects.filter(session__teacher=s.teacher)       # traverse a relationship
   ```
2. Now re-read `can_book()` in `services/booking.py` and identify *every* ORM call it makes. You
   should be able to explain each one — capacity check, duplicate check, timing check — in terms
   of the methods and lookups above.

**Check yourself:**
- When would you choose `.get()` over `.filter().first()`, and what happens in the failure case for each?
- What does "QuerySets are lazy" mean, and why is it useful?
- Explain `related_name` using `session.bookings.all()` as your example.
- What does `start_time__gte=now` translate to, and why is `session__teacher=user` a legal filter?

---

# WEEK 2 — Real app patterns (how *this* app is built)

Goal: forms, users/roles, the service layer, and testing — the patterns that separate a
tutorial toy from a maintainable app.

---

### LEARN-09 — Forms & ModelForms

**Concept:**
Any time users send data to your server — creating a session, updating a profile — you need to
**validate** it before trusting it. Never assume input is well-formed; users mistype, and
attackers lie. Django's **forms** framework is the disciplined answer. A form declares the fields
you expect, checks incoming data against rules, converts strings into proper Python types (a date
input becomes a `datetime`), and collects human-readable error messages when something's wrong.

The special case you'll use most is the **`ModelForm`**, which builds a form automatically from a
model. Just as the admin derives its editing UI from your models, a `ModelForm` derives its fields
from a model via `class Meta: model = Session; fields = [...]`. This means you describe your data
once (in the model) and get form validation almost for free. `SessionForm` in this app is exactly
this.

The view-side pattern is worth memorizing because you'll write it constantly:
`form = SessionForm(request.POST or None)` creates a form — bound to submitted data on a POST,
empty on a GET. Then `if form.is_valid():` runs all the validation; if it passes, `form.save()`
writes to the database (for a `ModelForm`), and if it fails, `form.errors` holds what went wrong
and the template re-renders with those messages. Crucially, **validation lives in the form**, not
scattered across the view or template. And every HTML form that POSTs must include
`{% csrf_token %}` (LEARN-25 explains why) or Django will reject it.

Forms are also customizable at construction time. This app's `SessionForm` overrides `__init__` to
filter the `class_type` dropdown so a teacher only sees *their own* class types — a good example of
tailoring a form to the current user.

**Look at:** `scheduling/forms.py`, `scheduling/views/teacher.py` (forms in use),
`scheduling/templates/scheduling/create_session.html`.

**Principles:**
- **Validate all input — forms are the front line.** The rule is "never trust the client."
  A form is where you enforce that trust boundary before data reaches your models.
- **`ModelForm` = a form generated from a model.** Declare `model` and `fields` in `Meta` and you
  get fields, widgets, and validation matched to your schema, with `.save()` writing straight to
  the DB. It's the form counterpart to the admin's auto-UI.
- **Memorize the on-POST view pattern:** build the form with the submitted data, call
  `is_valid()`, then either `save()` + redirect (success) or re-render with `form.errors`
  (failure). This "bound form" loop is the backbone of every write-through-a-form feature.
- **Validation belongs in the form, in one place.** Field-level checks come from field options;
  cross-field checks go in a `clean()` method. Keeping them in the form (not the view/template)
  means one place to find and test the rules.
- **`{% csrf_token %}` is mandatory in every POST form.** Omit it and Django returns a 403. It's
  not optional decoration — it's the anti-CSRF protection (LEARN-25).
- **Forms can adapt to the user.** Overriding `__init__` to limit choices (as `SessionForm` does
  for class types) is a clean way to make a form context-aware without leaking logic into the view.

**Do:**
1. Read `SessionForm` and trace how `teacher_create_session` constructs it, validates it, and
   saves it.
2. Add a cross-field rule: give `SessionForm` a `clean()` method that raises
   `forms.ValidationError('End time must be after start time.')` when `end_time <= start_time`.
   Then try to create an invalid session in the browser and watch the error render.

**Check yourself:**
- Why should validation live in the form rather than the view or template?
- Describe the full on-POST view pattern for a form, step by step.
- What happens if you forget `{% csrf_token %}`, and why does that protection exist?

---

### LEARN-10 — Users & authentication

**Concept:**
**Authentication** is the process of establishing *who a user is*. Django ships a complete,
battle-tested auth system so you never have to build (or get wrong) the dangerous parts yourself:
a `User` model, secure password hashing, login/logout flows, session management, and password-reset
plumbing. Reusing this is not laziness — hand-rolled auth is a classic source of catastrophic
security bugs.

The single most useful object is `request.user`. On *every* request, Django attaches the current
user here. If someone is logged in, it's their `User` instance; if not, it's a special
`AnonymousUser` object (which answers `False` to `is_authenticated`). Your views and templates
lean on this constantly to decide what to show and what to allow.

To protect a view, you use the `@login_required` decorator. It checks `request.user`; if the user
is anonymous, it redirects them to the login page instead of running the view. This is
*authentication* enforcement — "you must be someone." (It's distinct from *authorization* — "you
must be allowed" — which is LEARN-11.) The login/logout pages themselves come from
`path('accounts/', include('django.contrib.auth.urls'))`, which wires up Django's built-in auth
views for free.

The most security-critical detail: **passwords are never stored in plain text.** Django stores a
salted hash. You set a password with `user.set_password(raw_password)` (which hashes it) followed
by `user.save()`, and you verify one with `user.check_password(raw_password)` (which hashes the
input and compares). You used exactly this pair when we built the `/api/me/password/` change-password
endpoint. Directly assigning `user.password = "..."` would store an unusable plaintext string and
break login — always go through `set_password`.

**Look at:** `config/urls.py` (`accounts/` include), `scheduling/views/common.py`, any view
decorated with `@login_required`, and the password logic in `scheduling/api/serializers.py`.

**Principles:**
- **Use Django's auth system; don't reinvent it.** Password hashing, session handling, and reset
  flows are easy to get subtly, dangerously wrong. The built-ins are audited and free.
- **`request.user` is always present.** It's either a real `User` or `AnonymousUser`. Check
  `request.user.is_authenticated` rather than testing for `None`.
- **`@login_required` enforces *authentication*, not permission.** It answers "are you logged in?"
  and redirects anonymous users to login. It does *not* check roles — that's the next ticket.
- **Passwords are hashed, one-way.** `set_password()` to store, `check_password()` to verify. You
  can never retrieve the original password (that's the point). Assigning `.password` directly
  bypasses hashing and breaks auth.
- **The `accounts/` include gives you login/logout/reset for free.** Wiring one `include()` line
  gets you Django's full suite of auth views — another batteries-included win.

**Do:**
1. Add `@login_required` to your `ping` view. Log out, hit `/ping/`, and observe the redirect to
   login. Log back in and confirm it works again.
2. In the shell, inspect users:
   ```python
   from django.contrib.auth import get_user_model
   User = get_user_model()
   list(User.objects.values_list('username', 'is_staff', 'is_superuser'))
   ```

**Check yourself:**
- What is `request.user` when nobody is logged in, and how do you test for "logged in"?
- What does `@login_required` do, and what does it *not* do?
- How are passwords stored, and which two methods do you use to set and verify them?

---

### LEARN-11 — Groups & role-based authorization

**Concept:**
It's essential to separate two ideas that sound similar. **Authentication** (LEARN-10) answers
*"who are you?"* **Authorization** answers *"what are you allowed to do?"* A logged-in student and
a logged-in teacher are both authenticated, but they're authorized for very different actions.
Getting this distinction wrong is how apps accidentally let students edit other people's data.

This app models roles using Django **Groups** — named buckets you assign users to. There are three:
`student`, `teacher`, and `staff`. A user's group membership determines their capabilities. You
check membership with `user.groups.filter(name='teacher').exists()` — this asks the database
"is this user in the teacher group?" and returns a boolean.

Because that check would otherwise be copy-pasted into dozens of views, the app centralizes it in
`scheduling/views/common.py` with helpers like `user_in_group()` and `require_group()`. This is the
**DRY** principle (Don't Repeat Yourself) applied to authorization: one function encodes "must be a
teacher," and every teacher-only view calls it. If the rule ever changes, you change it once.

There's also a correctness nuance in *how* you refuse access. If a user isn't logged in at all, the
right response is to redirect them to login (an *authentication* failure — "become someone").
If a user *is* logged in but lacks the role, the right response is `HttpResponseForbidden` — HTTP
403 (an *authorization* failure — "you're someone, just not someone allowed"). Using the correct
response makes the app's behavior clear and correct.

Where do the groups come from? They're created by a **management command**,
`bootstrap_sandbox` (in `scheduling/management/commands/`). Management commands are custom
`manage.py` subcommands you write — great for setup, seeding demo data, and batch jobs. Reading
this one shows you both how groups are created and how the demo users are assigned to them.

**Look at:** `scheduling/views/common.py` (`user_in_group`, `require_group`),
`scheduling/services/booking.py` (role checks inside the rules),
`scheduling/management/commands/bootstrap_sandbox.py` (groups + demo users created).

**Principles:**
- **Authentication ≠ authorization.** "Who are you" and "what may you do" are different questions
  with different enforcement. Always ask which one a given check is really about.
- **Roles here are Django Groups, checked with `user.groups.filter(name=...).exists()`.** This is
  the app's single convention for "is this user a teacher/student/staff?" Learn to spot it.
- **Centralize the check (DRY).** `require_group()` exists so the role logic isn't scattered.
  Duplicated authorization is dangerous: miss one copy and you've got a security hole. One helper,
  many callers.
- **Use the right refusal: 403 vs redirect.** Logged-in-but-forbidden → `HttpResponseForbidden`
  (403). Not-logged-in → redirect to login. Choosing correctly communicates intent and avoids
  confusing "why am I at the login page?" behavior for users who are already signed in.
- **Management commands automate setup and chores.** `bootstrap_sandbox` creates groups and demo
  data reproducibly. Any repeatable operational task (seeding, syncing, backfilling) is a good
  candidate for a custom command rather than a one-off script.

**Do:**
1. Trace how `student_session_list` guarantees only students reach it, following the call into
   `common.py`.
2. Make your `ping` view teacher-only using `require_group`. Test the outcome as `demo_student`
   (should be forbidden — a 403) versus `demo_teacher` (should succeed). Notice the *difference*
   from LEARN-10, where logging out sent you to login instead.

**Check yourself:**
- Give a one-sentence definition of authentication and of authorization, and an example of each from this app.
- How does this app represent and check roles?
- Why is centralizing the group check a *security* concern, not just tidiness?
- When should a refused request return 403 versus redirect to login?

---

### LEARN-12 — The service layer (where business logic lives)

**Concept:**
This is the most important architectural idea in the whole app, so read slowly. A **service layer**
is a set of plain Python functions that contain your **business rules** — the domain logic that
defines what your app actually *means* ("a student may book a session only if they have an active
membership, the session is open and in the future, there's capacity, and they haven't already
booked it"). These functions live in `scheduling/services/` (and `progress/services.py`),
completely separate from views, templates, and API code.

Why go to this trouble? Because this app has **two front-ends over one backend**: the Django
templates website and the React SPA (which talks to the DRF API). Both let a student book a
session. If the booking rules lived inside the HTML view, the API would either duplicate them
(and inevitably drift out of sync — someone fixes a bug in one place and forgets the other) or
skip them (a security hole). By putting the rules in `create_booking()` and having *both* the HTML
view *and* the API view call that same function, the rules can only exist in one place. Change them
once, and every UI is instantly consistent.

Look at the shape of `booking.py`: `can_book(user, session)` returns a boolean encoding *all* the
rules, and `create_booking(user, session)` calls `can_book` and, if allowed, performs the write
and fires the confirmation email. This separation — a "can I?" predicate plus a "do it" action — is
a clean, testable pattern. The functions take explicit inputs, return clear results, and make side
effects (like sending mail) obvious rather than hidden.

The payoff is enormous and shows up in three places you already care about. **Testing:** you can
test `can_book` directly, fast, without HTTP (LEARN-16). **Consistency:** the website and API can
never disagree about the rules. **Maintainability:** when a rule changes, you touch one function,
not a dozen views. This is the rule `CLAUDE.md` states as law: *views and serializers stay thin;
business logic lives in services.*

**Look at:** `scheduling/services/booking.py`, `membership.py`, `availability.py`,
`notifications.py`, `payments.py`, `progress/services.py`. Then look at *two callers of the same
logic*: `scheduling/views/student.py` (the website) and `scheduling/api/views.py` (the API).

**Principles:**
- **Business rules go in services — this is the app's core rule.** Views (HTML and API) coordinate
  and translate HTTP; services decide. If you're writing an `if` that encodes a domain rule inside
  a view, it probably belongs in a service.
- **One rule, one place, many callers.** The entire justification is avoiding duplication and
  drift. The website and React both call `create_booking`, so booking rules can't diverge between
  them. This is DRY applied to your most important logic.
- **The "predicate + action" shape is clean and testable.** `can_book()` answers a yes/no question
  with no side effects; `create_booking()` performs the change. Splitting them lets you test the
  decision independently and reuse the predicate (e.g. to disable a button in the UI).
- **Side effects should be explicit.** `create_booking` visibly calls `send_booking_confirmation`.
  Because the service is the one place the action happens, the email can't be forgotten by one UI
  and remembered by another.
- **Thin views are a *consequence* of a good service layer.** When rules live in services, views
  shrink to "gather input → call service → respond." Fat views are a symptom that logic leaked out
  of the service layer.
- **Ideal blast radius for a rule change is one function.** If changing "can a student book?"
  forces edits in the HTML view, the API view, *and* a test in three different styles, your logic
  is in the wrong place.

**Do:**
1. Read `can_book()` line by line and write out, in plain English, every distinct rule it enforces
   (there are several). This is the domain model of "booking" in words.
2. Add a new rule *in the service*: a student may hold at most 3 confirmed bookings at once.
   Implement it inside `can_book()` — not in any view. Then verify the payoff: test booking a 4th
   session both on the website *and* via the API booking endpoint. Both should refuse it, because
   both call the same service. That single-edit, everywhere-consistent result is the whole point.

**Check yourself:**
- Why is putting logic in a service better than putting it in the view, given this app has two UIs?
- If a booking rule changes, how many functions should ideally change, and why?
- Name the two callers of `create_booking` and explain how they stay consistent.
- What's the benefit of splitting `can_book` (predicate) from `create_booking` (action)?

---

### LEARN-13 — Messages framework & the POST→redirect→GET pattern

**Concept:**
Here's a problem every web app faces: a user submits a form (a POST), you process it, and now you
need to show them the result. If you simply *render* a page in response to that POST, the browser's
URL still points at the POST endpoint — so if the user refreshes, the browser re-submits the form,
and they accidentally book the same session twice. The fix is a discipline called
**POST → Redirect → GET (PRG)**: after handling a POST successfully, don't render — issue a
`redirect()` to a normal GET page. The browser follows the redirect, lands on a safe GET URL, and a
refresh just reloads that harmless page.

But a redirect throws away the page you were about to render, so how do you tell the user "Booked!"?
That's what Django's **messages framework** is for. You queue a one-time message with
`messages.success(request, "Booked!")` (or `.error`, `.info`, `.warning`), issue your redirect, and
on the *next* page the base template loops over the queued messages and displays them. They're
"flash" messages: shown exactly once, then gone — refresh again and they've cleared. This gives you
the clean "do the thing, bounce to a safe page, confirm what happened" flow that feels right to
users.

Notice how this ties together earlier tickets: the redirect target is a URL **name** (LEARN-03),
the display happens in the shared **base template** (LEARN-05), and the actual work is done by a
**service** (LEARN-12) before the message is queued. PRG is where routing, templates, and services
meet in a single user interaction.

**Look at:** `scheduling/views/student.py` (`student_book_session`, `student_cancel_booking`),
`scheduling/templates/scheduling/base.html` (where messages render).

**Principles:**
- **After a successful POST, redirect — never render.** This prevents the duplicate-submission bug
  on refresh and keeps the browser's URL pointing at a safe, reloadable GET page. It's a reflex to
  build.
- **Flash messages carry feedback across the redirect.** `messages.success/error/info/warning`
  queue a message that survives exactly one redirect and displays once. They're the standard way to
  say "it worked" or "that failed" after a PRG bounce.
- **Redirect by URL name.** `redirect('student_booking_list')` uses the name from `urls.py`, so it
  keeps working even if the path string changes — same reasoning as `{% url %}`.
- **Messages render in one shared place.** Because the base template displays them, *any* view can
  flash a message and it shows up consistently, without per-page wiring. That's template inheritance
  paying off.
- **PRG is the meeting point of the layers.** A single booking exercises routing (the redirect
  name), the service (the actual booking), messages (the feedback), and templates (the display).
  Understanding it means you understand how the pieces cooperate.

**Do:**
1. Follow one complete booking in the code: form POST → `create_booking` service call →
   `messages.success(...)` → `redirect(...)` → the message appearing on the next page.
2. Add a `messages.info(request, "Tip: check your inbox for confirmations.")` somewhere sensible,
   confirm it appears once, then refresh and confirm it's gone.

**Check yourself:**
- Why is rendering directly in response to a POST a bug waiting to happen?
- How long does a flashed message live, and where is it displayed?
- Which earlier concepts (name three) does a single PRG interaction rely on?

---

### LEARN-14 — Settings & environment variables

**Concept:**
Some configuration must differ between your laptop and a production server: the secret key, whether
debug mode is on, which database to use, allowed hostnames, email credentials. Hardcoding these in
`settings.py` is both insecure (secrets end up in git) and inflexible (you can't have different
values per environment without editing code). The professional solution is **environment
variables**: `settings.py` reads values from the environment (via a `.env` file in development),
so the *same code* behaves correctly in every environment just by changing the environment.

Two settings deserve special fear. `DEBUG` must be `True` only in development — it enables detailed
error pages that expose your source code, settings, and even parts of your database on any
exception. Shipping `DEBUG=True` to production is a serious, common security incident. And
`SECRET_KEY` is used to sign sessions, password-reset tokens, and more; it must be unique,
unpredictable, and never committed. Both come from the environment here.

The convention this app follows: a `.env.example` file is committed to git to *document* every
variable the app understands (with placeholder values), while the real `.env` holding actual secrets
is gitignored and never shared. A new developer copies `.env.example` to `.env` and fills in real
values. You'll also see environment-awareness in the database config: Postgres for development and
production, but the fast in-memory-ish SQLite for the automated test runner, chosen automatically.

**Look at:** `config/settings.py`, `.env.example`.

**Principles:**
- **Environment-specific config comes from the environment, not the code.** Same `settings.py`,
  different `.env` per machine. This is the "twelve-factor app" idea and it's how real deployments
  stay both secure and flexible.
- **`DEBUG=False` in production, always.** Debug pages leak source, settings, and query details to
  anyone who triggers an error. This is one of the highest-severity misconfigurations in web dev.
- **`SECRET_KEY` is a real secret.** It signs security-sensitive tokens. Keep it in the environment,
  make it unique per deployment, and never let it touch git.
- **`.env.example` documents; `.env` holds secrets and is gitignored.** The example file is the
  contract ("here's every knob"); the real file is the private configuration. This lets you share
  *what* is configurable without sharing the values.
- **Different environments can use different backends.** Postgres in dev/prod for realism, SQLite
  for tests for speed. The query code doesn't change — that's the ORM's portability (LEARN-08) at
  work.

**Do:**
1. Pick three settings in `settings.py` that read from the environment and find their matching
   entries in `.env.example`. Understand the round trip: example documents it → your `.env` sets it
   → `settings.py` reads it.
2. Find the code that decides Postgres vs SQLite and explain, in your own words, exactly when each
   is used.

**Check yourself:**
- Why is `DEBUG=True` in production dangerous — specifically, what does it expose?
- Why keep `SECRET_KEY` and passwords in `.env` rather than `settings.py`?
- What is the purpose of `.env.example` if it contains no real secrets?

---

### LEARN-15 — Static files, the base template & the two front-ends

**Concept:**
**Static files** are the assets that don't change per request: CSS, JavaScript, images, fonts.
Django treats them specially because *how* they're served differs sharply between development and
production. In development, `runserver` conveniently serves them for you automatically. In
production, you don't want your Python app spending time serving CSS — so you run
`collectstatic`, which gathers every app's static files into one directory, and let **WhiteNoise**
(a piece of middleware) serve them efficiently with caching headers. Same files, very different
delivery.

This ticket is also the moment to fully grasp the app's **dual-UI architecture**, documented in
`CLAUDE.md`. There are *two independent front-ends* sitting on top of one Django backend. The first
is the classic **Django templates** website — server-rendered HTML, styled by Django's static
files, authenticated by sessions/cookies. The second is the **React SPA** in `frontend/`, a
separate JavaScript app with its *own* build system and its *own* stylesheet
(`frontend/src/index.css`), authenticated by JWT (LEARN-20). They share the database and the
service-layer rules, but they do *not* share HTML or CSS.

This is why, in this ticket's exercise, editing a Django template's footer will change the
templates site but have zero effect on the React app — and vice versa. Understanding that these are
two distinct presentation layers over a shared core prevents a lot of confusion ("I changed the CSS,
why didn't the React page update?").

**Look at:** `scheduling/templates/scheduling/base.html`, the `STATIC_URL`/`STORAGES` settings in
`config/settings.py`, and `frontend/src/index.css` for the React side.

**Principles:**
- **Static files are served differently in dev vs prod.** `runserver` does it automatically in dev;
  production uses `collectstatic` + WhiteNoise. Knowing this prevents the classic "my CSS works
  locally but 404s in production" surprise.
- **`collectstatic` + WhiteNoise is the production static story.** One command gathers assets;
  WhiteNoise serves them with proper caching so your Python workers aren't wasted on static files.
- **One base template = one consistent shell.** Nav, message display, footer — define them once in
  `base.html` and every templates page inherits them. This is LEARN-05's inheritance in its most
  valuable role.
- **This app has two front-ends over one backend.** Templates (session auth, Django static files)
  and React (JWT, its own CSS/build). They share data and service rules, not presentation. Keep the
  two mental models separate.
- **A change only affects the layer you changed.** Template edits touch the templates site; React
  edits touch the SPA. If you want a change in both, you make it in both — there's no shared HTML.

**Do:**
1. Add a footer to `base.html` (e.g. "Booking Studio — learning build") and confirm it appears on
   every templates page you visit.
2. Note that the React app (`:5173`) is unchanged by that edit. Articulate *why* — which layer did
   you touch, and which layer is React?

**Check yourself:**
- Who serves static files in development, and who serves them in production?
- What does `collectstatic` do, and why does production want WhiteNoise?
- Why do edits to a Django template not change the React app?

---

### LEARN-16 — Testing (prove your rules work)

**Concept:**
Manual clicking proves a feature works *right now, for the one path you tried*. Automated **tests**
prove it works *repeatedly, for many paths, forever* — and, more importantly, they catch
**regressions**: the moment a future change silently breaks existing behavior. In an app with
interlocking rules (booking depends on membership, capacity, timing, roles), tests are what let you
change code confidently instead of fearfully.

Django makes testing first-class. `python manage.py test` spins up a *separate, throwaway* test
database (so your real data is never touched), runs every test, and tears the database down
afterward. This app is configured to use fast SQLite for tests specifically so the suite runs
quickly (LEARN-14).

The highest-value place to test is your **service layer** (LEARN-12), because that's where the
rules live. A service test needs no HTTP at all: create some users and sessions in the test, call
`can_book(...)` directly, and assert it returns what you expect. This is fast and precise. You can
*also* test the API end-to-end using DRF's test client with a JWT — there's already a smoke test
that does this. Every good test follows the same three-beat rhythm, often called
**Arrange–Act–Assert**: *arrange* the data and preconditions, *act* by calling the thing under
test, *assert* that the result matches expectations.

**Look at:** `scheduling/tests.py`.

**Principles:**
- **Tests catch regressions; that's their superpower.** They don't just verify today's code — they
  guard against tomorrow's accidental breakage. A rule worth having is a rule worth testing.
- **`manage.py test` uses a disposable test database.** Your development data is safe; each run
  starts clean. This is why tests can freely create and delete objects.
- **Test services hardest.** The service layer holds the rules, so testing it gives the most
  coverage per line of test. Testing `can_book` directly is faster and more focused than driving
  the whole website to check the same rule.
- **Follow Arrange–Act–Assert.** Set up the world, perform one action, check one outcome. Tests
  that do this are readable and pinpoint failures precisely.
- **Test the true edges, not just the happy path.** The valuable cases are the boundaries: exactly
  at capacity, a duplicate booking, a session in the past, a student without membership. Bugs live
  at edges.

**Do:**
1. Read the existing booking, membership, and ICS tests to absorb the style and the AAA rhythm.
2. Write a test for the "max 3 bookings" rule you added in LEARN-12: *arrange* a student with 3
   confirmed bookings, *act* by calling `can_book` for a 4th session, *assert* it returns `False`.
   Run `python manage.py test` and watch it pass (or fail, if your rule has a bug — either way you
   learned something).

**Check yourself:**
- Why are automated tests more valuable than manual clicking, especially over time?
- Why test the service layer rather than only the website UI?
- Name the three phases of a well-structured test and what each does.

---

### LEARN-17 — Migrations, deeper

**Concept:**
You met migrations in LEARN-06 as "the two commands you run after changing a model." Now go one
level deeper. Each migration is a Python file in an app's `migrations/` folder, and they form an
*ordered, dependency-linked chain* — migration `0006` declares that it depends on `0005`, and so
on. Django tracks which migrations a given database has already applied (in a hidden table), so it
knows exactly which ones still need to run. This is what lets a brand-new database and a
months-old production database both arrive at the identical current schema by replaying the chain.

There are two flavors of migration, and the distinction matters. A **schema migration** changes the
*structure* of the database — adding a column, creating a table, changing a field type. These are
what `makemigrations` writes automatically when you edit `models.py`. A **data migration** changes
the *contents* — backfilling a new column with computed values, transforming existing rows,
splitting data between tables. Data migrations are written by hand using a `RunPython` operation
that calls a Python function you provide. You need them whenever a structural change requires
existing rows to be updated too (e.g., you add a `estimated_minutes` column and want to set a
sensible value on the thousands of rows that already exist).

A few operational commands round out your toolkit: `makemigrations` writes migrations, `migrate`
applies them, `showmigrations` lists each migration with a checkbox showing whether it's applied,
and `migrate app_label 0004` can *roll back* to a specific point (powerful but use with care on
real data). And the cardinal rule: commit each migration together with the model change that
produced it, so history stays coherent for everyone.

**Look at:** `scheduling/migrations/` — open a couple of the numbered files and read the
`operations` list.

**Principles:**
- **Migrations are an ordered, dependency-linked chain.** Each depends on the previous; Django
  replays the unapplied ones to bring any database up to date. Don't casually reorder or hand-edit
  already-applied migrations — you'll break that chain.
- **Schema vs data migration is a real distinction.** Schema = structure (auto-generated). Data =
  contents (hand-written with `RunPython`). Adding a column is schema; filling that column on
  existing rows is data. Big changes often need one of each.
- **`RunPython` is how a migration carries logic.** It runs a function during `migrate`, letting you
  transform existing data as part of the deployment. It takes a forward function and (ideally) a
  reverse one so the migration can be undone.
- **Know your inspection commands.** `showmigrations` tells you the current state; `migrate` with a
  target can roll back. These are your tools when a migration goes wrong or you need to understand
  where a database stands.
- **Commit model change + migration together.** They're inseparable. A commit that changes a model
  without its migration will fail for every teammate and every environment.

**Do:**
1. Run `python manage.py showmigrations scheduling` and read the applied/unapplied list. Match a
   couple of entries to files in the `migrations/` folder.
2. Create a **data migration**:
   ```bash
   python manage.py makemigrations scheduling --empty --name backfill_minutes
   ```
   Edit the generated file to add a `RunPython` operation that sets `estimated_minutes = 30` on
   every `CurriculumItem` still at the default `15`. Apply it with `migrate`, then verify in the
   shell that the values changed.

**Check yourself:**
- What is the difference between a schema migration and a data migration, with an example of each?
- What does `RunPython` let a migration do that an auto-generated one can't?
- Why must a migration be committed together with its model change?

---

# WEEK 3 — APIs, React, and shipping

Goal: understand DRF (the REST API), how React consumes it, and how the app deploys.

---

### LEARN-18 — What is DRF? Serializers

**Concept:**
So far every "view" produced HTML. But your React front-end doesn't want HTML — it wants **data**,
as JSON, so it can render the UI itself. Serving structured data over HTTP for programs (rather than
pages for humans) is what an **API** does, and **Django REST Framework (DRF)** is the toolkit that
makes building one pleasant. It sits on top of Django and adds serializers, API views, permissions,
and authentication tailored to JSON APIs.

The central new concept is the **serializer**, and the cleanest way to understand it is by analogy:
*a serializer is to JSON what a form is to HTML.* A `ModelForm` (LEARN-09) turns a model into an
HTML form, validates submitted form data, and saves it. A `ModelSerializer` turns a model into
JSON, validates submitted JSON, and saves it. Same job, different wire format. You declare it the
same way too: `class Meta: model = Session; fields = [...]`. Serialization goes both directions —
model → JSON when responding, and JSON → validated model data when accepting input.

Serializers give you fine control over the shape of your API. `read_only_fields` marks fields the
client may *see* but never *set* — `status` and `meeting_url` are server-controlled, so a client
can't forge them. A `SerializerMethodField` computes a value that isn't a plain database column;
`confirmed_count` on `SessionSerializer` runs a query to count confirmed bookings and includes the
result in the JSON. And when your payload doesn't correspond to a model at all — like a login or a
password change — you use a plain `serializers.Serializer` and define its fields by hand, as this
app does for `BookingCreateSerializer` and `PasswordChangeSerializer`. Just like forms, validation
lives in the serializer via `validate_<field>()` (single field) and `validate()` (cross-field)
methods.

**Look at:** `scheduling/api/serializers.py`.

**Principles:**
- **DRF builds JSON APIs; serializers are its core.** When the consumer is a program (your React
  app), you serve JSON, and serializers are how models become JSON and back.
- **Serializer : JSON :: ModelForm : HTML.** This analogy carries you a long way. Both validate
  input, both can save to the database, both derive fields from a model via `Meta`. Only the wire
  format differs.
- **`read_only_fields` protects server-controlled data.** Fields like `status` and `meeting_url`
  are output-only; the client can read them but any attempt to set them is ignored. This is a
  security boundary, not just a convenience.
- **`SerializerMethodField` adds computed values.** When the API should return something that isn't
  a stored column (a count, a derived label), a method field computes it. `confirmed_count` is a
  live example.
- **Plain `Serializer` handles non-model payloads.** Not every request maps to a model. Logins,
  password changes, and custom actions use hand-declared serializers with their own validation.
- **Validation belongs in the serializer.** `validate_<field>` and `validate` are the API's
  equivalent of a form's `clean` methods — the trust boundary for incoming JSON.

**Do:**
1. Map each field in `SessionSerializer.fields` back to the `Session` model. Which are plain model
   fields, which are `read_only`, and which are computed method fields?
2. Read the `PasswordChangeSerializer` we added earlier. Find the exact lines where it (a) verifies
   the current password and (b) runs Django's password-strength validators. Connect this back to
   `set_password`/`check_password` from LEARN-10.

**Check yourself:**
- Complete the analogy: a serializer is to JSON as a ModelForm is to ___.
- What does `read_only_fields` prevent, and why is that a security concern?
- When would you use a plain `Serializer` instead of a `ModelSerializer`?

---

### LEARN-19 — DRF views: APIView vs generics

**Concept:**
Just as Django has views that turn requests into HTML responses, DRF has **API views** that turn
requests into JSON responses. DRF offers two styles, and knowing when to use each is the skill of
this ticket. At the low level is **`APIView`**, where you write the HTTP-method handlers yourself —
a `get()` method, a `post()` method, a `patch()` method — giving you total control over exactly
what happens. At the high level are the **generic views** (`ListAPIView`, `ListCreateAPIView`,
`DestroyAPIView`, etc.), which implement the common CRUD patterns for you; you just supply a
`serializer_class` and a queryset, and DRF fills in the standard list/create/delete behavior with
almost no code.

The rule of thumb: reach for a **generic** when your endpoint is standard CRUD over a model
("list the teacher's sessions, and let them create one"), and drop to **`APIView`** when the action
is custom or doesn't map cleanly to CRUD (the `MeView` needs to combine user + profile data and the
`BookingCreateView` needs to run the booking *service* and interpret its boolean result). Generics
save code; `APIView` gives control. This app uses both deliberately — compare
`TeacherSessionListCreateView` (generic) with `MeView` (APIView).

Two methods carry critical responsibility in generic views. **`get_queryset`** defines *which rows*
the endpoint exposes, and this is a **security boundary**: `Booking.objects.filter(student=self.request.user)`
ensures a student sees only *their own* bookings. If you carelessly returned `Booking.objects.all()`,
every student could read everyone's bookings — a classic data-leak bug. And **`perform_create`**
lets you inject server-side values the client must not control, like stamping the new object with
`teacher=self.request.user` so a teacher can't create a session "as" someone else.

**Look at:** `scheduling/api/views.py`.

**Principles:**
- **Generics for CRUD, `APIView` for custom.** Match the tool to the job: standard list/create/
  delete → generic (minimal code); anything bespoke → `APIView` (full control). Using a generic
  where an `APIView` is needed leads to fighting the framework, and vice versa leads to reinventing
  CRUD.
- **`get_queryset` is a security boundary, not just a data source.** It decides what the caller can
  possibly see. Always scope it to the current user for user-owned data. "Return everything and
  filter later" is how leaks happen.
- **`perform_create` injects trusted, server-side fields.** Ownership and status should be set by
  the server, not accepted from the client. `perform_create` (and `read_only_fields`) together stop
  a client from forging who owns a record.
- **API views still lean on serializers and permissions.** A DRF view is thin glue: a permission
  class guards it (LEARN-20), a serializer validates and shapes the data (LEARN-18), and — ideally —
  a service does the real work (LEARN-12). The view coordinates.
- **The same thin-view discipline from LEARN-04 applies here.** `BookingCreateView` doesn't contain
  booking rules; it calls `create_booking`. The API is just another caller of your services.

**Do:**
1. Contrast `TeacherSessionListCreateView` (generic) with `MeView` (APIView). For each, articulate
   *why* that style is the right choice.
2. Find every `get_queryset` that filters by `self.request.user`. Pick one and describe exactly
   what security bug would appear if it returned `.all()` instead.

**Check yourself:**
- When do you choose `APIView` over a generic view, and vice versa?
- What is the security role of `get_queryset`, and what breaks if you get it wrong?
- What does `perform_create` let you enforce that the client can't override?

---

### LEARN-20 — API authentication & permissions (JWT)

**Concept:**
The templates website authenticates with **sessions**: when you log in, Django stores a session on
the server and hands your browser a cookie; every subsequent request carries that cookie and Django
looks up who you are. That works great for a server-rendered site, but it fits an API poorly,
especially one consumed by a separate JavaScript app. Instead, this app's API uses **JWT**
(JSON Web Tokens) for **stateless** authentication. "Stateless" means the server keeps *no* session
record; instead, the client holds a signed token that itself proves who they are, and presents it on
every request in the `Authorization: Bearer <token>` header. The server verifies the signature and
trusts the claims inside — no server-side lookup needed.

The flow has two tokens by design. You `POST` your username and password once to
`/api/auth/token/` and receive an **access** token and a **refresh** token. The *access* token is
short-lived (minutes) and is what you attach to API calls; keeping it short limits the damage if
it leaks. The *refresh* token lives longer and is used only to obtain a fresh access token from
`/api/auth/token/refresh/` when the old one expires — so the user doesn't have to log in again
every few minutes. (Your React `api.js` automates exactly this refresh dance, which you'll see in
LEARN-21.)

Separate from *authentication* (who you are) is **authorization** via DRF **permission classes**
(the API's version of LEARN-11's role checks). A permission class runs *before* your view body and
decides whether this caller may proceed. `IsAuthenticated` requires a valid token at all; the
custom `IsStudent` and `IsTeacher` classes require the right group. The two failure modes map to two
HTTP status codes you must be able to distinguish: **401 Unauthorized** means "I don't know who you
are" (missing/invalid token — authenticate first), while **403 Forbidden** means "I know who you
are, but you're not allowed" (valid token, wrong role).

**Look at:** `scheduling/api/permissions.py`, `scheduling/api/urls.py` (token endpoints),
`config/settings.py` (`REST_FRAMEWORK`, `SIMPLE_JWT`), `frontend/src/api.js`.

**Principles:**
- **Session auth for the website, JWT for the API.** Two front-ends, two auth mechanisms suited to
  each. Cookies/sessions fit server-rendered HTML; stateless tokens fit APIs and SPAs.
- **JWT is stateless: the token *is* the proof.** No server-side session store. The client sends
  `Authorization: Bearer <access-token>`; the server verifies the signature. This scales well and
  decouples the API from session storage.
- **Two tokens, two lifetimes, for safety and convenience.** Short-lived *access* tokens limit the
  blast radius of a leak; long-lived *refresh* tokens spare users from constant re-login. Never
  treat them as interchangeable.
- **Permission classes are authorization, and they run first.** `IsAuthenticated`, `IsStudent`,
  `IsTeacher` gate the view before any logic runs — the API mirror of `require_group` from
  LEARN-11.
- **401 ≠ 403.** 401 = "authenticate" (no/invalid identity). 403 = "you're identified but
  forbidden." Reading these correctly is essential for debugging API access and for building good
  clients.
- **CORS is a *browser* thing, not an auth thing (foreshadowing LEARN-22).** Note in the exercise
  that `curl` reaches the API fine without any CORS setup — because CORS only constrains browsers.

**Do:**
1. Get a token pair from the command line:
   ```bash
   curl -s -X POST http://127.0.0.1:8000/api/auth/token/ \
     -H "Content-Type: application/json" \
     -d '{"username":"demo_student","password":"demo1234"}'
   ```
2. Copy the `access` value and call a protected endpoint with it:
   ```bash
   curl -s http://127.0.0.1:8000/api/me/ -H "Authorization: Bearer <PASTE_ACCESS>"
   ```
3. Now call `/api/me/` with **no** header and read the 401. Then (optional) try a student-only
   endpoint with a teacher token, or vice versa, and observe a 403 — feel the difference.

**Check yourself:**
- Why does an API prefer stateless JWT over server-side sessions?
- What are the distinct roles of the access token and the refresh token?
- Explain the difference between a 401 and a 403 response, with a cause for each.

---

### LEARN-21 — The React front-end & how it talks to the API

**Concept:**
The `frontend/` directory is a wholly separate **React single-page application (SPA)**. Unlike the
Django templates — where the server builds each HTML page — a SPA loads once in the browser and then
*renders itself* using JavaScript, fetching raw data from your API as needed and updating the page
in place without full reloads. The crucial mental model: **React never touches the database.** It
has no ORM, no models, no direct data access. It makes HTTP calls to `/api/...`, receives JSON, and
turns that JSON into UI. All the rules still live in your Django services (LEARN-12); React is a
consumer, not an authority.

All the plumbing for talking to the backend is centralized in `frontend/src/api.js`. This one module
handles logging in (calling the token endpoint), storing the JWT tokens in the browser's
`localStorage` so they survive page reloads, attaching the `Authorization: Bearer` header to every
request, and — importantly — **automatically refreshing** an expired access token using the refresh
token (the LEARN-20 dance, automated) so the user isn't kicked out mid-session. Centralizing this
means individual pages just call a helper and don't each reimplement auth.

React's rendering model rests on two "hooks." `useState` holds data that can change over time (the
list of sessions, a form's current input); when you update state, React re-renders the affected UI
automatically. `useEffect` runs side effects like fetching data — typically "when this page first
appears, go fetch from the API and put the result in state." You can see the whole pattern in
`StudentSessionsPage.jsx`: on mount, fetch open sessions into state; render a card per session; when
the user books, POST to the API and refresh the list. A nice higher-level example is the sidebar,
which fetches `/api/me/` to learn your **roles** and shows only the links relevant to you — a UI
decision driven entirely by backend data.

**Look at:** `frontend/src/api.js`, `frontend/src/App.jsx`,
`frontend/src/pages/StudentSessionsPage.jsx`, `frontend/src/pages/ProfilePage.jsx`.

**Principles:**
- **React consumes the API; it never touches the database.** It fetches JSON and renders it. Every
  rule is still enforced server-side in your services — never trust the client to enforce anything
  important, because anyone can call your API directly (as your `curl` in LEARN-20 proved).
- **Centralize API/auth plumbing in one module.** `api.js` owns tokens, headers, and refresh logic
  so pages stay simple. This is DRY for the front-end: one place to fix an auth bug.
- **Tokens live in `localStorage` and are auto-refreshed.** Persisting them survives reloads;
  transparent refresh keeps sessions alive without re-login. Understand this flow — it's where SPA
  auth bugs usually hide.
- **`useState` + `useEffect` are the core rendering loop.** State holds data and drives re-renders;
  effects fetch data (usually on mount). "Fetch in an effect, store in state, render from state" is
  the pattern behind almost every page.
- **The same backend rules apply to both UIs, with zero duplication.** Because both the website and
  React call the same services, a rule change (like your "max 3 bookings") is instantly true
  everywhere. The front-end can't and shouldn't re-encode business logic.

**Do:**
1. Run React (`cd frontend && npm run dev`, then open `:5173`) and trace one booking end to end:
   which `api.js` function fires, which endpoint it hits, what JSON returns, and how the page
   updates its state to reflect the new booking.
2. In `StudentSessionsPage.jsx`, render one more piece of info per session — the API already
   returns `teacher_name`, so display it. Watch the UI update from a pure front-end change.

**Check yourself:**
- Where does the React app store its JWTs, and why there?
- What triggers an automatic token refresh, and which module handles it?
- Why can the same booking rule apply on both the website and React without being written twice?

---

### LEARN-22 — CORS & the dev proxy

**Concept:**
Browsers enforce a security rule called the **same-origin policy**: JavaScript running on one
"origin" (the combination of scheme + host + port, e.g. `http://127.0.0.1:5173`) is, by default,
*not allowed* to make requests to a different origin (e.g. `http://127.0.0.1:8000`). This exists to
stop a malicious site from quietly calling *your* bank's API using your logged-in cookies. But it
creates a practical problem in development, because your React dev server runs on port `5173` while
Django runs on port `8000` — two different origins. Left alone, the browser would block React's API
calls.

There are two standard ways to solve this, and this project is set up to use them. The first is a
**development proxy**: `frontend/vite.config.js` tells the Vite dev server "any request starting
with `/api`, forward it to `http://127.0.0.1:8000`." From the browser's perspective the request goes
to `5173` (same origin as the React app), so the same-origin policy is satisfied; Vite quietly
relays it to Django behind the scenes. The second is **CORS** (Cross-Origin Resource Sharing):
Django, via the `corsheaders` package, can send special response headers that explicitly say
"origin `http://127.0.0.1:5173` is allowed to call me," which tells the browser to permit the
cross-origin request. `CORS_ALLOWED_ORIGINS` in settings is that allow-list.

The subtlety that ties this back to LEARN-20: **CORS is purely a browser mechanism.** It is not
authentication, and it is not a server-side firewall. That's precisely why your `curl` commands
reached the API with no CORS configuration at all — `curl` is not a browser and doesn't enforce the
same-origin policy. CORS only ever affects requests made by browser JavaScript. In production you
typically sidestep the whole issue by serving the built React files from the *same* origin as the
API, or you lock `CORS_ALLOWED_ORIGINS` down to your real domain.

**Look at:** `config/settings.py` (`CORS_ALLOWED_ORIGINS`, the `corsheaders` middleware),
`frontend/vite.config.js` (the `/api` proxy).

**Principles:**
- **The same-origin policy is the reason CORS exists.** Browsers block cross-origin JS requests by
  default to protect users. CORS is the controlled, opt-in way for a server to say "these specific
  other origins may call me."
- **Two dev strategies for the `5173`/`8000` split:** the Vite dev proxy (make the browser think
  it's same-origin by routing `/api` through `5173`) and CORS headers (let Django authorize the
  cross-origin call). This project uses/knows both.
- **CORS is a browser feature, not auth and not a firewall.** It never blocks non-browser clients.
  `curl`, mobile apps, and server-to-server calls ignore it entirely — which is exactly why your
  earlier `curl` worked. Don't mistake CORS for a security boundary against all clients.
- **Production usually removes the problem.** Serve the built SPA from the same origin as the API,
  or restrict `CORS_ALLOWED_ORIGINS` to your production domain. Never leave it wide open.

**Do:**
1. Find the allowed origins in `settings.py` and the proxy rule in `vite.config.js`.
2. Write one sentence explaining what the proxy does and one sentence explaining what CORS does —
   in your own words, capturing why each solves the cross-origin problem.

**Check yourself:**
- What is an "origin," and what does the same-origin policy prevent?
- Why did your `curl` calls in LEARN-20 work without any CORS configuration?
- Name the two development strategies for the two-port split and how each satisfies the browser.

---

### LEARN-23 — Extending the API: pagination, filtering, ordering

**Concept:**
A toy list endpoint returns *everything* — fine when there are five sessions, disastrous when there
are fifty thousand. Real APIs shape their list responses in three related ways. **Pagination** caps
how many items come back per request and provides links to fetch subsequent "pages," so a single
call never dumps the whole table (and never times out or blows up memory). **Filtering** lets the
client narrow results with query-string parameters — `/api/sessions/open/?class_type=3` asks for
just one class type's sessions. **Ordering** lets the client choose the sort — `?ordering=start_time`.
Together these turn a naive list into a scalable, flexible resource.

DRF supports all three with minimal effort. Pagination is often configured *globally* in
`REST_FRAMEWORK` (a default pagination class plus a `PAGE_SIZE`), so every list endpoint gets it at
once; enabling it changes the response shape from a bare array to an object with `count`, `next`,
`previous`, and `results`. Filtering and ordering can be added declaratively with helpers
(`django-filter`, DRF's `SearchFilter` and `OrderingFilter`) or done by hand inside `get_queryset`
by reading `self.request.query_params` and applying `.filter(...)` accordingly.

There's a design lesson here that connects to your earlier REST-vs-JSON-RPC exploration. In REST,
you expose *one* resource (`/sessions/`) and vary it with query parameters, rather than inventing a
new named method for every variation (as JSON-RPC's long method lists did). "Filter the same
collection with parameters" is the idiomatic REST approach — fewer endpoints, more composability.

**Look at:** `config/settings.py` (`REST_FRAMEWORK`), `scheduling/api/views.py`.

**Principles:**
- **Never return unbounded lists — paginate.** A list endpoint should cap its response size by
  default. Pagination protects your server (memory, query time) and your client (bandwidth, render
  time). It's a correctness and scalability issue, not a nicety.
- **Filter and sort via query parameters — the REST way.** `?status=open&ordering=start_time`
  varies one resource instead of multiplying endpoints. This is the flexibility you noticed REST
  has over JSON-RPC: the collection is one URL, refined by params.
- **`self.request.query_params` is where those params live in a DRF view.** Reading them in
  `get_queryset` lets you translate client intent into ORM filters — reusing everything you learned
  in LEARN-08.
- **Global config vs per-view config.** Pagination is commonly global (one setting, all list
  endpoints benefit); bespoke filtering is per-view. Know which knob is which so you change behavior
  at the right scope.

**Do:**
1. Add manual filtering to `OpenSessionListView.get_queryset`: if `class_type` is present in
   `self.request.query_params`, `.filter(class_type=...)` by it. Test with a valid token against
   `/api/sessions/open/?class_type=1` and confirm the list narrows.
2. (Optional) Turn on global pagination in `REST_FRAMEWORK` and observe how the JSON response shape
   changes to include `count`/`next`/`previous`/`results`.

**Check yourself:**
- Why is returning an unbounded list a real problem, not a minor one?
- How does filtering-by-query-param reflect REST's design compared to JSON-RPC's many methods?
- Where do query-string parameters live on a DRF request, and how do you turn them into ORM filters?

---

### LEARN-24 — Deployment: WhiteNoise, Gunicorn, Docker

**Concept:**
The `runserver` command you've used all along is a *development* server: convenient, auto-reloading,
and explicitly **not** built for production traffic (it's single-threaded-ish, unhardened, and
Django's own docs warn against it in production). Shipping a Django app means replacing it with a
real **WSGI server**. WSGI is the standard interface between a Python web app and a server;
**Gunicorn** is a popular WSGI server that runs multiple worker processes to handle real concurrent
traffic, serving your app via `config.wsgi`. That's the "web" process in production.

Production also handles static files differently (recall LEARN-15): at build/release time you run
`collectstatic` to gather every app's CSS/JS/images into one folder, and **WhiteNoise** serves them
efficiently with caching headers, so Gunicorn's Python workers aren't wasted delivering static
assets. And because "it works on my machine" is not a deployment strategy, this project uses
**Docker** to package the app and all its dependencies into a reproducible image; `docker-compose`
additionally spins up a Postgres database container so the whole stack comes up with one command.
The `Procfile` expresses the same idea for Heroku-style platforms: a `release` step that runs
`migrate`, and a `web` step that starts Gunicorn.

Finally, production flips on a set of **security hardening** settings (guarded so they're off in
dev): forcing HTTPS (`SECURE_SSL_REDIRECT`), marking cookies secure so they only travel over HTTPS,
and enabling HSTS so browsers refuse to talk to your site over plain HTTP. Read that block in
`settings.py` and understand that each line closes a specific real-world attack vector.

**Look at:** `Dockerfile`, `docker-compose.yml`, `Procfile`, `requirements.txt`, and the
production-hardening block in `config/settings.py`.

**Principles:**
- **`runserver` is dev-only; production uses a WSGI server (Gunicorn).** The dev server isn't built
  for real load or hostile input. Gunicorn runs multiple workers and is designed for production
  traffic. Never expose `runserver` to the internet.
- **Static files: `collectstatic` + WhiteNoise.** Gather once, serve efficiently, keep Python
  workers focused on dynamic requests. This is the production half of LEARN-15.
- **Docker makes deployment reproducible.** The image bundles the exact Python version, deps, and
  code, so it runs the same everywhere. `docker-compose` brings up the app *and* Postgres together —
  the whole environment as code.
- **The `Procfile` declares processes.** `release` (run migrations on deploy) and `web` (start
  Gunicorn) — a concise contract for platform-as-a-service hosts. Same concepts as Docker, different
  packaging.
- **Production hardening is deliberate and settings-driven.** SSL redirect, secure cookies, HSTS —
  each defends against a specific attack (downgrade, cookie theft over HTTP). They're gated so dev
  stays convenient while prod stays safe.

**Do:**
1. Read the `Dockerfile` top to bottom and narrate each instruction in plain English (base image →
   install dependencies → copy code → collectstatic → run migrate + gunicorn).
2. Match each line of the `Procfile` to what it accomplishes and when it runs.
3. (Only if you have Docker installed) `docker compose up --build` and hit the running app.

**Check yourself:**
- Why must you not use `runserver` in production, and what replaces it?
- What do `collectstatic` and WhiteNoise together accomplish?
- What problem does Docker solve, and what does `docker-compose` add on top?

---

### LEARN-25 — Security checklist (Django's built-ins)

**Concept:**
A comforting truth: Django ships with strong defenses against the most common web attacks *turned on
by default* — your main job is to not accidentally disable them and to understand what they protect
against. This ticket consolidates the security ideas scattered through the course into one mental
checklist. The four big categories are CSRF, SQL injection, XSS, and secret management.

**CSRF** (Cross-Site Request Forgery) is an attack where a malicious page tricks your logged-in
browser into submitting a state-changing request to your app using your cookies. Django blocks this
by requiring a secret token on every form POST — which is why every HTML `<form method="post">` must
include `{% csrf_token %}` (LEARN-09), and why the API, which uses stateless JWT in a header rather
than cookies, isn't vulnerable in the same cookie-based way. **SQL injection** is neutralized by the
ORM (LEARN-08): because you pass values as parameters (`filter(name=user_input)`) rather than
building SQL strings, malicious input can't alter your query — *provided* you don't drop down to
raw string-built SQL. **XSS** (Cross-Site Scripting) is when attacker-supplied content is rendered
as executable HTML/JS in another user's browser; Django's templates **auto-escape** every
`{{ variable }}` by default, so `<script>` in user data renders as harmless text — you only lose
that protection if you explicitly mark content `|safe`, which you must never do to untrusted data.
And **secrets** (LEARN-14): `SECRET_KEY` and passwords come from the environment, never git, and
`DEBUG` is `False` in production so error pages don't leak internals.

The single most useful habit: run `python manage.py check --deploy`. This is Django's own
production-readiness audit — it inspects your settings and warns about insecure configuration
(missing HSTS, insecure cookies, `DEBUG` on, and more). Some warnings are expected in a dev
environment; the skill is reading each one and knowing whether it matters for your target
environment.

**Look at:** `config/settings.py` (middleware + hardening), any `<form method="post">` template
(for `{% csrf_token %}`).

**Principles:**
- **Django is secure by default — the risk is turning protections off.** CSRF protection,
  auto-escaping, and parameterized queries are on unless you disable them. Respect them; don't
  reach for `|safe`, raw SQL, or `csrf_exempt` without a very good, well-understood reason.
- **CSRF: every cookie-based POST needs `{% csrf_token %}`.** It proves the request came from your
  own form, not a hostile third-party page. The JWT API avoids cookie-CSRF by authenticating via a
  header instead — a different model with different risks.
- **SQL injection: let the ORM parameterize.** Never build queries by string-concatenating user
  input. `filter(x=user_input)` is safe; f-string SQL is a vulnerability.
- **XSS: templates auto-escape — keep it that way.** `{{ value }}` renders untrusted data inertly.
  `|safe` disables that and should only ever touch content you fully control and trust.
- **Secrets in the environment, `DEBUG=False` in prod.** No secrets in git; no debug pages in
  production. These two alone prevent a large share of real-world Django incidents.
- **`manage.py check --deploy` is your pre-flight audit.** Run it before shipping and read every
  warning deliberately. It encodes Django's own security recommendations so you don't have to
  memorize them.

**Do:**
1. Run `python manage.py check --deploy` and read each warning. For a couple of them, decide whether
   it's an expected dev-only warning or something you'd fix before production.
2. Find a `{% csrf_token %}` in a form template and explain, concretely, what attack becomes
   possible if you remove it.

**Check yourself:**
- Name the four attack categories Django defends against by default and one mechanism for each.
- Why is the JWT API not vulnerable to CSRF in the same way the cookie-based website is?
- When is using `|safe` in a template dangerous, and when is it acceptable?

---

# WEEK 4 — Testing in depth (the different kinds of tests)

Goal: go beyond "I wrote a test" to understanding the *taxonomy* of tests — what each kind
proves, what it costs, and when to reach for it. This is the skill that lets you trust a codebase
enough to change it. LEARN-16 taught you the basics; this week makes you fluent.

---

### LEARN-26 — The testing pyramid: what kinds of tests exist and why

**Concept:**
"Write tests" is too vague to act on, because *tests* is a family of very different tools. The
classic mental model is the **testing pyramid**, which sorts tests by scope. At the wide bottom are
**unit tests**: they check one small piece (a single function or method) in isolation, run in
milliseconds, and you write hundreds of them. In the middle are **integration tests**: they check
that several pieces work together — a service function that touches the database, a view that calls
a service and renders a template — slower and fewer. At the narrow top are **end-to-end (E2E)
tests**: they drive the whole system the way a real user would (a browser clicking through the
site), which is the most realistic but also the slowest and most fragile, so you write only a
handful covering critical journeys.

The pyramid *shape* is the lesson: you want *many* fast, focused unit tests, *some* integration
tests, and *few* slow E2E tests. Inverting it — relying mostly on slow, flaky end-to-end tests —
gives you a test suite so slow and unreliable that people stop running it, which is worse than no
suite because it provides false confidence. Each layer trades **speed and precision** (a failing
unit test points at the exact broken function) against **realism** (an E2E test proves the actual
product works, integrations and all).

There are also *cross-cutting* test types you'll meet this week that don't live on one pyramid
level: **mocking** (LEARN-30) is a technique used inside unit/integration tests to fake external
systems; **coverage** (LEARN-32) measures how much code your tests exercise; **characterization
tests** (LEARN-34) are how you retrofit tests onto code that has none. Understanding the whole map
first makes each specific ticket click into place — especially important for your goal of
maintaining code others (or an AI) wrote quickly and left untested.

**Look at:** `scheduling/tests.py` — classify each existing test. Is `test_purchase_membership_activates`
a unit test or an integration test? What about `test_jwt_and_open_sessions`?

**Principles:**
- **Tests form a pyramid: many unit, some integration, few E2E.** The proportions matter. Lots of
  fast tests give quick, precise feedback; a few realistic tests confirm the whole thing works.
  Aim for that shape deliberately.
- **Every test type trades speed/precision against realism.** A unit test is instant and tells you
  exactly what broke but proves little about the whole system. An E2E test proves the product works
  but is slow and, when it fails, doesn't tell you *where*. You need both ends, in the right ratio.
- **A slow or flaky suite gets ignored — and an ignored suite is worthless.** Speed and reliability
  are features of a test suite, not luxuries. This is *the* reason the pyramid is bottom-heavy.
- **Know which kind you're writing and why.** "What is the smallest thing that could prove this
  behavior?" usually points you to the right level. Don't write an E2E test for a rule a unit test
  could pin down.

**Do:**
1. Open `scheduling/tests.py` and label each of the existing tests as unit, integration, or E2E.
   (Hint: most are integration tests because they hit the database via `TestCase`.)
2. Write down, for your own reference, one example from *this app* that would be worth testing at
   each pyramid level (e.g. unit: a pure calculation; integration: `create_booking`; E2E: "student
   logs in, books a session, sees it in their list").

**Check yourself:**
- Describe the three pyramid levels and the trade-off each makes.
- Why is an inverted pyramid (mostly E2E) a bad idea?
- For a new booking rule, which test level would you reach for first, and why?

---

### LEARN-27 — Unit tests: pin down one piece in isolation

**Concept:**
A **unit test** verifies the smallest meaningful unit of behavior — usually a single function — in
isolation from the rest of the system. The ideal unit test has no database, no network, no file
system: you give the function inputs, you check its output. That isolation is what makes unit tests
blazing fast (you can run thousands per second) and *precise*: when one fails, exactly one small
thing is wrong, and the test name tells you what.

The catch in a Django app is that most of your logic touches the database, which technically makes
those tests "integration" tests (next ticket). True units are the pure, calculation-like pieces:
helpers that transform data, validation rules that operate on values, formatting functions. In this
app, `get_plan_prices()` in `services/payments.py` (returns a price mapping) and the escaping/
formatting helpers in `services/calendar.py` are close to pure — they compute from inputs without
much DB involvement, so they're natural unit-test targets. When you *write* code you want to unit
test, a good habit is to separate the pure decision from the impure action (exactly the
`can_book` predicate vs `create_booking` action split from LEARN-12): the predicate is far easier to
unit test.

Mechanically, unit tests use Python's `unittest` assertions (`assertEqual`, `assertTrue`,
`assertIn`, `assertRaises`) inside test methods. If a "unit" needs a database object to exist,
that's your signal it's really an integration test — and that's fine, just know which you're
writing.

**Look at:** `scheduling/services/payments.py` (`get_plan_prices`), `scheduling/services/calendar.py`
(the `_fmt`/`_escape` helpers), and the assertion style in `scheduling/tests.py`.

**Principles:**
- **A unit test isolates one function — no DB, no network, ideally.** That isolation buys speed and
  pinpoint failure messages. The more dependencies a test drags in, the less "unit" it is.
- **Pure functions are the easiest and best unit-test targets.** Same input → same output, no side
  effects. Writing your logic as pure functions where possible is what *makes* it unit-testable —
  testability is a design property, not an afterthought.
- **Separate decision from action to expose testable units.** `can_book` (pure-ish predicate) is
  trivially testable; `create_booking` (does the write, sends mail) needs more setup. Designing this
  split is a gift to your future test-writing self.
- **Fast tests get run constantly.** Because units are instant, you can run them on every save. That
  tight feedback loop is where a lot of the value of testing actually comes from.

**Do:**
1. Write a unit test for `get_plan_prices()`: assert it returns the expected plans with the expected
   price types. No database needed — just import and call it.
2. Write a unit test for the ICS escaping helper in `calendar.py` (e.g. that a comma or newline in a
   title is escaped correctly). Run `python manage.py test` and note how fast these are compared to
   the DB-backed tests.

**Check yourself:**
- What makes a test a "unit" test specifically?
- Why are pure functions the easiest things to unit-test?
- How does splitting `can_book` from `create_booking` help testing?

---

### LEARN-28 — Integration tests: prove the pieces work together

**Concept:**
An **integration test** checks that multiple components cooperate correctly — most commonly, that
your Python logic works *with the database*. In Django this is the bread-and-butter test, and it's
what almost every test in `scheduling/tests.py` actually is: `BookingServiceTests` creates real
`User`, `Group`, `Membership`, and `Session` rows, then calls `create_booking` and asserts the
database ends up in the right state (booking confirmed, and when all bookings are cancelled, the
session flips to cancelled). That's several units — the service, the models, the ORM, the cascade
logic — verified *together*.

Django's `TestCase` is what makes this safe and fast. Each test method runs inside a database
**transaction that is rolled back** at the end, so tests never pollute each other or your real data,
and setup work shared across tests goes in `setUp()`, which runs before each method. The pattern is:
`setUp` arranges the world (create the users, session, membership), each `test_` method acts and
asserts. Because it's a real database (SQLite in tests, per your settings), these tests catch bugs
unit tests can't — a wrong `related_name`, a bad migration, a query that doesn't filter what you
think it does.

Integration tests are the *sweet spot* for a service-layer app like this one. Your rules live in
services, your services talk to the database, and integration tests exercise exactly that
combination. They're slower than unit tests (each hits the DB) but far more realistic, and they're
where you'll spend most of your testing effort. This is also the level that protects you when
maintaining unfamiliar code: an integration test around a service documents and locks in its real
behavior.

**Look at:** `scheduling/tests.py` — `BookingServiceTests` in full, especially `setUp` and
`test_create_and_cancel_booking`.

**Principles:**
- **Integration tests verify components *together*, usually with the database.** They catch the
  bugs that live *between* units — wiring, migrations, relationships, query correctness — which unit
  tests by design cannot see.
- **`TestCase` wraps each test in a rolled-back transaction.** Tests are isolated and repeatable;
  they can freely create and destroy data without touching your real database or each other. This
  isolation is why you can trust a green suite.
- **`setUp` arranges shared fixtures; each `test_` acts and asserts.** Keep arrangement in `setUp`
  so individual tests stay focused on one behavior. This is Arrange–Act–Assert (LEARN-16) with the
  "arrange" hoisted up.
- **For a service-layer app, integration tests are the workhorse.** Your value lives where logic
  meets data, so that's where most tests should live. They're realistic enough to trust and fast
  enough to run often.

**Do:**
1. Add an integration test to `BookingServiceTests`: assert that booking the *same* session twice
   with the same student fails the second time (the duplicate rule). Reuse the `setUp` fixtures.
2. Add another: create a session whose `start_time` is in the *past* and assert `create_booking`
   returns `False`. Run the suite.

**Check yourself:**
- What kind of bug can an integration test catch that a unit test cannot?
- What does `TestCase` do at the end of each test method, and why does that matter?
- Why are integration tests the primary test type for *this* app specifically?

---

### LEARN-29 — API tests: exercise your endpoints like a client

**Concept:**
When you have an API (Week 3), you need tests that call it the way a real client would — over HTTP,
with authentication, checking status codes and JSON bodies. This is a specialized kind of
integration test focused on the *request/response contract* of your endpoints. The existing
`ApiSmokeTests.test_jwt_and_open_sessions` is the template: it POSTs credentials to
`/api/auth/token/`, asserts a 200 and pulls the `access` token from the JSON, then calls a protected
endpoint with an `Authorization: Bearer` header and asserts a 200. That single test proves the whole
auth chain (LEARN-20) works end to end.

API tests are where you verify things that only matter at the HTTP boundary: correct **status
codes** (200 for success, 201 for created, 400 for bad input, 401 for unauthenticated, 403 for
forbidden, 404 for missing), correct **JSON shape** (the fields your React app depends on), and —
critically — **authorization boundaries**. That last one is a security test: log in as a student and
assert you *cannot* reach a teacher-only endpoint (expect 403); assert one student cannot read
another student's bookings (the `get_queryset` scoping from LEARN-19). Bugs here are data-leak bugs,
so these tests earn their keep.

Django's test client (`self.client`, used in the smoke test) works well for this. DRF also ships its
own `APIClient` with conveniences like `force_authenticate` (skip the token dance when you just want
to test the view logic). Either way, the discipline is the same: make a request, assert the status,
assert the body, and cover both the allowed and the *forbidden* paths.

**Look at:** `scheduling/tests.py` (`ApiSmokeTests`), `scheduling/api/views.py` (the endpoints and
their permissions), `scheduling/api/permissions.py`.

**Principles:**
- **API tests verify the HTTP contract: status code + body + auth.** These are the things a client
  actually depends on. A view can "work" in Python and still return the wrong status or shape — API
  tests catch that.
- **Always test the *forbidden* paths, not just the happy path.** Assert that the wrong role gets
  403 and that users can't see each other's data. These are security regression tests; they're the
  most valuable API tests you'll write.
- **Match status codes to meaning.** 200/201 success, 400 bad request, 401 unauthenticated, 403
  forbidden, 404 not found. Asserting the *right* code (not just "not 500") documents and enforces
  correct behavior.
- **`force_authenticate` tests view logic; the token flow tests auth too.** Use the full token dance
  when you want to prove auth works; use `force_authenticate` when you just want to test what an
  authenticated user can do. Pick based on what you're actually verifying.

**Do:**
1. Add an API test: authenticate as a student, POST to the booking-create endpoint for a valid
   session, and assert a 201 plus the expected JSON. Then POST again for the same session and assert
   a 400 (duplicate).
2. Add a security test: with a student token, call a **teacher-only** endpoint (e.g. teacher
   sessions) and assert 403. This proves your permission classes actually work.

**Check yourself:**
- What three things does an API test typically assert?
- Why is testing the forbidden path a *security* measure?
- When would you use `force_authenticate` instead of getting a real token?

---

### LEARN-30 — Mocking: testing code that talks to the outside world

**Concept:**
Your app talks to systems you don't control: it sends email, it (eventually) charges Stripe, creates
Google Meet links, and syncs SimplyBook. You cannot let your tests actually send email or hit a
payment API — that would be slow, flaky (the network fails), and dangerous (real charges). The
solution is **mocking**: replacing a real dependency with a fake stand-in during the test, so you
can control what it returns and assert *how your code used it* without any real side effect.

Python's `unittest.mock` (and the `@patch` decorator / `patch()` context manager) is the standard
tool. The key idea is **patch where the thing is *used*, not where it's defined.** If
`services/notifications.py` does `from django.core.mail import send_mail` and calls `send_mail(...)`,
you patch `scheduling.services.notifications.send_mail` — the name *in the module under test* — and
your fake replaces it for the duration of the test. Then you can assert `mock_send_mail.assert_called_once()`
(did my code send exactly one email?) or make the mock raise an exception to test your error
handling.

This app is *designed* for this: the integrations degrade gracefully (`SimplyBookClient.fetch_bookings`
returns `[]` when disabled; `create_meet_link` returns a placeholder). That means you can test the
*happy path* by mocking the integration to return a canned success, and test the *failure path* by
making the mock raise — proving your code copes with a dead payment provider or a down email server.
Django also gives you a convenient built-in for email specifically: the `locmem` email backend
captures sent messages in `django.core.mail.outbox` so you can assert on them without mocking at all.
Mocking is the technique that makes external-facing code testable, which is exactly the kind of code
"vibecoded" apps wire up carelessly and leave unverified.

**Look at:** `scheduling/services/notifications.py` (`send_mail` usage), `scheduling/services/payments.py`,
`integrations/google/meet.py`, `integrations/simplybook/client.py`.

**Principles:**
- **Mock external dependencies — never hit real email/payment/network in tests.** Real side effects
  make tests slow, flaky, and unsafe. A mock gives you a fast, deterministic, harmless stand-in.
- **Patch where it's *used*, not where it's defined.** You replace the name as imported into the
  module under test (`scheduling.services.notifications.send_mail`), not `django.core.mail.send_mail`.
  Getting this wrong is the #1 mocking mistake — the patch silently does nothing.
- **Mocks let you assert *interactions* and simulate *failures*.** `assert_called_once_with(...)`
  verifies your code called the dependency correctly; `mock.side_effect = Exception(...)` lets you
  prove your error handling works when the outside world breaks. Both are things you can't test with
  the real thing.
- **Prefer a real fake when the framework gives you one.** For email, Django's `locmem` backend and
  `mail.outbox` are simpler and more realistic than mocking `send_mail`. Reach for purpose-built test
  doubles before hand-rolling mocks.
- **Testable external code is decoupled external code.** The reason this app is mockable is that its
  integrations are isolated behind small functions/clients. When you refactor messy code, pushing
  external calls behind a seam like this is what *makes* it testable.

**Do:**
1. Using `unittest.mock.patch`, write a test that books a session and asserts the confirmation email
   function was invoked — by patching `send_mail` in the notifications module and checking it was
   called once. (Alternative: switch the email backend to `locmem` in the test and assert
   `len(mail.outbox) == 1`.)
2. Write a failure test: make the patched `send_mail` raise an exception and assert that
   `create_booking` still succeeds (because `_safe_send` swallows errors). This proves email
   problems don't break booking.

**Check yourself:**
- Why must tests never call real external services?
- Explain "patch where it's used, not where it's defined" in your own words.
- What two things can a mock let you verify that a real dependency can't?

---

### LEARN-31 — Test data: setUp, fixtures, and factories

**Concept:**
Every test needs a *world* to act on — users, groups, sessions, memberships. How you build that
world determines how readable and maintainable your suite is. The simplest approach, which this app
uses, is the `setUp()` method: it runs before each test and creates the shared objects (see how
`BookingServiceTests.setUp` builds two groups, a teacher, a student, a membership, and a session).
This is perfect for a small suite. But as tests grow, you'll notice pain: every test class
re-creates users and groups, the setup gets long, and a tiny model change (a new required field)
forces edits in many places.

Three tools address this. **Fixtures** are pre-defined data (JSON files loaded with
`loaddata`/`fixtures = [...]`) — useful but rigid and easy to let rot, so use sparingly. **Helper
functions** (a `make_student()` you write once) are a pragmatic middle ground. The professional
standard is a **factory** library like `factory_boy`: you declare a `UserFactory`,
`SessionFactory`, etc., that know how to build valid objects with sensible defaults, and each test
overrides only the fields it cares about (`SessionFactory(capacity=1)`). Factories make tests read
like intent — "a session with capacity 1" — instead of a wall of boilerplate, and they update in one
place when your models change.

The deeper principle is that **good test data setup is what keeps a large suite maintainable.** When
adding a field to a model breaks 40 tests because each hand-built the object, people stop writing
tests. Factories (or at least shared helpers) localize that cost. For your goal of maintaining
messy inherited code, this matters doubly: the first thing you often do to untested code is stand up
easy ways to create its objects so you *can* start testing.

**Look at:** `scheduling/tests.py` (`setUp` methods across the three test classes — notice the
repetition of group/user creation).

**Principles:**
- **`setUp` runs before each test and holds shared arrangement.** It keeps individual tests focused
  on one behavior. Great for small suites; the first thing you reach for.
- **Repetition in `setUp` across classes is a smell pointing at factories.** When you see the same
  "create group, create user, add to group" everywhere, that's the signal to extract a helper or
  adopt `factory_boy`. DRY applies to tests too.
- **Factories make tests express intent, not boilerplate.** `SessionFactory(capacity=1)` says what
  matters and defaults the rest. Readable tests are maintainable tests.
- **Localized test-data setup survives model changes.** One factory to update beats forty hand-built
  objects to fix. This is what keeps a big suite from rotting — and what makes retrofitting tests
  onto legacy code feasible.

**Do:**
1. Extract the repeated group/user creation in `tests.py` into a module-level helper (e.g.
   `make_user(username, group)`), and refactor at least one test class to use it. Confirm the suite
   still passes.
2. (Stretch, needs internet before you fly) `pip install factory_boy`, write a `UserFactory` and a
   `SessionFactory`, and rewrite one test's setup with them to feel the difference.

**Check yourself:**
- What does `setUp` do, and when is it enough on its own?
- What problem do factories solve that hand-built objects in each test create?
- Why does test-data strategy affect whether a team keeps writing tests?

---

### LEARN-32 — Coverage: measuring what your tests actually exercise

**Concept:**
Once you have tests, a natural question is "how much of my code do they actually run?" **Code
coverage** answers that. A coverage tool (`coverage.py`, the standard for Python/Django) watches
your code while the test suite runs and records which lines executed and which never did. You get a
percentage and — more usefully — a line-by-line report showing exactly which branches your tests
never touched. Those untouched lines are your blind spots: code that could be completely broken and
your suite wouldn't notice.

The crucial caveat, and the reason coverage is often misused: **coverage measures execution, not
correctness.** A line can be "covered" by a test that never actually *asserts* anything about it.
100% coverage with weak assertions proves little; 70% coverage with sharp assertions on the
important paths can be plenty. So treat coverage as a *flashlight for finding untested code*, not a
score to maximize. Chasing 100% leads to worthless tests written just to color lines green,
especially on trivial code. The high-value use is: run coverage, look at what's *red* in your
critical modules (the services, the permissions, the booking rules), and decide whether those gaps
matter.

For maintaining inherited/vibecoded code, coverage is genuinely useful as a *map*: it shows you
which parts of an unfamiliar codebase have zero test protection, so you know where changes are
riskiest and where to add characterization tests (LEARN-34) before touching anything.

**Look at:** your whole test suite — this ticket is about measuring it, not a specific file.

**Principles:**
- **Coverage shows which lines ran during tests — your blind spots are the rest.** The line-level
  report is the valuable part; it points precisely at untested code. The single percentage is the
  least useful number it gives you.
- **Coverage measures execution, not correctness.** A covered line can still be untested if nothing
  asserts on its behavior. Never confuse "the tests ran this line" with "the tests verify this line
  is right."
- **Don't chase 100%.** Past a point, forcing coverage up produces hollow tests on trivial code and
  wastes effort better spent on sharp assertions for important paths. Coverage is a diagnostic, not
  a target.
- **On unfamiliar code, coverage is a risk map.** Zero-coverage modules are where changes are most
  dangerous and where you most need to add tests before editing. That's the maintainer's use of it.

**Do:**
1. (Needs internet) `pip install coverage`, then run:
   ```bash
   coverage run manage.py test
   coverage report        # summary per file
   coverage html          # open htmlcov/index.html for line-by-line
   ```
2. Open the HTML report and find the *lowest-covered* file among your services. Pick one untested
   branch that actually matters (a real rule, not a `__str__`) and write a test that exercises it.

**Check yourself:**
- What exactly does a coverage tool measure?
- Why is "100% coverage" not the same as "well tested"?
- How is coverage useful specifically when inheriting an unfamiliar codebase?

---

### LEARN-33 — End-to-end tests: drive the whole system like a user

**Concept:**
At the top of the pyramid, **end-to-end (E2E) tests** verify complete user journeys through the
*real, running* system: a browser opens the site, types into the login form, clicks "Book," and the
test asserts the booking appears in the list. Unlike the integration tests you've written (which
call Python directly), an E2E test exercises everything at once — the front-end JavaScript, the HTTP
layer, the API, the services, the database, even CSS-dependent interactions — the way an actual user
would. That realism is their unique value: they catch bugs that only appear when all the pieces run
together (a broken JS bundle, a CORS misconfig, a template that renders but whose button does
nothing).

That realism comes at a steep price, which is exactly why they sit at the narrow top. E2E tests are
**slow** (they boot a browser and a server), **flaky** (timing, animations, and network make them
intermittently fail for no real reason), and **expensive to maintain** (a redesigned page breaks
them). So you write *few* of them, covering only your most critical flows — for this app, something
like "log in → book a session → see it in my bookings," and "teacher creates a session → student can
book it." Everything else is better tested lower in the pyramid.

The tooling: Django's `LiveServerTestCase` starts a real test server your test can hit over HTTP.
Pair it with a browser-automation library — **Playwright** (modern, fast, less flaky) or **Selenium**
(older, ubiquitous) — to script the clicks. For your React SPA specifically, Playwright driving a
real browser against both servers is the realistic setup. You won't build a full E2E harness on the
plane, but you should understand *what* it is, *why* it's scarce, and *when* it's worth the cost.

**Look at:** conceptual — but map it to this app: `frontend/src/pages/StudentSessionsPage.jsx`
(the flow a browser test would drive) and `ApiSmokeTests` (the closest thing you have today).

**Principles:**
- **E2E tests prove the *whole product* works, integrations and all.** They're the only tests that
  exercise the real browser + front-end + API + DB together. That's their irreplaceable value.
- **They're slow, flaky, and costly — so keep them few and critical.** Cover only journeys whose
  breakage would be a disaster. Pushing lots of logic into E2E tests recreates the inverted-pyramid
  problem from LEARN-26.
- **`LiveServerTestCase` + Playwright/Selenium is the Django E2E stack.** One boots a real server;
  the other drives a real browser. Understand the two halves even before you wire them up.
- **Prefer the lowest pyramid level that can catch a given bug.** If an integration or API test can
  prove it, don't spend an E2E test on it. Reserve E2E for "does the assembled product actually
  work for a user."

**Do:**
1. Write down the 2–3 user journeys in this app that would genuinely justify an E2E test (the ones
   where silent breakage would be worst).
2. (Optional, needs internet + setup) `pip install playwright pytest-playwright`, `playwright install`,
   and sketch a single test: open `:5173`, log in as `demo_student`, and assert the sessions page
   loads. Notice how much slower it is than everything else — that's the pyramid teaching you.

**Check yourself:**
- What can an E2E test catch that even an API test cannot?
- Why do you write so few E2E tests?
- Which Django class gives you a real server for browser tests to hit?

---

### LEARN-34 — Characterization tests: safely changing code you didn't write

**Concept:**
This is the ticket that matters most for your actual goal — inheriting hastily built, untested code
and having to fix it without breaking it. Here's the trap: you're asked to change some messy
function, but there are no tests, so you have no idea what behavior you might break. If you just
start editing, you're flying blind. The professional technique is the **characterization test** (also
called a *golden master* test): before changing anything, you write tests that capture what the code
*currently does* — not what it *should* do, but what it *actually* does, bugs and all. These tests
"characterize" the existing behavior and become a safety net. Now you can refactor or fix
confidently: if a characterization test unexpectedly fails, you changed behavior you didn't mean to.

The workflow for taming legacy/vibecoded code is: (1) find a **seam** — a place you can call the code
and observe its output; (2) write characterization tests that pin the current outputs for a range of
inputs (run the code, see what it returns, assert exactly that); (3) *now* make your change; (4)
watch which characterization tests fail — expected failures confirm your intended change, unexpected
ones warn you of collateral damage; (5) update the tests to reflect the new intended behavior. This
is the inverse of TDD: in TDD you write a failing test for behavior you *want*; in characterization
testing you write passing tests for behavior that *exists*.

A close cousin is the **regression test for a bug**: when you find a bug, first write a test that
*reproduces* it (it fails, proving the bug is real and understood), then fix the code until the test
passes. That failing-first test guarantees the bug can never silently return, and it documents the
bug for the next person. Both techniques share one mindset: *never change code you don't understand
without first pinning its behavior in a test.* That single habit is what separates someone who
"fixes" vibecoded apps and introduces three new bugs from someone businesses trust to maintain their
software.

**Look at:** `scheduling/services/booking.py` (imagine it had *no* tests — how would you safely add
the "max 3 bookings" rule?) and the existing `scheduling/tests.py` as the safety net that already
exists here.

**Principles:**
- **Before changing untested code, characterize it.** Write tests that capture current behavior so
  you have a baseline. Editing untested code blind is how maintainers become bug-introducers.
- **Characterization tests record what *is*, not what *should be*.** You're building a safety net,
  not judging correctness yet. Even buggy behavior gets pinned — so you notice if your change alters
  it unintentionally.
- **For a bug, write a failing reproduction test first, then fix.** The red-then-green cycle proves
  you understood the bug and locks it out forever. A fix without a test invites the bug's return.
- **Unexpected test failures after a change are the point.** The safety net exists to catch behavior
  you *didn't* intend to change. Expected failures you then update; unexpected ones you investigate.
- **This mindset is the maintainer's core skill.** "Pin behavior, then change" is exactly what lets
  a human safely fix code that an AI or a rushed developer produced without tests. It's the whole
  reason this week matters for you.

**Do:**
1. Pretend `can_book` has no tests. Write 3–4 **characterization tests** that capture its current
   behavior across cases (no membership → False; valid → True; full session → False; duplicate →
   False). Run them; they should pass, describing today's behavior.
2. *Now* make a change (add the "max 3 bookings" rule from LEARN-12 if you haven't). Observe that
   your characterization tests still pass for the old cases while your new test covers the new rule —
   proof you extended behavior without breaking it.
3. Practice the bug workflow: introduce a deliberate small bug in a service, write a failing test
   that catches it, then fix the code and watch the test go green.

**Check yourself:**
- What is a characterization test, and how does it differ from a normal "should" test?
- Why write a failing reproduction test *before* fixing a bug?
- Explain, in one sentence, the habit that lets you safely change code you didn't write.

---

# WEEK 5 — DevOps & maintaining vibecoded apps

Goal: the practices that keep software *alive* after it's written — version control discipline,
automated quality gates, deployment pipelines, observability, and the meta-skill of inheriting a
messy codebase and making it trustworthy. This is the maintenance work businesses most need humans
for.

---

### LEARN-35 — Version control workflow: branches, commits, and pull requests

**Concept:**
Git is more than "save my code" — used well, it's the backbone of safe collaboration and safe
change. The core workflow professionals use: never commit straight to the main branch. Instead,
create a **feature branch** for each change (`git switch -c fix-booking-cap`), make small, focused
**commits** with clear messages as you go, push the branch, and open a **pull request (PR)** — a
proposal to merge your branch into main that others (or automated checks) review before it lands.
Main stays always-deployable; risky work happens on branches; nothing merges without passing review
and tests (LEARN-37).

Two habits make this powerful. First, **small, focused commits and PRs.** A commit should be one
logical change with a message explaining *why*, not *what* (the diff already shows what). A PR should
be reviewable in one sitting — a giant PR gets rubber-stamped, defeating the purpose. Second, the
PR is where **code review** happens: a second set of eyes catches bugs, questions unclear code, and
spreads knowledge. For inheriting vibecoded work, this is where you'd flag "this endpoint has no
auth" or "this duplicates a service" before it becomes permanent.

Git also gives you *safety*: because history is preserved, you can always see what changed and when
(`git log`, `git blame` to find when a line was introduced and why), and you can **revert** a bad
change cleanly. This history is your primary tool when debugging "it worked last week" — you can
literally bisect commits to find the one that broke things. Knowing git deeply is non-negotiable for
maintenance work.

**Look at:** run `git log --oneline -20` and `git status` in this repo to see its history and state.

**Principles:**
- **Work on branches; keep main always-deployable.** Feature branches isolate risk; main stays
  clean and shippable. This is the foundation every other DevOps practice builds on.
- **Small, focused commits and PRs — messages explain *why*.** Reviewable units get real review;
  huge ones get waved through. The *why* in a message is what helps future-you (the diff already
  shows the what).
- **Pull requests are where review and CI gate changes.** Nothing merges to main without passing
  automated checks and, ideally, human review. This is the quality gate that keeps bad code out.
- **Git history is a debugging tool.** `git log`, `git blame`, and `git revert` let you find when
  and why something changed and undo it safely. "When did this break?" is often answerable directly
  from history.

**Do:**
1. Create a branch for the learning work you've been doing: `git switch -c learning-django`. Notice
   your changes are now isolated from main.
2. Make a small, well-messaged commit of one ticket's work. Then run `git log --oneline` and
   `git blame LEARN_DJANGO.md` to see history and authorship.
3. Read the git safety and PR sections in your own `CLAUDE.md` — this repo already documents a
   commit/PR discipline.

**Check yourself:**
- Why work on branches instead of committing directly to main?
- What makes a good commit message and a good PR size?
- Name two ways git history helps you *debug* a problem.

---

### LEARN-36 — Linting & formatting: automated code quality gates

**Concept:**
Two categories of "is this code okay?" can be checked automatically, before a human ever reviews it.
A **formatter** enforces a consistent *style* — indentation, quote style, line length, import order
— so the whole codebase looks like one person wrote it and diffs stay clean (no noise from someone's
editor reformatting). A **linter** goes further and catches *likely problems*: unused imports,
variables assigned but never used, undefined names, shadowed built-ins, suspicious comparisons — a
whole class of bugs and smells found without running the code. For Python, the modern tool that does
both fast is **Ruff** (a formatter + linter in one); the classic split is **Black** (formatter) +
**Flake8** (linter). For your React side, **ESLint** + **Prettier** play the same roles.

The value is twofold. First, it removes an entire category of pointless debate and review comments
("you used tabs," "unused import here") — the machine handles style so humans review *substance*.
Second, linters genuinely catch bugs: an undefined variable or an unreachable branch is a real
defect a linter flags instantly. In vibecoded code especially, running a linter is often the fastest
way to surface dead code, obvious mistakes, and inconsistency left behind by rushed generation.

The professional move is to make these checks **automatic and unavoidable** via a **pre-commit
hook**: a script that runs the formatter and linter on your staged files *every time you commit*, so
badly formatted or lint-failing code literally can't enter the repo. The `pre-commit` framework
manages these hooks from a config file. Combined with the same checks running in CI (LEARN-37), you
get a two-layer guarantee that every commit meets a baseline of quality without anyone remembering
to check.

**Look at:** `requirements.txt` (see what tooling is/isn't present), and the code style across
`scheduling/` (consistent because a human followed conventions — a linter enforces that
automatically).

**Principles:**
- **Formatters kill style debates; linters catch real bugs.** Style is mechanical — let a tool own
  it. Linters find unused/undefined names and smells before code even runs. Together they raise the
  floor for free.
- **Automate the checks so they can't be skipped.** A rule only enforced by memory isn't enforced.
  Pre-commit hooks (local) plus CI (remote) make quality gates unavoidable — the only kind that
  actually hold.
- **Machines review style; humans review substance.** Offloading formatting/lint to tools means code
  review focuses on logic, design, and correctness — the things humans are actually good at.
- **On messy inherited code, the linter is a fast first pass.** Run it and you instantly see dead
  code, unused imports, and obvious mistakes — a cheap map of low-hanging problems in a vibecoded
  codebase.

**Do:**
1. (Needs internet) `pip install ruff`, then run `ruff check .` and `ruff format --check .` in the
   repo. Read what it flags. Fix a couple of real findings.
2. Add a `.pre-commit-config.yaml` that runs Ruff on commit, `pip install pre-commit`, and
   `pre-commit install`. Make a deliberately badly formatted change and try to commit it — watch the
   hook block you.

**Check yourself:**
- What's the difference between a formatter and a linter?
- Why run these as a pre-commit hook *and* in CI, rather than just asking people to run them?
- How does a linter help when you first open an unfamiliar, messy codebase?

---

### LEARN-37 — Continuous Integration: tests that run themselves

**Concept:**
All the tests and linters in the world do nothing if people forget to run them. **Continuous
Integration (CI)** fixes this by running your quality checks *automatically* on a server every time
code is pushed or a pull request is opened. The moment you push, a fresh clean machine spins up,
installs your dependencies, runs your test suite and linters, and reports pass/fail back on the PR.
If anything fails, the PR is blocked from merging. This is the mechanism that makes "main is always
green" a guarantee rather than a hope — broken code can't merge because the robot catches it first.

The most common platform is **GitHub Actions**, configured with a YAML file in
`.github/workflows/`. The workflow declares *when* to run (on push, on PR), and *what steps* to
execute: check out the code, set up Python, `pip install -r requirements.txt`, run
`python manage.py test`, run `ruff check`. Because your tests use SQLite (per this project's
settings), CI is simple — no database service needed; the test runner creates its own. Each run is
isolated and reproducible, which also catches "works on my machine" bugs (a missing dependency shows
up immediately on the clean CI box).

CI is the linchpin of the whole DevOps story: it's where the version-control discipline (LEARN-35),
the linting (LEARN-36), and the tests (Week 4) come together into an automatic gate. For maintaining
inherited code, setting up CI is often the *first* thing you do — it gives you a safety net that runs
on every change, so you can start improving a scary codebase knowing the robot will shout if you
break something.

**Look at:** `requirements.txt` (what CI would install), `CLAUDE.md` (the commands CI would run:
`python manage.py test`), and note the absence of a `.github/workflows/` folder — you'll create it.

**Principles:**
- **CI runs your checks automatically on every push/PR — no human memory required.** Automation is
  the entire point: checks that depend on discipline eventually get skipped; checks that run
  themselves never do.
- **A failing CI check blocks the merge.** This is what actually keeps main green and deployable. CI
  turns "we should run tests" into "you cannot merge broken code."
- **CI runs on a clean machine, catching environment bugs.** Missing dependencies, hidden reliance
  on local state, and "works on my machine" issues surface immediately in the fresh CI environment.
- **CI is where all the other practices converge.** Branch → PR → CI runs lint + tests → merge only
  if green. Understanding this pipeline is understanding modern software delivery.

**Do:**
1. Create `.github/workflows/ci.yml` for this project: trigger on push and PR; set up Python 3.14;
   `pip install -r requirements.txt`; run `python manage.py test`; run `ruff check .`. (Write it
   even if you won't push from the plane — the exercise is understanding each step.)
2. Trace, on paper, what happens from `git push` on a feature branch to the green check appearing on
   the PR. Name each stage.

**Check yourself:**
- What problem does CI solve that having tests alone does not?
- Why does running CI on a clean machine catch bugs your laptop hides?
- Why is CI often the first thing you set up when inheriting a codebase?

---

### LEARN-38 — Continuous Delivery, deployment & rollbacks

**Concept:**
CI proves your code is *good*; **Continuous Delivery/Deployment (CD)** gets that good code *to users*
automatically and safely. Where CI ends (tests pass on a merged commit), CD begins: build a
deployable artifact (for this app, a Docker image — LEARN-24), run the release steps (apply database
migrations), and start the new version serving traffic. "Continuous Delivery" means every green
commit is *ready* to deploy at the push of a button; "Continuous Deployment" means it deploys
*automatically*. Either way, the goal is deployments that are small, frequent, boring, and reversible
— the opposite of the terrifying big-bang release.

The single most important safety concept here is the **rollback**. Things *will* go wrong in
production despite your tests, so every deploy must be undoable *fast*. The way you achieve this is
by making deployments **immutable and versioned**: each release is a distinct, tagged artifact (a
Docker image with a version tag), so "roll back" simply means "redeploy the previous known-good
image." This app's `Procfile` shows the release/​deploy split (a `release` step runs migrations, a
`web` step runs Gunicorn), and Docker gives you the versioned artifacts. A subtle but critical rule:
**database migrations must be backward-compatible** if you want painless rollbacks — if a migration
deletes a column the old code needs, you can't simply roll back the code. This is why production
migration strategy (add columns before removing, deploy in phases) is its own discipline.

The mindset shift is from "deployment is a scary event" to "deployment is a routine, automated,
reversible operation." Small frequent deploys mean each change is low-risk and easy to pinpoint when
something breaks; a fast rollback means a bad deploy is a minor blip, not an outage. For maintaining
someone else's app, understanding *how it deploys and how to roll it back* is often the very first
thing you need to learn, because you'll be on the hook when it breaks.

**Look at:** `Dockerfile`, `docker-compose.yml`, `Procfile` (the release vs web split),
`config/settings.py` (production hardening that a deploy activates).

**Principles:**
- **CD turns green commits into safe, routine deployments.** Automating the path to production makes
  releases small, frequent, and boring — which makes them *safe*. Manual, rare, huge deploys are
  where disasters live.
- **Every deploy must be fast to roll back.** Production surprises are inevitable; recoverability is
  the safety net. If you can't quickly undo a deploy, you can't deploy safely.
- **Immutable, versioned artifacts make rollback trivial.** A tagged Docker image per release means
  rolling back is just redeploying the previous image. Reproducibility (LEARN-24) is what enables
  reversibility.
- **Migrations must be backward-compatible for clean rollbacks.** If new-code migrations break
  old-code assumptions, you can't roll back the code alone. Phased, additive migrations are the
  production-safe pattern.
- **Small, frequent deploys reduce risk and speed diagnosis.** When each release is tiny, a
  regression is easy to attribute and cheap to revert. This is counterintuitive but foundational.

**Do:**
1. Map this app's deploy: what does `release` do vs `web` in the `Procfile`? What artifact does the
   `Dockerfile` produce? Write out the steps from "merge to main" to "new version serving traffic."
2. Reason through a rollback: if a deploy breaks production, what exactly would you do to restore the
   previous version? What could make that hard (hint: a destructive migration)?

**Check yourself:**
- What's the difference between Continuous Delivery and Continuous Deployment?
- Why do versioned, immutable artifacts make rollbacks easy?
- Why can a database migration make a code rollback dangerous, and how do you avoid that?

---

### LEARN-39 — Observability: logging, monitoring & error tracking

**Concept:**
Once code runs in production, you can no longer see it with a debugger — so you need it to *tell you*
what it's doing. **Observability** is the practice of making a running system's behavior visible,
and it has three pillars. **Logging**: your app emits structured records of significant events
(a booking created, a payment failed, an unexpected error), written somewhere you can search later.
**Monitoring/metrics**: numeric signals over time (requests per second, error rate, response
latency, CPU) with **alerts** that page you when something crosses a threshold — this is how you find
out about problems *before* users complain. **Error tracking**: a service like **Sentry** that
captures every unhandled exception with its full stack trace, request context, and user info, and
groups them so you see "this error happened 400 times to 30 users since the last deploy."

Django has real logging built in — configured in `settings.py` under `LOGGING` — and the right habit
is to use Python's `logging` module (`logger.info(...)`, `logger.error(...)`) rather than `print()`,
because logging has levels (DEBUG/INFO/WARNING/ERROR), can be routed to files/services, and can be
turned up or down per environment. A key nuance you already touched: with `DEBUG=False` in
production (LEARN-14/25), users see a generic error page, so your logs and error tracker become your
*only* window into what actually went wrong. If they're not set up, a production bug is a mystery.

A humble but vital piece is the **health check** — a simple endpoint (e.g. `/healthz`) that returns
200 when the app is alive, which load balancers and uptime monitors ping constantly to know whether
to route traffic or raise an alarm. For maintaining inherited apps, observability is often the
difference between "a user tweeted that it's down" and "we got paged, saw the exact exception in
Sentry, and shipped a fix" — it's how professionals operate software they didn't write.

**Look at:** `config/settings.py` (look for/plan a `LOGGING` config), `scheduling/services/notifications.py`
(`except Exception: return False` — a place that silently swallows errors and would benefit from a
log line).

**Principles:**
- **You can't debug production with a debugger — instrument it instead.** Logging, metrics, and
  error tracking are how a running system tells you what's happening. Without them you're blind the
  moment code leaves your laptop.
- **Use the `logging` module, not `print`.** Levels, routing, and per-environment control make
  logging vastly more useful than prints — and prints often vanish in production anyway.
- **Alerts should tell you before users do.** Monitoring with thresholds means you learn about
  outages proactively. Finding out from an angry customer is a process failure.
- **With `DEBUG=False`, logs and error tracking are your only visibility.** Production hides details
  from users (correctly), so it must expose them to *you* through instrumentation. Set this up
  *before* you need it.
- **Silently swallowed errors are invisible failures — log them.** Code like `except Exception:
  return False` hides problems; at minimum it should `logger.exception(...)` so the failure is
  observable. Watch for this pattern in vibecoded code.

**Do:**
1. Add a `LOGGING` config to `settings.py` (console handler, sensible level) and add a
   `logger.exception(...)` line inside the `except` block in `notifications.py` so failed emails are
   *visible* instead of silent. Trigger it (e.g. with a bad email backend) and see the log.
2. Add a trivial health-check view returning `HttpResponse("ok")` at `/healthz/` and wire its URL.
   Understand why an uptime monitor would ping it.

**Check yourself:**
- Name the three pillars of observability and what each provides.
- Why is `logging` preferable to `print` in a real app?
- Why does `DEBUG=False` make logging and error tracking essential rather than optional?

---

### LEARN-40 — Dependency & supply-chain security

**Concept:**
Your app is mostly *other people's code*: Django, DRF, and everything in `requirements.txt` (plus the
huge tree of packages *those* depend on). That's normal and good — but it means your security and
stability depend on code you didn't write and that changes over time. **Dependency management** is
the discipline of keeping that borrowed code known, current, and safe. Two problems it addresses:
**reproducibility** (does everyone, and production, get the *exact same* versions?) and
**vulnerabilities** (does any dependency have a known security hole?).

Reproducibility comes from **pinning** versions. A loose `requirements.txt` with unpinned packages
means two installs a month apart can get different versions and behave differently — a classic
"works on my machine" and "worked last week" source. The fix is a **lockfile** or fully pinned
requirements (exact versions, ideally with hashes), so every environment is identical. Your React
side already does this: `package-lock.json` pins the entire JS dependency tree. The Python side
should be pinned with equal rigor.

Security comes from **auditing and updating**. Tools like **pip-audit** (Python) and `npm audit`
(JS) check your installed packages against databases of known vulnerabilities and tell you which to
upgrade. Automated services like **Dependabot** open PRs when a dependency has a security fix. The
discipline is to update *regularly and in small steps* — a dependency that's three years stale is
both a security risk and a nightmare to upgrade later (breaking changes pile up). This is enormous
for maintaining inherited apps: vibecoded projects are notorious for unpinned, outdated, vulnerable
dependencies, and getting them under control is often job #1.

**Look at:** `requirements.txt` (are versions pinned?), `frontend/package-lock.json` (fully pinned
JS tree — the gold standard), `frontend/package.json`.

**Principles:**
- **Your dependencies are your attack surface and your stability surface.** Most of your running code
  is third-party. Its bugs and vulnerabilities are *your* problem in production. Treat dependencies
  as code you're responsible for.
- **Pin versions for reproducibility.** Exact, locked versions mean dev, CI, and production run the
  identical code. Unpinned deps are a top cause of "works here, breaks there" and "worked last week."
- **Audit for known vulnerabilities, and update regularly in small steps.** `pip-audit`/`npm audit`
  surface risky packages; frequent small updates keep you current and make each upgrade manageable.
  Big-bang upgrades of years-stale deps are where projects get stuck.
- **Automate dependency updates where you can.** Tools like Dependabot turn "remember to check for
  security patches" into automatic PRs — the same automate-so-it-can't-be-forgotten principle as CI.
- **Stale dependencies are a hallmark of neglected/vibecoded code.** Pinning, auditing, and updating
  is often the first cleanup you do on an inherited project — and a concrete, high-value win to show.

**Do:**
1. Check whether `requirements.txt` pins exact versions. If any are loose, pin them to the currently
   installed versions (`pip freeze` shows them).
2. (Needs internet) `pip install pip-audit` and run `pip-audit` against the project. Read any
   findings and understand what an upgrade would involve.

**Check yourself:**
- Why are your dependencies part of *your* security responsibility?
- What problem does pinning versions (a lockfile) solve?
- Why update dependencies regularly in small steps instead of rarely in big jumps?

---

### LEARN-41 — Debugging production incidents

**Concept:**
Eventually something breaks in production, and fixing it is a distinct skill from writing features.
An **incident** follows a rough lifecycle: *detect* (an alert or a user report — LEARN-39 is what
makes detection fast), *triage* (how bad is it? who's affected? is it getting worse?), *mitigate*
(stop the bleeding *now* — often a rollback (LEARN-38) or disabling a feature, which is faster than a
proper fix), *diagnose* (find the real root cause using logs, error tracker, and git history), *fix*
(a real, tested correction), and *learn* (a blameless postmortem so it can't recur). The most
important reflex: **mitigate before you diagnose.** A user-facing outage is not the time to
leisurely hunt the root cause — restore service first (roll back), *then* investigate calmly.

Your diagnostic toolkit is everything from earlier weeks, now aimed at a live system. **Logs and the
error tracker** (LEARN-39) tell you *what* failed and with what stack trace. **Git history**
(LEARN-35: `git log`, `git blame`, and bisecting) tells you *when* it started and *what change*
likely caused it — "it worked last week" plus a deploy timeline usually points straight at the
culprit commit. The goal is to **reproduce** the failure (in a test or locally) because a bug you
can reproduce is a bug you can fix and, crucially, a bug you can write a **regression test** for
(LEARN-34) so it never returns.

The distinction between a **hotfix** and a **proper fix** matters. A hotfix is the minimal, urgent
change to stop harm (or a rollback); the proper fix is the considered correction with tests and
review that you ship once the fire is out. Confusing the two — either shipping a risky "real" fix
under pressure, or leaving a hacky hotfix as permanent — is a common failure mode. This whole
ticket *is* the job description for "human who maintains vibecoded apps": you'll be the one paged,
and calm, methodical incident response is what businesses are paying for.

**Look at:** conceptual, but concrete for this app — imagine `create_booking` starts throwing in
production. Where would you look first? (`config/settings.py` `LOGGING`, your error tracker, recent
commits touching `scheduling/services/booking.py`, `git log`.)

**Principles:**
- **Mitigate before you diagnose.** Stop user harm first — usually a rollback or feature disable —
  *then* investigate root cause. Debugging a live outage while users suffer is the wrong order.
- **Reproduce, then fix, then regression-test.** A reproducible bug is a fixable bug; a regression
  test (written to fail first) ensures it stays dead. No production fix is complete without a test
  that locks it out.
- **Logs + error tracker + git history are your diagnostic trio.** *What* failed (logs/Sentry),
  *when* it started and *what changed* (git). Together they usually pinpoint the cause fast.
- **Distinguish hotfix from proper fix.** Urgent minimal change to stop the bleeding vs the
  tested, reviewed correction shipped afterward. Don't ship risky fixes under fire; don't leave
  hacks permanent.
- **Blameless postmortems turn incidents into improvements.** Focus on *what in the system* allowed
  the failure (missing test? no alert? bad rollback?), not *who* did it. That's how reliability
  compounds — and it's exactly the maturity vibecoded projects lack.

**Do:**
1. Write your own one-page **incident runbook** for this app: the ordered steps you'd take if
   production started 500-ing on bookings (detect → mitigate/rollback → diagnose with logs+git →
   reproduce → fix+test → postmortem).
2. Practice the diagnosis half: introduce a bug in a service, then find it *only* using the test
   suite output and `git diff`/`git log` (no staring at the code first) — simulating production
   debugging where you start from symptoms, not the source.

**Check yourself:**
- Why mitigate before diagnosing, and what does "mitigate" usually mean in practice?
- What are your three main tools for diagnosing a production issue?
- What's the difference between a hotfix and a proper fix, and when do you use each?

---

### LEARN-42 — Inheriting & taming a vibecoded codebase (the meta-skill)

**Concept:**
This ticket ties the whole course to your actual goal. "Vibecoded" apps — built fast, by a person or
an AI, optimizing for "it runs" over "it lasts" — share predictable problems: no tests, business
logic smeared across views and templates, no separation of concerns, secrets in the code,
inconsistent style, unpinned/outdated dependencies, no CI, no observability, and behavior nobody
fully understands. Your job as the human who maintains it is to convert that into something safe to
change *without* a big scary rewrite (which usually fails). The strategy is incremental hardening,
and every tool in this course is a step.

Here's the playbook, in order, and notice it's just the course applied to a mess you didn't make:
**(1) Get it running and under version control** — reproduce the environment, pin dependencies
(LEARN-40), commit a known-good baseline (LEARN-35). **(2) Add a safety net before changing
anything** — set up CI (LEARN-37) and write **characterization tests** (LEARN-34) around the
critical paths so you can detect breakage. **(3) Add guardrails** — linting/formatting (LEARN-36)
and, if it's live, basic observability (LEARN-39) so you can see failures. **(4) Refactor in small,
tested steps** — extract business logic into a service layer (LEARN-12), fix one thing at a time,
each change protected by tests and reviewed via PR. **(5) Only then add features**, now that the
foundation is trustworthy. The golden rule throughout: **never make a behavioral change and a
refactor in the same commit**, and never change code you haven't first pinned with a test.

The mindset is *humility and incrementalism*. You will be tempted to rewrite it all — resist, because
the messy code encodes real, hard-won behavior (and edge cases) you don't fully see yet, and a
rewrite throws that away while introducing new bugs. The maintainer who's actually valuable is the
one who makes a scary codebase progressively safer, one tested change at a time, keeping it working
the entire way. That patience, backed by the concrete skills in Weeks 4–5, is the whole job.

**Look at:** your *own* app as the counter-example — it already has the things vibecoded apps lack: a
service layer (`scheduling/services/`), tests (`scheduling/tests.py`), separation of concerns,
env-driven secrets (`.env.example`), and docs (`CLAUDE.md`). Use it as the reference for what "tamed"
looks like.

**Principles:**
- **Vibecoded code has predictable weaknesses: no tests, tangled logic, no CI/observability, stale
  deps.** Knowing the pattern means you know where to look first. You're not exploring randomly;
  you're checking a known list.
- **Add a safety net *before* you change anything.** CI + characterization tests first, always.
  Changing untested code you don't understand is how maintainers become the next person's problem.
- **Refactor in small, tested, reviewed steps — never rewrite wholesale.** Big rewrites discard
  encoded behavior and usually fail. Incremental hardening keeps the app working while it improves.
- **Separate behavioral changes from refactors.** A commit either changes behavior *or* restructures
  it, never both — so when something breaks, you know which kind of change caused it. This is the
  single most important refactoring discipline.
- **Your own app is the template for "good."** Service layer, tests, separation of concerns, managed
  secrets, docs, deploy config. Taming a mess means moving it toward this shape, piece by piece.
- **Humility beats heroics.** The messy code knows things you don't yet. Respect it, pin it, improve
  it gradually. Patience is the professional skill.

**Do:**
1. Write a **"taming checklist"** you could apply to any inherited app, ordered by what you'd do
   first (version control + pinned deps → CI → characterization tests → linting → observability →
   incremental refactor to a service layer → features). Keep it; you'll reuse it for real.
2. Audit *this* app against that checklist: which items does it already satisfy, and what's the one
   thing you'd add next (hint: it has no CI or linting config yet — you added those in LEARN-36/37).

**Check yourself:**
- What are the recurring weaknesses of hastily built codebases?
- Why add CI and characterization tests *before* refactoring?
- Why should a behavioral change and a refactor never share a commit?
- Why is incremental hardening usually better than a rewrite?

---

### LEARN-43 — CAPSTONE: build one feature end to end

**Concept:**
Every ticket so far isolated one layer. Real features cut through *all* of them, and the only way to
prove you've internalized Django is to build one yourself, end to end, in the right order. This
capstone has you add **session reviews**: after a session has happened, a student who booked it can
leave a 1–5 star rating and a comment. Nothing here is new — it's a deliberate re-run of the entire
course on a fresh feature, so you feel how the layers connect into a single coherent workflow. Work
in the same order the layers were taught; that order is itself the lesson.

**Goal:** students can review sessions they attended; each review has a rating (1–5) and a comment.

**Do (in this order — it mirrors the whole course):**
1. **Model (LEARN-06)** — add a `Review` model in `scheduling/models.py`: a `ForeignKey` to
   `Session` and one to the student `User`, a `PositiveSmallIntegerField` `rating` (validate 1–5), a
   `comment` `TextField`, a `created_at`, plus a readable `__str__` and a `Meta.ordering`.
2. **Migration (LEARN-06/17)** — `makemigrations` then `migrate`. Open and read the generated file
   so you know exactly what it did.
3. **Admin (LEARN-07)** — register `Review` (ideally with a `list_display`) so you can inspect
   entries you create.
4. **Service (LEARN-12)** — create `scheduling/services/reviews.py` with `can_review(user, session)`
   (student must have a confirmed booking, the session must be over, and no review may already
   exist) and `create_review(user, session, rating, comment)`. *All rules live here* — not in the
   view or serializer.
5. **API (LEARN-18/19/20)** — add a `ReviewSerializer` and a `ReviewCreateView` that calls your
   service; scope any list `get_queryset` to the current user; protect it with the right permission
   class; wire a URL into `scheduling/api/urls.py`.
6. **React (LEARN-21)** — add a small review form to a past booking that POSTs through `api.js` and
   flashes a success message on completion.
7. **Test (LEARN-16, 27–30)** — write a *unit* test for any pure helper, *integration* tests for
   `can_review` (assert `False` before the session ends, `False` for a duplicate, `True` in the
   valid case), an *API* test for the review endpoint (201 on success, 403 for the wrong role), and
   *mock* any external call. Run `python manage.py test`.
8. **Document** — file a real entry in `TICKETS.md` describing what you built (practice the workflow
   you'll use for the rest of this app's life).

**Principles:**
- **Features are vertical; they cross every layer.** Model → migration → admin → service → API →
  front-end → test. Internalizing this sequence is the real graduation criterion.
- **Rules go in the service, even for a brand-new feature.** Resist putting "can this user review?"
  in the view or serializer. The service is the one home for domain logic — the same discipline that
  keeps the whole app consistent.
- **Build in dependency order.** You can't serialize a model that doesn't exist, or test a rule you
  haven't written. The teaching order *is* the build order for a reason.
- **Finish with tests and docs, not just working code.** A feature isn't done when it works once;
  it's done when it's guarded by tests and recorded for the next person (often future you).

**Check yourself:** You've now touched models, migrations, admin, services, DRF, React, and tests
for a single feature, in order. If you can do this unaided — including deciding what belongs in each
layer — you genuinely know Django.

---

## After the course

- Keep `TICKETS.md` for actual bugs and polish — that's its job.
- Revisit `docs/architecture-and-roadmap.md`; it will read completely differently now that you know
  every layer it describes.
- The real remaining work on *this* app is the credentialed integrations (Stripe, Google, SimplyBook)
  listed under "Not done" in `CLAUDE.md`.

Safe travels — build something on the plane.
