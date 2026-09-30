"""Class catalog helpers."""

from django.db.models import Q

from scheduling.models import ClassTopic


def offering_visible_to_student(offering, student):
    """Studio-path classes are public; personalized tracks require enrollment."""
    if offering is None or not offering.track_id:
        return True
    if offering.track.is_template:
        return True
    from scheduling.models import StudentCurriculum

    return StudentCurriculum.objects.filter(
        student=student, track_id=offering.track_id, is_active=True,
    ).exists()


def visible_offerings(queryset, student):
    """Hide personalized-track classes from students who are not enrolled on them."""
    from scheduling.models import StudentCurriculum

    enrolled = list(
        StudentCurriculum.objects.filter(student=student, is_active=True).values_list('track_id', flat=True)
    )
    personalized = Q(track__isnull=False, track__is_template=False)
    return queryset.filter(~personalized | Q(track_id__in=enrolled))


def apply_track_to_offering(offering, track):
    """Copy track labels onto the bookable class. A track is always ordered."""
    offering.track = track
    offering.subject = (track.subject or 'Custom')[:100]
    offering.level = (track.cefr_band or ('' if track.is_template else 'Personalized'))[:100]
    offering.focus = track.title[:150]
    offering.topics_ordered = True
    return offering


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
    track = fields.pop('track', None)
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
    if track is not None:
        apply_track_to_offering(offering, track)
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
