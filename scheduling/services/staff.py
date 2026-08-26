"""Staff operations — act on behalf of teachers and students."""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from scheduling.models import Booking, StaffActionLog
from scheduling.services.booking import cancel_booking
from scheduling.services.staff_audit import log_staff_action

User = get_user_model()


def user_is_staff(user):
    return user.is_authenticated and user.groups.filter(name='staff').exists()


def list_teachers():
    return User.objects.filter(groups__name='teacher').order_by('username')


def get_teacher(teacher_id):
    return User.objects.filter(pk=teacher_id, groups__name='teacher').first()


def staff_cancel_booking(actor, booking_id, *, refund=True, note=''):
    """Cancel a student's booking on their behalf. Returns (payload, error)."""
    booking = (
        Booking.objects.filter(pk=booking_id)
        .select_related('student', 'session', 'session__teacher')
        .first()
    )
    if booking is None:
        return None, 'Booking not found.'
    if booking.status != 'confirmed':
        return None, 'That booking is already cancelled.'

    student = booking.student
    session = booking.session
    tickets = booking.tickets_spent
    if not cancel_booking(actor, booking, refund=refund):
        return None, 'That booking could not be cancelled.'

    refunded = refund and booking.class_request_id is None and tickets > 0
    log_staff_action(
        actor=actor,
        action=StaffActionLog.ACTION_BOOKING_CANCELLED,
        target_user=student,
        summary=(
            f'Cancelled {student.username}\'s booking for "{session.title}" '
            f'({"refunded" if refunded else "no refund"})'
        ),
        note=note,
        booking_id=booking.id,
        session_id=session.id,
        refunded=refunded,
        tickets=tickets,
    )
    return {
        'booking_id': booking.id,
        'status': booking.status,
        'refunded': refunded,
        'tickets': tickets,
        'session_cancelled': session.status == 'cancelled',
    }, None


def staff_reset_password(actor, target_user, new_password, *, note=''):
    """Set a temporary password for a teacher or student. Staff accounts are refused."""
    if target_user.groups.filter(name='staff').exists():
        return False, 'Staff passwords cannot be reset here.'
    try:
        validate_password(new_password, user=target_user)
    except ValidationError as exc:
        return False, ' '.join(exc.messages)

    target_user.set_password(new_password)
    target_user.save(update_fields=['password'])
    log_staff_action(
        actor=actor,
        action=StaffActionLog.ACTION_PASSWORD_RESET,
        target_user=target_user,
        summary=f'Reset password for {target_user.username}',
        note=note,
    )
    return True, None
