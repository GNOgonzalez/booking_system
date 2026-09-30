"""Session creation helpers."""

from django.db.models import Count, Prefetch, Q

from scheduling.models import Booking, ClassOffering, ClassTopic, CurriculumModule, SessionCheckIn


def visible_open_sessions(queryset, student):
    """Hide personalized-track classes from students who are not enrolled on them."""
    from scheduling.models import StudentCurriculum

    enrolled = StudentCurriculum.objects.filter(student=student, is_active=True).values_list('track_id', flat=True)
    personalized = Q(
        class_offering__track__isnull=False,
        class_offering__track__is_template=False,
    )
    return queryset.filter(~personalized | Q(class_offering__track_id__in=list(enrolled)))


def annotate_confirmed_count(queryset):
    """One SQL COUNT per session row — avoids N+1 in session list APIs."""
    return queryset.annotate(
        confirmed_count=Count('bookings', filter=Q(bookings__status='confirmed')),
    )


def sessions_for_list(queryset):
    """List queryset with common select_related + confirmed bookings, no N+1."""
    confirmed = Booking.objects.filter(status='confirmed').select_related('student')
    return annotate_confirmed_count(
        queryset.select_related(
            'teacher', 'class_offering', 'class_offering__track', 'class_topic', 'curriculum_module', 'branch',
        ).prefetch_related(
            Prefetch('bookings', queryset=confirmed, to_attr='confirmed_bookings'),
            Prefetch('check_ins', queryset=SessionCheckIn.objects.select_related('user')),
        ),
    )


def session_display_title(offering, lesson=None):
    base = offering.display_name
    if lesson is not None:
        return f"{base} · {lesson.title}"
    return base


def apply_session_defaults(session):
    """Derive title and capacity from the linked class offering when missing."""
    offering = session.class_offering
    if offering is None:
        return session

    if not session.title:
        lesson = session.curriculum_module or session.class_topic
        session.title = session_display_title(offering, lesson)
    if session.capacity in (None, 0, 1) and offering.default_capacity:
        session.capacity = offering.default_capacity
    return session


def class_offering_belongs_to_teacher(offering_id, teacher):
    if offering_id is None:
        return False
    return ClassOffering.objects.filter(pk=offering_id, teacher=teacher, is_active=True).exists()


def class_topic_belongs_to_offering(topic_id, offering):
    if topic_id is None or offering is None:
        return False
    return ClassTopic.objects.filter(pk=topic_id, class_offering=offering).exists()


def module_belongs_to_offering(module_id, offering):
    if module_id is None or offering is None or not offering.track_id:
        return False
    return CurriculumModule.objects.filter(pk=module_id, track_id=offering.track_id).exists()


def update_session(
    session,
    teacher,
    *,
    class_offering=None,
    class_topic=None,
    curriculum_module=None,
    start_time=None,
    end_time=None,
    capacity=None,
):
    if session.teacher_id != teacher.id:
        return False, 'Session not found.'
    if session.status == 'cancelled':
        return False, 'Cancelled sessions cannot be edited.'

    if class_offering is not None:
        if not class_offering_belongs_to_teacher(class_offering.id, teacher):
            return False, 'Class not found in your catalog.'
        session.class_offering = class_offering
        if class_topic is not None and not class_topic_belongs_to_offering(class_topic.id, class_offering):
            return False, 'Topic not found in this class.'
        session.class_topic = class_topic
        if curriculum_module is not None and not module_belongs_to_offering(curriculum_module.id, class_offering):
            return False, 'That lesson is not on this curriculum.'
        if curriculum_module is not None:
            session.curriculum_module = curriculum_module
        session.title = session_display_title(class_offering, curriculum_module or class_topic)
    elif class_topic is not None or curriculum_module is not None:
        offering = session.class_offering
        if class_topic is not None and not class_topic_belongs_to_offering(class_topic.id, offering):
            return False, 'Topic not found in this class.'
        if class_topic is not None:
            session.class_topic = class_topic
        if curriculum_module is not None and not module_belongs_to_offering(curriculum_module.id, offering):
            return False, 'That lesson is not on this curriculum.'
        if curriculum_module is not None:
            session.curriculum_module = curriculum_module
        session.title = session_display_title(offering, curriculum_module or class_topic)
    if start_time is not None:
        session.start_time = start_time
    if end_time is not None:
        session.end_time = end_time
    if capacity is not None:
        session.capacity = capacity

    session.save()

    from scheduling.services.meetings import sync_meeting_update
    sync_meeting_update(session)
    return True, None


def cancel_session(session, teacher):
    if session.teacher_id != teacher.id:
        return False, 'Session not found.'
    if session.status == 'cancelled':
        return False, 'Session is already cancelled.'
    session.status = 'cancelled'
    session.save(update_fields=['status'])

    from scheduling.services.meetings import sync_meeting_cancel
    sync_meeting_cancel(session)
    return True, None
