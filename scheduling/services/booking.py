from django.utils import timezone

from scheduling.models import Booking
from scheduling.services.membership import (
    has_active_membership,
    membership_for_booking,
)
from scheduling.services.notifications import (
    send_booking_cancellation,
    send_booking_confirmation,
)
from scheduling.services.tickets import (
    refund_booking_tickets,
    spend_tickets_for_session,
)


def can_book(user, session):
    if not user.is_active:
        return False
    if not user.groups.filter(name='student').exists():
        return False
    if not has_active_membership(user):
        return False
    if membership_for_booking(user, session) is None:
        return False
    if session.status != 'open':
        return False
    if session.start_time <= timezone.now():
        return False
    if session.bookings.filter(status='confirmed').count() >= session.capacity:
        return False
    if Booking.objects.filter(
        student=user,
        session=session,
        status='confirmed',
    ).exists():
        return False
    return True


def create_booking(user, session):
    membership = membership_for_booking(user, session)
    if membership is None or not can_book(user, session):
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
    send_booking_confirmation(booking)
    return True


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
