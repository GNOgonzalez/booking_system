"""Email notifications. Uses console backend in dev, SMTP in prod (see settings)."""

from django.conf import settings
from django.core.mail import send_mail


def _safe_send(subject, body, recipient):
    if not recipient:
        return False
    try:
        send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [recipient],
            fail_silently=True,
        )
        return True
    except Exception:
        return False


def send_booking_confirmation(booking):
    session = booking.session
    body = (
        f"Hi {booking.student.username},\n\n"
        f'You booked "{session.title}" on {session.start_time}.\n'
    )
    if session.meeting_url:
        body += f"Join link: {session.meeting_url}\n"
    body += "\nSee you there!"
    return _safe_send(f'Booking confirmed: {session.title}', body, booking.student.email)


def send_booking_cancellation(booking):
    session = booking.session
    body = (
        f"Hi {booking.student.username},\n\n"
        f'Your booking for "{session.title}" on {session.start_time} was cancelled.'
    )
    return _safe_send(f'Booking cancelled: {session.title}', body, booking.student.email)


def send_membership_receipt(membership):
    body = (
        f"Hi {membership.user.username},\n\n"
        f"Your {membership.plan_type} membership is active"
    )
    if membership.valid_until:
        body += f" until {membership.valid_until}"
    body += ".\n\nThank you!"
    return _safe_send('Membership receipt', body, membership.user.email)
