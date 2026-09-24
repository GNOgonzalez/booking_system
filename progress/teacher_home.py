"""Teacher home queues — lessons just taught, and the students still owed a report."""

from datetime import timedelta

from django.utils import timezone

from progress.models import SessionFeedback
from scheduling.models import Booking, Session

RECENT_DAYS = 14
RECENT_LIMIT = 15
MISSING_DAYS = 90
MISSING_LIMIT = 50


def _past_sessions(teacher, *, since, limit):
    return list(
        Session.objects.filter(
            teacher=teacher,
            end_time__lte=timezone.now(),
            end_time__gte=since,
        )
        .exclude(status='cancelled')
        .select_related('class_offering')
        .order_by('-end_time')[:limit]
    )


def _confirmed_bookings(sessions):
    if not sessions:
        return []
    return list(
        Booking.objects.filter(session__in=sessions, status='confirmed')
        .select_related('student')
        .order_by('session__end_time', 'student__username')
    )


def _reported_pairs(teacher, sessions):
    """(session_id, student_id) pairs this teacher has already written up."""
    if not sessions:
        return set()
    return set(
        SessionFeedback.objects.filter(teacher=teacher, session__in=sessions).values_list(
            'session_id', 'student_id'
        )
    )


def _session_label(session):
    offering = session.class_offering if session.class_offering_id else None
    return {
        'id': session.id,
        'title': session.title,
        'start_time': session.start_time,
        'end_time': session.end_time,
        'subject': offering.subject if offering else '',
    }


def teacher_home(teacher):
    """Recently finished lessons plus the per-student report backlog."""
    now = timezone.now()

    recent_sessions = _past_sessions(
        teacher,
        since=now - timedelta(days=RECENT_DAYS),
        limit=RECENT_LIMIT,
    )
    recent_bookings = _confirmed_bookings(recent_sessions)
    recent_reported = _reported_pairs(teacher, recent_sessions)

    booked_by_session = {}
    for booking in recent_bookings:
        booked_by_session.setdefault(booking.session_id, []).append(booking)

    recent_rows = []
    for session in recent_sessions:
        bookings = booked_by_session.get(session.id, [])
        reported = sum(
            1 for booking in bookings if (session.id, booking.student_id) in recent_reported
        )
        recent_rows.append({
            **_session_label(session),
            'student_count': len(bookings),
            'reported_count': reported,
            'students': [b.student.username for b in bookings],
        })

    # Wider window than the "recent" list: a report from two months ago is still owed.
    backlog_sessions = _past_sessions(
        teacher,
        since=now - timedelta(days=MISSING_DAYS),
        limit=None,
    )
    backlog_reported = _reported_pairs(teacher, backlog_sessions)
    session_by_id = {session.id: session for session in backlog_sessions}

    missing_rows = []
    for booking in _confirmed_bookings(backlog_sessions):
        if (booking.session_id, booking.student_id) in backlog_reported:
            continue
        session = session_by_id[booking.session_id]
        missing_rows.append({
            'session': _session_label(session),
            'student_id': booking.student_id,
            'student_name': booking.student.username,
        })

    missing_rows.sort(key=lambda row: row['session']['end_time'], reverse=True)

    return {
        'generated_at': now,
        'recent_days': RECENT_DAYS,
        'recent_sessions': recent_rows,
        'missing_reports': missing_rows[:MISSING_LIMIT],
        'missing_reports_total': len(missing_rows),
    }
