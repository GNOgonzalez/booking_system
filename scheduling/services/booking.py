from django.utils import timezone

from scheduling.models import Booking
from scheduling.services.membership import (
    has_active_membership,
    membership_for_booking,
)
from scheduling.services.notifications import (
    send_booking_cancellation,
    notify_booking_created,
)
from scheduling.services.tickets import (
    refund_booking_tickets,
    session_ticket_cost,
    spend_tickets_for_session,
)


def booking_block_reason(user, session):
    """Return None if booking is allowed, else a short user-facing message."""
    if not user.is_active:
        return 'Your account is inactive.'
    if not user.groups.filter(name='student').exists():
        return 'Only students can book sessions.'
    if not has_active_membership(user):
        return 'An active membership is required to book.'
    membership = membership_for_booking(user, session)
    if membership is None:
        from scheduling.services.membership import (
            _membership_allows_class,
            active_memberships_for,
        )

        cost = session_ticket_cost(session)
        if not any(
            _membership_allows_class(m, session.class_offering)
            for m in active_memberships_for(user)
        ):
            return 'Your membership does not include this class.'
        return f'Not enough tickets (this session costs {cost}).'
    if session.status != 'open':
        return 'This session is not open for booking.'
    if session.start_time <= timezone.now():
        return 'This session has already started.'
    if session.bookings.filter(status='confirmed').count() >= session.capacity:
        return 'This session is full.'
    if Booking.objects.filter(
        student=user,
        session=session,
        status='confirmed',
    ).exists():
        return 'You already have a booking for this session.'
    return None


def can_book(user, session):
    return booking_block_reason(user, session) is None


def create_booking(user, session):
    membership = membership_for_booking(user, session)
    if membership is None or booking_block_reason(user, session) is not None:
        return False
    ok, cost = spend_tickets_for_session(membership, session)
    if not ok:
        return False
    booking = Booking.objects.create(
        student=user,
        session=session,
        membership=membership,
        status='confirmed',
        tickets_spent=cost,
    )
    booking = Booking.objects.select_related(
        'student',
        'session__teacher',
        'session',
    ).get(pk=booking.pk)
    notifications = notify_booking_created(booking)
    return booking, notifications


def can_cancel(user, booking):
    if booking.status != 'confirmed':
        return False
    if user == booking.student:
        return True
    if user == booking.session.teacher:
        return True
    if user.groups.filter(name='staff').exists():
        return True
    return False


def cancel_booking(user, booking):
    if not can_cancel(user, booking):
        return False

    booking.status = 'cancelled'
    booking.save()

    if booking.class_request_id is None:
        refund_booking_tickets(booking)
    send_booking_cancellation(booking)

    session = booking.session
    if not session.bookings.filter(status='confirmed').exists():
        session.status = 'cancelled'
        session.save()

    return True
