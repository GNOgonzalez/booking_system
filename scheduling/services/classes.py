"""Class catalog helpers."""

from scheduling.models import ClassTopic


def sync_class_topics(offering, topics_data):
    """Replace the topic list on an offering."""
    if topics_data is None:
        return
    kept_ids = []
    for index, item in enumerate(topics_data):
        title = (item.get('title') or '').strip()
        if not title:
            continue
        sort_order = item.get('sort_order', index)
        topic_id = item.get('id')
        if topic_id:
            topic = ClassTopic.objects.filter(pk=topic_id, class_offering=offering).first()
            if topic is not None:
                topic.title = title
                topic.sort_order = sort_order
                topic.save(update_fields=['title', 'sort_order'])
                kept_ids.append(topic.id)
                continue
        topic = ClassTopic.objects.create(
            class_offering=offering,
            title=title,
            sort_order=sort_order,
        )
        kept_ids.append(topic.id)
    ClassTopic.objects.filter(class_offering=offering).exclude(pk__in=kept_ids).delete()


def update_class_offering(offering, teacher, **fields):
    topics = fields.pop('topics', None)
    allowed = {
        'subject',
        'level',
        'focus',
        'topics_ordered',
        'default_capacity',
        'ticket_cost',
        'is_active',
    }
    for key, value in fields.items():
        if key in allowed:
            setattr(offering, key, value)
    if offering.teacher_id != teacher.id:
        return False
    offering.save()
    if topics is not None:
        sync_class_topics(offering, topics)
    return True


def deactivate_class_offering(offering, teacher):
    if offering.teacher_id != teacher.id:
        return False
    offering.is_active = False
    offering.save(update_fields=['is_active'])
    return True
