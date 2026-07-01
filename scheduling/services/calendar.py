"""Minimal iCalendar (.ics) generation — no external dependency."""

from datetime import timezone as dt_timezone

from django.utils import timezone


def _fmt(dt):
    return dt.astimezone(dt_timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def _escape(text):
    return (
        str(text)
        .replace('\\', '\\\\')
        .replace(';', '\\;')
        .replace(',', '\\,')
        .replace('\n', '\\n')
    )


def session_to_ics(session):
    """Return an .ics string for a Session."""
    now = _fmt(timezone.now())
    description = f'Teacher: {session.teacher.username}'
    if session.meeting_url:
        description += f'\\nJoin: {session.meeting_url}'

    lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//booking_scheduling_app//EN',
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',
        'BEGIN:VEVENT',
        f'UID:session-{session.id}@booking.local',
        f'DTSTAMP:{now}',
        f'DTSTART:{_fmt(session.start_time)}',
        f'DTEND:{_fmt(session.end_time)}',
        f'SUMMARY:{_escape(session.title)}',
        f'DESCRIPTION:{_escape(description)}',
    ]
    if session.meeting_url:
        lines.append(f'URL:{session.meeting_url}')
    lines += ['END:VEVENT', 'END:VCALENDAR']
    return '\r\n'.join(lines) + '\r\n'
