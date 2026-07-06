"""Email notifications. Uses console backend in dev, SMTP in prod (see settings)."""

import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def _using_console_email():
    return settings.EMAIL_BACKEND.endswith('console.EmailBackend')


def _safe_send(subject, body, recipient):
    if not recipient:
        logger.warning('Skipping email %r: empty recipient', subject)
        return False
    try:
        sent = send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [recipient],
            fail_silently=False,
        )
        if sent:
            if _using_console_email():
                logger.info(
                    'Email logged to console only (set EMAIL_HOST for real delivery): %s -> %s',
                    subject,
                    recipient,
                )
            return True
        logger.warning('Email not sent: %s -> %s', subject, recipient)
        return False
    except Exception:
        logger.exception('Email failed: %s -> %s', subject, recipient)
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


def send_teacher_booking_notification(booking):
    session = booking.session
    teacher = session.teacher
    body = (
        f"Hi {teacher.username},\n\n"
        f'{booking.student.username} booked "{session.title}".\n'
        f"Starts: {session.start_time}\n"
        f"Ends: {session.end_time}\n"
    )
    if session.meeting_url:
        body += f"Meeting link: {session.meeting_url}\n"
    body += "\nSee your schedule in the studio app."
    return _safe_send(f'New booking: {session.title}', body, teacher.email)


def notify_booking_created(booking):
    """Email the student and session teacher when a booking is confirmed."""
    return {
        'student_email_sent': send_booking_confirmation(booking),
        'teacher_email_sent': send_teacher_booking_notification(booking),
    }


def _class_request_label(class_request):
    if class_request.class_offering_id:
        return class_request.class_offering.display_name
    return class_request.class_profile_label


def _class_request_teacher_label(class_request):
    if class_request.open_to_any_teacher and class_request.teacher_id is None:
        return 'any available teacher'
    if class_request.teacher_id:
        return class_request.teacher.username
    return 'your teacher'


def send_teacher_class_request_notification(class_request, *, teacher):
    student = class_request.student
    label = _class_request_label(class_request)
    topic = ''
    if class_request.class_topic_id:
        topic = f"\nTopic: {class_request.class_topic.title}\n"
    open_note = ''
    if class_request.open_to_any_teacher and class_request.teacher_id is None:
        open_note = (
            "\nThis request is open to any teacher who teaches this class — "
            "the first teacher to accept will schedule it.\n"
        )
    body = (
        f"Hi {teacher.username},\n\n"
        f"{student.username} requested a class:\n"
        f'"{label}"\n'
        f"{topic}"
        f"Time: {class_request.start_time} – {class_request.end_time}\n"
        f"Tickets offered: {class_request.tickets_requested}\n"
        f"{open_note}\n"
        "Review it under Class requests in the studio app."
    )
    return _safe_send(f'New class request from {student.username}', body, teacher.email)


def notify_class_request_created(class_request):
    """Email relevant teacher(s) when a student submits a class request."""
    from scheduling.services.class_requests import teachers_for_open_profile

    teacher_sent = False
    teachers_notified = 0

    if class_request.teacher_id:
        if send_teacher_class_request_notification(class_request, teacher=class_request.teacher):
            teacher_sent = True
            teachers_notified = 1
    elif class_request.open_to_any_teacher:
        teachers = teachers_for_open_profile(
            class_request.student,
            class_request.subject,
            class_request.level,
            class_request.focus,
        )
        for teacher in teachers:
            if send_teacher_class_request_notification(class_request, teacher=teacher):
                teacher_sent = True
                teachers_notified += 1

    return {
        'teacher_email_sent': teacher_sent,
        'teachers_notified': teachers_notified,
    }


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
        f"Your {membership.plan.name} membership is active"
    )
    if membership.valid_until:
        body += f" until {membership.valid_until}"
    body += f".\nYou have {membership.tickets_remaining} booking tickets.\n\nThank you!"
    return _safe_send('Membership receipt', body, membership.user.email)
