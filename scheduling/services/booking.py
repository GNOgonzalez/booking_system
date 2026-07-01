from django.utils import timezone

from scheduling.models import Booking
from scheduling.services.membership import has_active_membership
from scheduling.services.notifications import (
    send_booking_cancellation,
    send_booking_confirmation,
)


def can_book(user, session):
    if not user.groups.filter(name='student').exists():
        return False
    if not has_active_membership(user):
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
    if can_book(user, session):
        booking = Booking.objects.create(
            student=user,
            session=session,
            status='confirmed',
        )
        send_booking_confirmation(booking)
        return True
    return False


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
    send_booking_cancellation(booking)

    session = booking.session
    if not session.bookings.filter(status='confirmed').exists():
        session.status = 'cancelled'
        session.save()

    return True
