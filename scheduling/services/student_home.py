"""Student home dashboard aggregation for the React home page."""

from django.utils import timezone

from scheduling.models import Booking, ClassRequest, Membership
from scheduling.services.membership import total_tickets_remaining


def _serialize_booking(booking):
    session = booking.session
    return {
        'id': booking.id,
        'session_id': session.id if session else None,
        'session_title': session.title if session else '',
        'session_start_time': session.start_time if session else None,
        'session_end_time': session.end_time if session else None,
        'teacher_name': session.teacher.username if session and session.teacher_id else '',
        'meeting_url': session.meeting_url if session else '',
        'class_subject': (
            session.class_offering.subject
            if session and session.class_offering_id
            else None
        ),
    }


def student_home(user, *, low_ticket_threshold=2):
    now = timezone.now()

    next_booking = (
        Booking.objects.filter(
            student=user,
            status='confirmed',
            session__start_time__gte=now,
        )
        .select_related(
            'session',
            'session__teacher',
            'session__class_offering',
        )
        .order_by('session__start_time')
        .first()
    )

    pending_requests = ClassRequest.objects.filter(
        student=user,
        status=ClassRequest.STATUS_PENDING,
    ).count()

    tickets_remaining = total_tickets_remaining(user)
    has_membership = Membership.objects.filter(user=user, is_active=True).exists()

    recent_feedback = None
    try:
        from progress.models import SessionFeedback

        fb = (
            SessionFeedback.objects.filter(student=user)
            .select_related('session', 'teacher')
            .order_by('-created_at')
            .first()
        )
        if fb:
            recent_feedback = {
                'id': fb.id,
                'created_at': fb.created_at,
                'teacher_name': fb.teacher.username if fb.teacher_id else '',
                'session_title': fb.session.title if fb.session_id else '',
                'class_notes': (fb.class_notes or '')[:200],
            }
    except Exception:
        pass

    open_homework_count = 0
    try:
        from progress.models import HomeworkAssignment

        open_homework_count = HomeworkAssignment.objects.filter(
            student=user,
            status=HomeworkAssignment.STATUS_OPEN,
        ).count()
    except Exception:
        pass

    return {
        'next_lesson': _serialize_booking(next_booking) if next_booking else None,
        'pending_class_requests': pending_requests,
        'tickets_remaining': tickets_remaining,
        'has_membership': has_membership,
        'low_ticket_warning': (
            has_membership
            and tickets_remaining is not None
            and tickets_remaining <= low_ticket_threshold
        ),
        'recent_feedback': recent_feedback,
        'open_homework_count': open_homework_count,
    }
