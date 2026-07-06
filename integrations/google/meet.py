"""Google Meet link creation via the Calendar API.

When the session's teacher has connected Google (Phase 20), we insert a Calendar
event with conferenceData and return the generated Meet URL. Otherwise we fall
back to a deterministic placeholder so email/ICS/UI always have something to show.
"""

import json
import urllib.error
import urllib.request
import uuid

from integrations.google.oauth import valid_access_token

CALENDAR_EVENTS_URL = (
    'https://www.googleapis.com/calendar/v3/calendars/primary/events'
    '?conferenceDataVersion=1'
)


def _placeholder_link(session):
    token = uuid.uuid5(uuid.NAMESPACE_URL, f'session-{session.id}').hex[:10]
    return f'https://meet.google.com/lookup/{token}'


def _insert_calendar_event(access_token, session):
    body = {
        'summary': session.title,
        'start': {'dateTime': session.start_time.isoformat()},
        'end': {'dateTime': session.end_time.isoformat()},
        'conferenceData': {
            'createRequest': {
                'requestId': f'session-{session.id}-{uuid.uuid4().hex[:8]}',
                'conferenceSolutionKey': {'type': 'hangoutsMeet'},
            },
        },
    }
    request = urllib.request.Request(
        CALENDAR_EVENTS_URL,
        data=json.dumps(body).encode(),
        headers={
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        },
        method='POST',
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode())


def create_meet_link(session):
    """Return a Meet URL for a session — real if the teacher connected Google."""
    teacher = session.teacher
    if teacher is not None:
        access_token = valid_access_token(teacher)
        if access_token:
            try:
                event = _insert_calendar_event(access_token, session)
            except (urllib.error.URLError, urllib.error.HTTPError, ValueError):
                return _placeholder_link(session)
            link = event.get('hangoutLink', '')
            if not link:
                for entry in (event.get('conferenceData', {}).get('entryPoints') or []):
                    if entry.get('entryPointType') == 'video':
                        link = entry.get('uri', '')
                        break
            if link:
                return link

    return _placeholder_link(session)
