"""Lesson check-in: staff-set window, record arrival, reminder emails."""

from datetime import timedelta

from django.db.models import Prefetch
from django.utils import timezone

from scheduling.models import Booking, Session, SessionCheckIn, StudioCheckInConfig
from scheduling.services.notifications import send_checkin_reminder


MAX_HOURS_BEFORE = 168


def get_checkin_config():
    return StudioCheckInConfig.load()


def serialize_checkin_config(config=None):
    config = config or get_checkin_config()
    return {
        'check_in_opens_hours_before': config.check_in_opens_hours_before,
        'reminder_hours_before': config.reminder_hours_before,
    }


def update_checkin_config(*, check_in_opens_hours_before=None, reminder_hours_before=None):
    config = get_checkin_config()
    opens = config.check_in_opens_hours_before
    reminder = config.reminder_hours_before
    if check_in_opens_hours_before is not None:
        try:
            opens = int(check_in_opens_hours_before)
        except (TypeError, ValueError):
            return None, 'Check-in opening time must be a whole number of hours.'
        if opens < 1 or opens > MAX_HOURS_BEFORE:
            return None, f'Check-in can open 1–{MAX_HOURS_BEFORE} hours before the lesson.'
    if reminder_hours_before is not None:
        try:
            reminder = int(reminder_hours_before)
        except (TypeError, ValueError):
            return None, 'Reminder time must be a whole number of hours.'
        if reminder < 0 or reminder > MAX_HOURS_BEFORE:
            return None, f'Reminder can be 0–{MAX_HOURS_BEFORE} hours before the lesson.'
    if reminder > opens:
        return None, 'The reminder must be at or after check-in opens (fewer or equal hours before start).'
    config.check_in_opens_hours_before = opens
    config.reminder_hours_before = reminder
    config.save()
    return config, None


def checkin_window(session, config=None):
    config = config or get_checkin_config()
    opens_at = session.start_time - timedelta(hours=config.check_in_opens_hours_before)
    closes_at = session.end_time
    return opens_at, closes_at


def participant_role(session, user):
    if not user or not user.is_authenticated:
        return None
    if session.teacher_id == user.id:
        return SessionCheckIn.ROLE_TEACHER
    bookings = getattr(session, 'confirmed_bookings', None)
    if bookings is not None:
        if any(booking.student_id == user.id for booking in bookings):
            return SessionCheckIn.ROLE_STUDENT
        return None
    if Booking.objects.filter(session=session, student=user, status='confirmed').exists():
        return SessionCheckIn.ROLE_STUDENT
    return None


def _row_for(session, user):
    cached = getattr(session, '_prefetched_objects_cache', {}).get('check_ins')
    if cached is not None:
        for row in cached:
            if row.user_id == user.id:
                return row
        return None
    return SessionCheckIn.objects.filter(session=session, user=user).first()


def check_in_payload(session, user, config=None):
    opens_at, closes_at = checkin_window(session, config)
    now = timezone.now()
    role = participant_role(session, user)
    row = _row_for(session, user) if user and user.is_authenticated else None
    checked_in_at = row.checked_in_at if row else None
    window_open = (
        session.status == 'open'
        and opens_at <= now <= closes_at
    )
    return {
        'eligible': role is not None,
        'role': role,
        'opens_at': opens_at,
        'closes_at': closes_at,
        'window_open': window_open,
        'can_check_in': role is not None and window_open and checked_in_at is None,
        'checked_in': checked_in_at is not None,
        'checked_in_at': checked_in_at,
    }


HOME_CHECKIN_LIMIT = 8


def _home_checkin_row(session, user, config, extra=None):
    row = {
        'session_id': session.id,
        'title': session.title,
        'start_time': session.start_time,
        'end_time': session.end_time,
        'check_in': check_in_payload(session, user, config),
    }
    if extra:
        row.update(extra)
    return row


def home_check_ins_for_student(user, *, limit=HOME_CHECKIN_LIMIT):
    """Upcoming and in-progress booked lessons the student can check in for."""
    now = timezone.now()
    config = get_checkin_config()
    bookings = (
        Booking.objects.filter(
            student=user,
            status='confirmed',
            session__status='open',
            session__end_time__gte=now,
        )
        .select_related('session', 'session__teacher', 'session__class_offering')
        .prefetch_related('session__check_ins')
        .order_by('session__start_time')[:limit]
    )
    return [
        _home_checkin_row(
            booking.session,
            user,
            config,
            {
                'teacher_name': booking.session.teacher.username if booking.session.teacher_id else '',
                'meeting_url': booking.session.meeting_url or '',
            },
        )
        for booking in bookings
    ]


def home_check_ins_for_teacher(teacher, *, limit=HOME_CHECKIN_LIMIT):
    """Upcoming and in-progress lessons the teacher should check in for."""
    now = timezone.now()
    config = get_checkin_config()
    sessions = (
        Session.objects.filter(teacher=teacher, status='open', end_time__gte=now)
        .select_related('class_offering')
        .prefetch_related(
            Prefetch(
                'bookings',
                queryset=Booking.objects.filter(status='confirmed').select_related('student'),
                to_attr='confirmed_bookings',
            ),
            Prefetch('check_ins', queryset=SessionCheckIn.objects.select_related('user')),
        )
        .order_by('start_time')[:limit]
    )
    rows = []
    for session in sessions:
        students = [booking.student.username for booking in session.confirmed_bookings]
        rows.append(_home_checkin_row(session, teacher, config, {'students': students}))
    return rows


def list_check_ins(session):
    cached = getattr(session, '_prefetched_objects_cache', {}).get('check_ins')
    rows = list(cached) if cached is not None else list(
        session.check_ins.select_related('user').all()
    )
    return [
        {
            'user_id': row.user_id,
            'username': row.user.username,
            'role': row.role,
            'checked_in_at': row.checked_in_at,
        }
        for row in rows
        if row.checked_in_at
    ]


def record_check_in(session, user):
    if session.status != 'open':
        return None, 'This session is not open.'
    role = participant_role(session, user)
    if role is None:
        return None, 'You are not on this lesson.'
    opens_at, closes_at = checkin_window(session)
    now = timezone.now()
    if now < opens_at:
        return None, 'Check-in is not open yet.'
    if now > closes_at:
        return None, 'This lesson has finished.'
    row, _ = SessionCheckIn.objects.get_or_create(
        session=session,
        user=user,
        defaults={'role': role},
    )
    if row.checked_in_at is None:
        row.role = role
        row.checked_in_at = now
        row.save(update_fields=['role', 'checked_in_at'])
    return row, None


def expected_participants(session):
    people = [(session.teacher, SessionCheckIn.ROLE_TEACHER)]
    bookings = getattr(session, 'confirmed_bookings', None)
    if bookings is None:
        bookings = session.bookings.filter(status='confirmed').select_related('student')
    for booking in bookings:
        people.append((booking.student, SessionCheckIn.ROLE_STUDENT))
    return people


def send_due_checkin_reminders(*, now=None):
    """Email anyone who has not checked in once the staff-set reminder time is reached."""
    now = now or timezone.now()
    config = get_checkin_config()
    reminder_delta = timedelta(hours=config.reminder_hours_before)
    sessions = (
        Session.objects.filter(
            status='open',
            start_time__lte=now + reminder_delta,
            end_time__gte=now,
        )
        .select_related('teacher')
        .prefetch_related(
            Prefetch(
                'bookings',
                queryset=Booking.objects.filter(status='confirmed').select_related('student'),
                to_attr='confirmed_bookings',
            ),
            Prefetch('check_ins', queryset=SessionCheckIn.objects.select_related('user')),
        )
    )
    sent = 0
    skipped = 0
    for session in sessions:
        existing = {row.user_id: row for row in session.check_ins.all()}
        for user, role in expected_participants(session):
            row = existing.get(user.id)
            if row and row.checked_in_at:
                continue
            if row and row.reminder_sent_at:
                continue
            if send_checkin_reminder(user, session, role=role, config=config):
                if row is None:
                    SessionCheckIn.objects.update_or_create(
                        session=session,
                        user=user,
                        defaults={'role': role, 'reminder_sent_at': now},
                    )
                else:
                    row.reminder_sent_at = now
                    row.save(update_fields=['reminder_sent_at'])
                sent += 1
            else:
                skipped += 1
    return {'sent': sent, 'skipped': skipped}
