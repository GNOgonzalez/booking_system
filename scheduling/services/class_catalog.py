"""Studio class roadmap — subject → level → focus → topics."""

from scheduling.models import (
    CatalogFocus,
    CatalogLevel,
    CatalogSubject,
    CatalogTopic,
    ClassOffering,
    ClassTopic,
    MembershipPlan,
)

CATALOG_KINDS = ('subject', 'level', 'focus', 'topic')

_KIND_MODELS = {
    'subject': CatalogSubject,
    'level': CatalogLevel,
    'focus': CatalogFocus,
    'topic': CatalogTopic,
}


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


def _name_field(kind):
    return 'title' if kind == 'topic' else 'name'


def get_catalog_node(kind, node_id):
    model = _KIND_MODELS.get(kind)
    if model is None:
        return None
    return model.objects.filter(pk=node_id).first()


def _node_summary(kind, node):
    return {
        'kind': kind,
        'id': node.id,
        'name': getattr(node, _name_field(kind)),
        'is_active': node.is_active,
    }


def _offerings_for_node(kind, node):
    """Teacher classes that reference this roadmap entry (matched on stored names)."""
    if kind == 'subject':
        return ClassOffering.objects.filter(subject__iexact=node.name)
    if kind == 'level':
        return ClassOffering.objects.filter(
            subject__iexact=node.subject.name,
            level__iexact=node.name,
        )
    if kind == 'focus':
        level = node.level
        return ClassOffering.objects.filter(
            subject__iexact=level.subject.name,
            level__iexact=level.name,
            focus__iexact=node.name,
        )
    return ClassOffering.objects.none()


def _class_topics_for_topic(topic):
    return ClassTopic.objects.filter(
        class_offering__in=_offerings_for_node('focus', topic.focus),
        title__iexact=topic.title,
    )


def catalog_node_usage(kind, node):
    """How many teacher classes (or class topics) depend on this roadmap entry."""
    if kind == 'topic':
        return _class_topics_for_topic(node).count()
    return _offerings_for_node(kind, node).count()


def catalog_node_children(kind, node):
    if kind == 'subject':
        return node.levels.count()
    if kind == 'level':
        return node.focuses.count()
    if kind == 'focus':
        return node.topics.count()
    return 0


def _sibling_name_taken(kind, node, name):
    model = _KIND_MODELS[kind]
    if kind == 'subject':
        siblings = model.objects.filter(name__iexact=name)
    elif kind == 'level':
        siblings = model.objects.filter(subject=node.subject, name__iexact=name)
    elif kind == 'focus':
        siblings = model.objects.filter(level=node.level, name__iexact=name)
    else:
        siblings = model.objects.filter(focus=node.focus, title__iexact=name)
    return siblings.exclude(pk=node.pk).exists()


def rename_catalog_node(kind, node_id, new_name):
    """Rename a roadmap entry and keep already-created teacher classes in sync."""
    node = get_catalog_node(kind, node_id)
    if node is None:
        return None, 'Roadmap entry not found.'
    new_name = (new_name or '').strip()
    if not new_name:
        return None, 'Name is required.'

    field = _name_field(kind)
    if getattr(node, field) == new_name:
        return _node_summary(kind, node), None
    if _sibling_name_taken(kind, node, new_name):
        return None, f'"{new_name}" already exists here.'

    if kind == 'topic':
        _class_topics_for_topic(node).update(title=new_name)
    else:
        _offerings_for_node(kind, node).update(**{kind: new_name})

    setattr(node, field, new_name)
    node.save(update_fields=[field])
    return _node_summary(kind, node), None


def set_catalog_node_active(kind, node_id, is_active):
    """Hide or restore a roadmap entry without touching existing classes."""
    node = get_catalog_node(kind, node_id)
    if node is None:
        return None, 'Roadmap entry not found.'
    node.is_active = bool(is_active)
    node.save(update_fields=['is_active'])
    return _node_summary(kind, node), None


def delete_catalog_node(kind, node_id):
    """Remove a roadmap mistake. Blocked while teacher classes still reference it."""
    node = get_catalog_node(kind, node_id)
    if node is None:
        return None, 'Roadmap entry not found.'

    usage = catalog_node_usage(kind, node)
    if usage:
        noun = 'class' if usage == 1 else 'classes'
        return None, (
            f'{usage} {noun} still use this roadmap entry. '
            'Deactivate it instead, or remove those classes first.'
        )
    if kind == 'subject' and MembershipPlan.objects.filter(subject__iexact=node.name).exists():
        return None, (
            'A membership plan is scoped to this subject. '
            'Update the plan first, or deactivate the subject instead.'
        )

    summary = _node_summary(kind, node)
    node.delete()
    return summary, None


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
