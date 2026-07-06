"""Student class requests during teacher availability — hold tickets until approved."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Min
from django.utils import timezone

from scheduling.models import ClassOffering, ClassRequest, Session
from scheduling.services.availability import session_within_availability, times_overlap
from scheduling.services.meetings import create_meeting_link
from scheduling.services.membership import (
    _membership_allows_class,
    active_memberships_for,
    allowed_class_ids_for_user,
    has_active_membership,
)
from scheduling.services.notifications import notify_booking_created
from scheduling.services.sessions import class_topic_belongs_to_offering, session_display_title
from scheduling.services.tickets import hold_tickets, release_tickets
from scheduling.services.timezones import combine_in_teacher_tz

User = get_user_model()


def _teacher_queryset():
    return User.objects.filter(groups__name='teacher', is_active=True)


def _allowed_offerings_queryset(user):
    allowed_ids = allowed_class_ids_for_user(user)
    qs = ClassOffering.objects.filter(is_active=True)
    if allowed_ids is not None:
        if not allowed_ids:
            return ClassOffering.objects.none()
        qs = qs.filter(pk__in=allowed_ids)
    return qs


def teachers_for_student_requests(user):
    """Active teachers with availability whose classes the student may book."""
    if not has_active_membership(user):
        return User.objects.none()
    allowed_ids = allowed_class_ids_for_user(user)
    qs = _teacher_queryset().filter(class_offerings__is_active=True).distinct()
    if allowed_ids is not None:
        if not allowed_ids:
            return User.objects.none()
        qs = qs.filter(class_offerings__id__in=allowed_ids)
    from scheduling.services.availability import teacher_has_availability_blocks

    return [teacher for teacher in qs.order_by('username') if teacher_has_availability_blocks(teacher)]


def open_class_profiles_for_student(user):
    """Distinct subject/level/focus profiles bookable across any eligible teacher."""
    if not has_active_membership(user):
        return []
    from scheduling.services.availability import teacher_has_availability_blocks

    allowed = _allowed_offerings_queryset(user).select_related('teacher')
    profiles = {}
    for offering in allowed.order_by('subject', 'level', 'focus', 'teacher__username'):
        teacher = offering.teacher
        if not teacher_has_availability_blocks(teacher):
            continue
        key = (offering.subject, offering.level, offering.focus)
        row = profiles.get(key)
        if row is None:
            profiles[key] = {
                'subject': offering.subject,
                'level': offering.level,
                'focus': offering.focus,
                'label': offering.display_name,
                'min_ticket_cost': offering.ticket_cost or 1,
                'teacher_count': 1,
            }
        else:
            row['teacher_count'] += 1
            row['min_ticket_cost'] = min(row['min_ticket_cost'], offering.ticket_cost or 1)
    return list(profiles.values())


def teachers_for_open_profile(user, subject, level, focus):
    """Teachers with availability who teach the given class profile."""
    if not has_active_membership(user):
        return []
    from scheduling.services.availability import teacher_has_availability_blocks

    allowed = _allowed_offerings_queryset(user).filter(
        subject=subject,
        level=level,
        focus=focus,
    )
    teacher_ids = allowed.values_list('teacher_id', flat=True).distinct()
    teachers = []
    for teacher in _teacher_queryset().filter(pk__in=teacher_ids).order_by('username'):
        if teacher_has_availability_blocks(teacher):
            teachers.append(teacher)
    return teachers


def classes_for_teacher_request(user, teacher):
    allowed_ids = allowed_class_ids_for_user(user)
    qs = ClassOffering.objects.filter(teacher=teacher, is_active=True).prefetch_related('topics')
    if allowed_ids is not None:
        qs = qs.filter(pk__in=allowed_ids)
    return qs.order_by('subject', 'level', 'focus')


def membership_for_class_request(user, class_offering, tickets):
    for membership in active_memberships_for(user):
        if not _membership_allows_class(membership, class_offering):
            continue
        if membership.tickets_remaining >= tickets:
            return membership
    return None


def membership_for_open_class_request(user, subject, level, focus, tickets):
    qs = _allowed_offerings_queryset(user).filter(subject=subject, level=level, focus=focus)
    for offering in qs:
        membership = membership_for_class_request(user, offering, tickets)
        if membership is not None:
            return membership
    return None


def min_tickets_for_open_profile(user, subject, level, focus):
    qs = _allowed_offerings_queryset(user).filter(subject=subject, level=level, focus=focus)
    value = qs.aggregate(min_cost=Min('ticket_cost'))['min_cost']
    return value or 1


def _occupied_intervals(teacher, *, exclude_request_id=None):
    """Open sessions and pending requests that block a time slot."""
    now = timezone.now()
    intervals = []
    for session in Session.objects.filter(teacher=teacher, status='open', end_time__gt=now):
        intervals.append((session.start_time, session.end_time, 'session', session.id))
    pending = ClassRequest.objects.filter(teacher=teacher, status=ClassRequest.STATUS_PENDING)
    if exclude_request_id:
        pending = pending.exclude(pk=exclude_request_id)
    for request in pending:
        intervals.append((request.start_time, request.end_time, 'pending_request', request.id))
    return intervals


def slot_is_available(teacher, start_time, end_time, *, exclude_request_id=None):
    if start_time >= end_time:
        return False, 'End time must be after start time.'
    if start_time <= timezone.now():
        return False, 'Choose a future time.'
    if not session_within_availability(teacher, start_time, end_time):
        return False, 'That time is outside the teacher\'s availability.'
    for busy_start, busy_end, _, _ in _occupied_intervals(teacher, exclude_request_id=exclude_request_id):
        if times_overlap(start_time, end_time, busy_start, busy_end):
            return False, 'That time slot is no longer available.'
    return True, None


def open_slot_is_available(user, subject, level, focus, start_time, end_time):
    if start_time >= end_time:
        return False, 'End time must be after start time.'
    if start_time <= timezone.now():
        return False, 'Choose a future time.'
    teachers = teachers_for_open_profile(user, subject, level, focus)
    if not teachers:
        return False, 'No teachers are available for this class.'
    for teacher in teachers:
        ok, _ = slot_is_available(teacher, start_time, end_time)
        if ok:
            return True, None
    return False, 'No teacher is available at that time.'


def _open_request_matches_teacher(request, teacher):
    if not request.open_to_any_teacher:
        return False
    return ClassOffering.objects.filter(
        teacher=teacher,
        is_active=True,
        subject=request.subject,
        level=request.level,
        focus=request.focus,
    ).exists()


def teacher_can_access_request(teacher, request):
    if request.teacher_id == teacher.id:
        return True
    if request.open_to_any_teacher and request.teacher_id is None and request.status == ClassRequest.STATUS_PENDING:
        return _open_request_matches_teacher(request, teacher)
    return False


def matching_offering_for_teacher(teacher, request):
    return ClassOffering.objects.filter(
        teacher=teacher,
        is_active=True,
        subject=request.subject,
        level=request.level,
        focus=request.focus,
    ).order_by('subject', 'level', 'focus').first()


def availability_snapshot(teacher, *, days=28):
    """Availability windows and busy intervals for the next N days."""
    from scheduling.models import AvailabilityBlock, SpecialAvailability

    now = timezone.now()
    end_date = (now + timedelta(days=days)).date()
    windows = []

    for block in AvailabilityBlock.objects.filter(teacher=teacher).order_by('weekday', 'start_time'):
        day = now.date()
        while day <= end_date:
            if day.weekday() == block.weekday:
                start = combine_in_teacher_tz(teacher, day, block.start_time)
                end = combine_in_teacher_tz(teacher, day, block.end_time)
                if end > now:
                    windows.append({
                        'date': day.isoformat(),
                        'start_time': block.start_time.isoformat(timespec='minutes'),
                        'end_time': block.end_time.isoformat(timespec='minutes'),
                        'start': start.isoformat(),
                        'end': end.isoformat(),
                        'kind': 'weekly',
                    })
            day += timedelta(days=1)

    for block in SpecialAvailability.objects.filter(teacher=teacher, date__gte=now.date(), date__lte=end_date):
        start = combine_in_teacher_tz(teacher, block.date, block.start_time)
        end = combine_in_teacher_tz(teacher, block.date, block.end_time)
        if end > now:
            windows.append({
                'date': block.date.isoformat(),
                'start_time': block.start_time.isoformat(timespec='minutes'),
                'end_time': block.end_time.isoformat(timespec='minutes'),
                'start': start.isoformat(),
                'end': end.isoformat(),
                'kind': 'special',
                'note': block.note,
            })

    busy = []
    for start, end, kind, obj_id in _occupied_intervals(teacher):
        busy.append({
            'start': start.isoformat(),
            'end': end.isoformat(),
            'kind': kind,
            'id': obj_id,
        })

    return {'windows': windows, 'busy': busy}


def open_availability_snapshot(user, subject, level, focus, *, days=28):
    """Merged availability windows and slots across teachers for an open class profile."""
    from scheduling.services.scheduling_slots import scheduling_slot_options

    teachers = teachers_for_open_profile(user, subject, level, focus)
    windows = []
    busy = []
    slots = []
    seen_slots = set()
    for teacher in teachers:
        snapshot = availability_snapshot(teacher, days=days)
        windows.extend(snapshot['windows'])
        busy.extend(snapshot['busy'])
        for slot in scheduling_slot_options(teacher, days=days):
            key = slot['start']
            if key not in seen_slots:
                seen_slots.add(key)
                slots.append(slot)
    windows.sort(key=lambda item: item['start'])
    busy.sort(key=lambda item: item['start'])
    slots.sort(key=lambda item: item['start'])
    return {'windows': windows, 'busy': busy, 'slots': slots}


def create_class_request(
    user,
    *,
    teacher,
    class_offering,
    class_topic=None,
    start_time,
    end_time,
    tickets_requested,
):
    if not user.groups.filter(name='student').exists() or not user.is_active:
        return None, 'Only active students can request classes.'
    if not has_active_membership(user):
        return None, 'Active membership required.'
    if teacher is None or not _teacher_queryset().filter(pk=teacher.pk).exists():
        return None, 'Teacher not found.'
    if class_offering.teacher_id != teacher.id:
        return None, 'That class is not offered by this teacher.'
    if not class_offering.is_active:
        return None, 'That class is no longer available.'
    if class_topic is not None and not class_topic_belongs_to_offering(class_topic.id, class_offering):
        return None, 'Topic not found in this class.'
    min_tickets = class_offering.ticket_cost or 1
    if tickets_requested < min_tickets:
        return None, f'At least {min_tickets} ticket(s) required for this class.'

    ok, error = slot_is_available(teacher, start_time, end_time)
    if not ok:
        return None, error

    membership = membership_for_class_request(user, class_offering, tickets_requested)
    if membership is None:
        return None, 'Not enough tickets or class not included in your membership.'

    if ClassRequest.objects.filter(
        student=user,
        teacher=teacher,
        status=ClassRequest.STATUS_PENDING,
        start_time=start_time,
        end_time=end_time,
    ).exists():
        return None, 'You already have a pending request for this time.'

    if not hold_tickets(membership, tickets_requested):
        return None, 'Not enough tickets available.'

    request = ClassRequest.objects.create(
        student=user,
        teacher=teacher,
        class_offering=class_offering,
        class_topic=class_topic,
        start_time=start_time,
        end_time=end_time,
        tickets_requested=tickets_requested,
        membership=membership,
        status=ClassRequest.STATUS_PENDING,
    )
    return request, None


def create_open_class_request(
    user,
    *,
    subject,
    level,
    focus,
    start_time,
    end_time,
    tickets_requested,
):
    if not user.groups.filter(name='student').exists() or not user.is_active:
        return None, 'Only active students can request classes.'
    if not has_active_membership(user):
        return None, 'Active membership required.'
    if not subject or not level or not focus:
        return None, 'Class profile is required.'
    if not teachers_for_open_profile(user, subject, level, focus):
        return None, 'No teachers are available for this class.'

    min_tickets = min_tickets_for_open_profile(user, subject, level, focus)
    if tickets_requested < min_tickets:
        return None, f'At least {min_tickets} ticket(s) required for this class.'

    ok, error = open_slot_is_available(user, subject, level, focus, start_time, end_time)
    if not ok:
        return None, error

    membership = membership_for_open_class_request(user, subject, level, focus, tickets_requested)
    if membership is None:
        return None, 'Not enough tickets or class not included in your membership.'

    if ClassRequest.objects.filter(
        student=user,
        open_to_any_teacher=True,
        teacher__isnull=True,
        status=ClassRequest.STATUS_PENDING,
        subject=subject,
        level=level,
        focus=focus,
        start_time=start_time,
        end_time=end_time,
    ).exists():
        return None, 'You already have a pending request for this time.'

    if not hold_tickets(membership, tickets_requested):
        return None, 'Not enough tickets available.'

    request = ClassRequest.objects.create(
        student=user,
        teacher=None,
        open_to_any_teacher=True,
        subject=subject,
        level=level,
        focus=focus,
        class_offering=None,
        class_topic=None,
        start_time=start_time,
        end_time=end_time,
        tickets_requested=tickets_requested,
        membership=membership,
        status=ClassRequest.STATUS_PENDING,
    )
    return request, None


def update_pending_request(request, teacher, **fields):
    if not teacher_can_access_request(teacher, request) or request.status != ClassRequest.STATUS_PENDING:
        return None, 'Request not found.'

    class_offering = fields.get('class_offering', request.class_offering)
    class_topic = fields.get('class_topic', request.class_topic)
    start_time = fields.get('start_time', request.start_time)
    end_time = fields.get('end_time', request.end_time)

    if request.open_to_any_teacher and request.teacher_id is None:
        if class_offering is None:
            class_offering = matching_offering_for_teacher(teacher, request)
        if class_offering is None or class_offering.teacher_id != teacher.id:
            return None, 'Class not found in your catalog.'
        if (
            class_offering.subject != request.subject
            or class_offering.level != request.level
            or class_offering.focus != request.focus
        ):
            return None, 'Class not found in your catalog.'
    elif class_offering.teacher_id != teacher.id or not class_offering.is_active:
        return None, 'Class not found in your catalog.'
    if class_topic is not None and not class_topic_belongs_to_offering(class_topic.id, class_offering):
        return None, 'Topic not found in this class.'

    ok, error = slot_is_available(teacher, start_time, end_time, exclude_request_id=request.id)
    if not ok:
        return None, error

    if not request.open_to_any_teacher or request.teacher_id:
        request.class_offering = class_offering
        request.class_topic = class_topic
    request.start_time = start_time
    request.end_time = end_time
    request.save()
    return request, None


def _release_request_tickets(request):
    release_tickets(request.membership, request.tickets_requested)


def cancel_pending_request(user, request):
    if request.status != ClassRequest.STATUS_PENDING:
        return False, 'Only pending requests can be cancelled.'
    if request.student_id != user.id:
        return False, 'Request not found.'
    _release_request_tickets(request)
    request.status = ClassRequest.STATUS_CANCELLED
    request.save(update_fields=['status', 'updated_at'])
    return True, None


def deny_class_request(teacher, request):
    if request.teacher_id != teacher.id or request.status != ClassRequest.STATUS_PENDING:
        return False, 'Request not found.'
    _release_request_tickets(request)
    request.status = ClassRequest.STATUS_DENIED
    request.save(update_fields=['status', 'updated_at'])
    return True, None


def delete_class_request(teacher, request):
    """Delete a pending or denied request — refunds tickets if still pending."""
    if request.teacher_id != teacher.id:
        return False, 'Request not found.'
    if request.status == ClassRequest.STATUS_PENDING:
        _release_request_tickets(request)
    elif request.status not in (ClassRequest.STATUS_DENIED, ClassRequest.STATUS_CANCELLED):
        return False, 'Approved requests cannot be deleted.'
    request.delete()
    return True, None


def approve_class_request(teacher, request, *, capacity=None):
    if not teacher_can_access_request(teacher, request) or request.status != ClassRequest.STATUS_PENDING:
        return None, 'Request not found.'

    if request.open_to_any_teacher and request.teacher_id is None:
        offering = matching_offering_for_teacher(teacher, request)
        if offering is None:
            return None, 'Class not found in your catalog.'
        request.teacher = teacher
        request.class_offering = offering
        request.save(update_fields=['teacher', 'class_offering', 'updated_at'])

    ok, error = slot_is_available(
        teacher,
        request.start_time,
        request.end_time,
        exclude_request_id=request.id,
    )
    if not ok:
        return None, error

    offering = request.class_offering
    topic = request.class_topic
    session = Session.objects.create(
        teacher=teacher,
        class_offering=offering,
        class_topic=topic,
        title=session_display_title(offering, topic),
        start_time=request.start_time,
        end_time=request.end_time,
        capacity=capacity or offering.default_capacity or 1,
        status='open',
    )
    session.meeting_url = create_meeting_link(session)
    session.save(update_fields=['meeting_url'])

    from scheduling.models import Booking

    booking = Booking.objects.create(
        student=request.student,
        session=session,
        membership=request.membership,
        status='confirmed',
        tickets_spent=request.tickets_requested,
        class_request=request,
    )
    request.status = ClassRequest.STATUS_APPROVED
    request.session = session
    request.save(update_fields=['status', 'session', 'updated_at'])
    notify_booking_created(booking)
    return request, None


def pending_requests_for_teacher(teacher):
    specific_ids = set(
        ClassRequest.objects.filter(
            teacher=teacher,
            status=ClassRequest.STATUS_PENDING,
        ).values_list('pk', flat=True)
    )
    open_ids = [
        request.pk
        for request in ClassRequest.objects.filter(
            open_to_any_teacher=True,
            teacher__isnull=True,
            status=ClassRequest.STATUS_PENDING,
        )
        if _open_request_matches_teacher(request, teacher)
    ]
    all_ids = list(specific_ids | set(open_ids))
    return (
        ClassRequest.objects.filter(pk__in=all_ids)
        .select_related('student', 'class_offering', 'class_topic', 'membership')
    )


def requests_for_student(user):
    return (
        ClassRequest.objects.filter(student=user)
        .exclude(status=ClassRequest.STATUS_DENIED)
        .select_related('teacher', 'class_offering', 'class_topic', 'session')
    )
