"""Student class requests during teacher availability — hold tickets until approved."""

from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
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
from scheduling.services.notifications import send_booking_confirmation
from scheduling.services.sessions import class_topic_belongs_to_offering, session_display_title
from scheduling.services.tickets import hold_tickets, release_tickets

User = get_user_model()


def _teacher_queryset():
    return User.objects.filter(groups__name='teacher', is_active=True)


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
                start = timezone.make_aware(datetime.combine(day, block.start_time))
                end = timezone.make_aware(datetime.combine(day, block.end_time))
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
        start = timezone.make_aware(datetime.combine(block.date, block.start_time))
        end = timezone.make_aware(datetime.combine(block.date, block.end_time))
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
    if class_offering.teacher_id != teacher.id or not class_offering.is_active:
        return None, 'Class not found for this teacher.'
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


def update_pending_request(request, teacher, **fields):
    if request.teacher_id != teacher.id or request.status != ClassRequest.STATUS_PENDING:
        return None, 'Request not found.'

    class_offering = fields.get('class_offering', request.class_offering)
    class_topic = fields.get('class_topic', request.class_topic)
    start_time = fields.get('start_time', request.start_time)
    end_time = fields.get('end_time', request.end_time)

    if class_offering.teacher_id != teacher.id or not class_offering.is_active:
        return None, 'Class not found in your catalog.'
    if class_topic is not None and not class_topic_belongs_to_offering(class_topic.id, class_offering):
        return None, 'Topic not found in this class.'

    ok, error = slot_is_available(teacher, start_time, end_time, exclude_request_id=request.id)
    if not ok:
        return None, error

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
    if request.teacher_id != teacher.id or request.status != ClassRequest.STATUS_PENDING:
        return None, 'Request not found.'

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
    send_booking_confirmation(booking)
    return request, None


def pending_requests_for_teacher(teacher):
    return (
        ClassRequest.objects.filter(teacher=teacher, status=ClassRequest.STATUS_PENDING)
        .select_related('student', 'class_offering', 'class_topic', 'membership')
    )


def requests_for_student(user):
    return (
        ClassRequest.objects.filter(student=user)
        .exclude(status=ClassRequest.STATUS_DENIED)
        .select_related('teacher', 'class_offering', 'class_topic', 'session')
    )
