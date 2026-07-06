"""Studio-wide UI terminology — staff customizes labels shown in the React app."""

from scheduling.models import StudioGlossary

# (key, default singular, default plural, staff-facing description)
GLOSSARY_DEFS = [
    ('student', 'Student', 'Students', 'People who book and track progress'),
    ('teacher', 'Teacher', 'Teachers', 'People who teach and manage schedules'),
    ('class', 'Class', 'Classes', 'Teachable catalog entries (subject, level, topic)'),
    ('session', 'Session', 'Sessions', 'Scheduled appointments on the calendar'),
    ('booking', 'Booking', 'Bookings', 'A reserved seat in a session'),
    ('report', 'Report', 'Reports', 'Post-session feedback and skill ratings'),
    ('metric', 'Metric', 'Metrics', 'Scored dimensions on progress reports'),
    ('availability', 'Availability', 'Availability', 'When teachers can be booked'),
    ('studio', 'Studio', 'Studio', 'Your organization name in headings'),
]

GLOSSARY_KEYS = [key for key, _, _, _ in GLOSSARY_DEFS]


def ensure_default_glossary():
    for key, singular, plural, _ in GLOSSARY_DEFS:
        StudioGlossary.objects.get_or_create(
            key=key,
            defaults={'singular': singular, 'plural': plural},
        )


def glossary_entries():
    """All terms with current labels — for API and React."""
    ensure_default_glossary()
    rows = {r.key: r for r in StudioGlossary.objects.filter(key__in=GLOSSARY_KEYS)}
    return [
        {
            'key': key,
            'singular': rows[key].singular if key in rows else singular,
            'plural': rows[key].plural if key in rows else plural,
            'description': desc,
            'default_singular': singular,
            'default_plural': plural,
        }
        for key, singular, plural, desc in GLOSSARY_DEFS
    ]


def glossary_lookup():
    """Flat dict keyed by term for quick label resolution."""
    return {entry['key']: entry for entry in glossary_entries()}


def set_glossary_terms(updates):
    """Apply {key: {singular, plural}} from staff."""
    ensure_default_glossary()
    for key, values in updates.items():
        if key not in GLOSSARY_KEYS or not isinstance(values, dict):
            continue
        singular = (values.get('singular') or '').strip()
        plural = (values.get('plural') or '').strip()
        if not singular or not plural:
            continue
        StudioGlossary.objects.filter(key=key).update(singular=singular, plural=plural)
    return glossary_entries()
