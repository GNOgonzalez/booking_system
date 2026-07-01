"""Map SimplyBook records onto our domain models.

Principle (see docs/architecture-and-roadmap.md §10): our Postgres schema is the
source of truth. SimplyBook rows are matched/updated by `external_id`; business
rules still live in scheduling/services/.
"""

from django.contrib.auth.models import User

from scheduling.models import Booking, Session


def upsert_session(raw):
    """raw: {external_id, teacher_username, title, start_time, end_time, capacity}"""
    teacher, _ = User.objects.get_or_create(username=raw['teacher_username'])
    session, _ = Session.objects.update_or_create(
        external_id=raw['external_id'],
        defaults={
            'teacher': teacher,
            'title': raw.get('title', 'Imported session'),
            'start_time': raw['start_time'],
            'end_time': raw['end_time'],
            'capacity': raw.get('capacity', 1),
            'status': raw.get('status', 'open'),
        },
    )
    return session


def upsert_booking(raw):
    """raw: {external_id, student_username, session_external_id, status}"""
    student, _ = User.objects.get_or_create(username=raw['student_username'])
    session = Session.objects.filter(external_id=raw['session_external_id']).first()
    if session is None:
        return None
    booking, _ = Booking.objects.update_or_create(
        external_id=raw['external_id'],
        defaults={
            'student': student,
            'session': session,
            'status': raw.get('status', 'confirmed'),
        },
    )
    return booking
