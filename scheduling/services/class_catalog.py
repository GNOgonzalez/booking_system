"""Studio class roadmap — subject → level → focus → topics."""

from scheduling.models import CatalogFocus, CatalogLevel, CatalogSubject, CatalogTopic


def _serialize_topic(topic):
    return {
        'id': topic.id,
        'title': topic.title,
        'sort_order': topic.sort_order,
        'is_active': topic.is_active,
    }


def _serialize_focus(focus, *, include_inactive=False):
    topics = focus.topics.all()
    if not include_inactive:
        topics = topics.filter(is_active=True)
    return {
        'id': focus.id,
        'name': focus.name,
        'sort_order': focus.sort_order,
        'is_active': focus.is_active,
        'topics': [_serialize_topic(topic) for topic in topics],
    }


def _serialize_level(level, *, include_inactive=False):
    focuses = level.focuses.all()
    if not include_inactive:
        focuses = focuses.filter(is_active=True)
    return {
        'id': level.id,
        'name': level.name,
        'sort_order': level.sort_order,
        'is_active': level.is_active,
        'focuses': [_serialize_focus(focus, include_inactive=include_inactive) for focus in focuses],
    }


def _serialize_subject(subject, *, include_inactive=False):
    levels = subject.levels.all()
    if not include_inactive:
        levels = levels.filter(is_active=True)
    return {
        'id': subject.id,
        'name': subject.name,
        'sort_order': subject.sort_order,
        'is_active': subject.is_active,
        'levels': [_serialize_level(level, include_inactive=include_inactive) for level in levels],
    }


def catalog_tree(*, include_inactive=False):
    subjects = CatalogSubject.objects.all()
    if not include_inactive:
        subjects = subjects.filter(is_active=True)
    return [_serialize_subject(subject, include_inactive=include_inactive) for subject in subjects]


def create_catalog_subject(name):
    name = (name or '').strip()
    if not name:
        return None, 'Subject name is required.'
    subject, _ = CatalogSubject.objects.get_or_create(name=name, defaults={'is_active': True})
    if not subject.is_active:
        subject.is_active = True
        subject.save(update_fields=['is_active'])
    return subject, None


def create_catalog_level(subject_id, name):
    name = (name or '').strip()
    if not name:
        return None, 'Level name is required.'
    subject = CatalogSubject.objects.filter(pk=subject_id).first()
    if subject is None:
        return None, 'Subject not found.'
    level, _ = CatalogLevel.objects.get_or_create(
        subject=subject,
        name=name,
        defaults={'is_active': True},
    )
    if not level.is_active:
        level.is_active = True
        level.save(update_fields=['is_active'])
    return level, None


def create_catalog_focus(level_id, name):
    name = (name or '').strip()
    if not name:
        return None, 'Focus name is required.'
    level = CatalogLevel.objects.filter(pk=level_id).first()
    if level is None:
        return None, 'Level not found.'
    focus, _ = CatalogFocus.objects.get_or_create(
        level=level,
        name=name,
        defaults={'is_active': True},
    )
    if not focus.is_active:
        focus.is_active = True
        focus.save(update_fields=['is_active'])
    return focus, None


def _parse_topic_lines(raw):
    if raw is None:
        return []
    if isinstance(raw, str):
        lines = raw.replace('\r\n', '\n').split('\n')
    else:
        lines = list(raw)
    titles = []
    seen = set()
    for line in lines:
        title = str(line).strip()
        if not title:
            continue
        key = title.casefold()
        if key in seen:
            continue
        seen.add(key)
        titles.append(title)
    return titles


def bulk_add_catalog_topics(focus_id, raw_topics):
    focus = CatalogFocus.objects.filter(pk=focus_id).first()
    if focus is None:
        return None, 'Focus not found.'
    titles = _parse_topic_lines(raw_topics)
    if not titles:
        return None, 'Add at least one topic (one per line).'

    existing = {
        topic.title.casefold(): topic
        for topic in focus.topics.all()
    }
    next_order = focus.topics.order_by('-sort_order').values_list('sort_order', flat=True).first()
    next_order = 0 if next_order is None else next_order + 1
    created = []
    for title in titles:
        key = title.casefold()
        topic = existing.get(key)
        if topic is not None:
            if not topic.is_active:
                topic.is_active = True
                topic.save(update_fields=['is_active'])
            created.append(topic)
            continue
        topic = CatalogTopic.objects.create(
            focus=focus,
            title=title,
            sort_order=next_order,
            is_active=True,
        )
        existing[key] = topic
        created.append(topic)
        next_order += 1
    return [_serialize_topic(topic) for topic in created], None


def ensure_default_catalog():
    """Seed roadmap entries used by demo classes."""
    specs = [
        (
            'Japanese',
            'Beginner',
            'Grammar and Vocabulary',
            ['Present Tense Verbs', 'Hiragana Review'],
        ),
        ('Japanese', 'Beginner', 'Reading', ['Short Dialogues']),
        ('Japanese', 'Beginner', 'Speaking', ['Pronunciation Drills']),
        ('Japanese', 'Beginner', 'Listening', ['Greetings and Introductions']),
        ('Japanese', 'Intermediate', 'Conversation', ['Daily Routines']),
        ('Japanese', 'Advanced', 'Writing', ['Formal Email']),
        ('English', 'Beginner', 'Grammar', ['Present Simple', 'Articles', 'Questions']),
        ('English', 'Beginner', 'Speaking', ['Conversation Practice']),
        ('English', 'Intermediate', 'Writing', ['Essay Structure']),
        ('English', 'Advanced', 'Events', ['Workshop: Public Speaking']),
    ]
    for subject_name, level_name, focus_name, topics in specs:
        subject, _ = create_catalog_subject(subject_name)
        level, _ = create_catalog_level(subject.id, level_name)
        focus, _ = create_catalog_focus(level.id, focus_name)
        bulk_add_catalog_topics(focus.id, topics)
