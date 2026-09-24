"""Studio-wide view of completed session reports, for staff oversight."""

from datetime import timedelta

from django.utils import timezone

from progress.models import SessionFeedback
from progress.services import feedback_scores, subject_for_session

ALLOWED_PERIODS = (7, 30, 90)
DEFAULT_PERIOD = 30
FEEDBACK_LIMIT = 100
NOTES_EXCERPT_CHARS = 240


def _period_days(days):
    try:
        value = int(days)
    except (TypeError, ValueError):
        return DEFAULT_PERIOD
    return value if value in ALLOWED_PERIODS else DEFAULT_PERIOD


def _row(feedback):
    session = feedback.session if feedback.session_id else None
    notes = feedback.class_notes or ''
    return {
        'id': feedback.id,
        'created_at': feedback.created_at,
        'teacher_id': feedback.teacher_id,
        'teacher_name': feedback.teacher.username if feedback.teacher_id else '',
        'student_id': feedback.student_id,
        'student_name': feedback.student.username if feedback.student_id else '',
        'session_id': feedback.session_id,
        'session_title': session.title if session else '',
        'session_start_time': session.start_time if session else None,
        'subject': subject_for_session(session),
        'scores': feedback_scores(feedback),
        'notes_excerpt': notes[:NOTES_EXCERPT_CHARS],
        'notes_truncated': len(notes) > NOTES_EXCERPT_CHARS,
    }


def studio_feedback(*, days=None, teacher_id=None):
    period = _period_days(days)
    since = timezone.now() - timedelta(days=period)

    qs = (
        SessionFeedback.objects.filter(created_at__gte=since)
        .select_related('teacher', 'student', 'session', 'session__class_offering')
        .order_by('-created_at')
    )
    if teacher_id:
        try:
            qs = qs.filter(teacher_id=int(teacher_id))
        except (TypeError, ValueError):
            pass

    total = qs.count()
    rows = [_row(feedback) for feedback in qs[:FEEDBACK_LIMIT]]
    return {
        'period_days': period,
        'total': total,
        'returned': len(rows),
        'reports': rows,
    }
