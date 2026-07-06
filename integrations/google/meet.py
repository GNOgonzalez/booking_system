"""Google Meet link creation + Calendar event sync via the Calendar API.

When the session's teacher has connected Google (Phase 20), we insert a Calendar
event with conferenceData and return the generated Meet URL. Otherwise we fall
back to a deterministic placeholder so email/ICS/UI always have something to show.

The Calendar event id is kept on the session so later edits/cancellations can be
synced back to the teacher's calendar (update_calendar_event / delete_calendar_event).
"""

import json
import urllib.error
import urllib.parse
import urllib.request
import uuid

from integrations.google.oauth import valid_access_token

CALENDAR_BASE_URL = 'https://www.googleapis.com/calendar/v3/calendars/primary/events'


def _placeholder_link(session):
    token = uuid.uuid5(uuid.NAMESPACE_URL, f'session-{session.id}').hex[:10]
    return f'https://meet.google.com/lookup/{token}'


def _calendar_request(method, access_token, *, event_id=None, body=None, query=''):
    url = CALENDAR_BASE_URL
    if event_id:
        url += f'/{urllib.parse.quote(event_id)}'
    if query:
        url += f'?{query}'
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        headers={
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        },
        method=method,
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read().decode()
        return json.loads(raw) if raw else {}


def _event_body(session):
    return {
        'summary': session.title,
        'start': {'dateTime': session.start_time.isoformat()},
        'end': {'dateTime': session.end_time.isoformat()},
    }


def _insert_calendar_event(access_token, session):
    body = _event_body(session)
    body['conferenceData'] = {
        'createRequest': {
            'requestId': f'session-{session.id}-{uuid.uuid4().hex[:8]}',
            'conferenceSolutionKey': {'type': 'hangoutsMeet'},
        },
    }
    return _calendar_request(
        'POST',
        access_token,
        body=body,
        query='conferenceDataVersion=1',
    )


def _meet_url_from_event(event):
    link = event.get('hangoutLink', '')
    if not link:
        for entry in (event.get('conferenceData', {}).get('entryPoints') or []):
            if entry.get('entryPointType') == 'video':
                link = entry.get('uri', '')
                break
    return link


def create_meet_meeting(session):
    """Return (meet_url, calendar_event_id) — real if the teacher connected Google."""
    teacher = session.teacher
    if teacher is not None:
        access_token = valid_access_token(teacher)
        if access_token:
            try:
                event = _insert_calendar_event(access_token, session)
            except (urllib.error.URLError, urllib.error.HTTPError, ValueError):
                return _placeholder_link(session), ''
            link = _meet_url_from_event(event)
            if link:
                return link, event.get('id', '')

    return _placeholder_link(session), ''


def create_meet_link(session):
    """Return a Meet URL for a session — real if the teacher connected Google."""
    return create_meet_meeting(session)[0]


def update_calendar_event(session):
    """Push the session's current title/time to its Calendar event. Returns True on success."""
    if not session.google_calendar_event_id or session.teacher is None:
        return False
    access_token = valid_access_token(session.teacher)
    if not access_token:
        return False
    try:
        _calendar_request(
            'PATCH',
            access_token,
            event_id=session.google_calendar_event_id,
            body=_event_body(session),
        )
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError):
        return False
    return True


def delete_calendar_event(session):
    """Delete the session's Calendar event. Returns True if gone (incl. already deleted)."""
    if not session.google_calendar_event_id or session.teacher is None:
        return False
    access_token = valid_access_token(session.teacher)
    if not access_token:
        return False
    try:
        _calendar_request(
            'DELETE',
            access_token,
            event_id=session.google_calendar_event_id,
        )
    except urllib.error.HTTPError as exc:
        # Event already deleted or cancelled on Google's side — treat as synced.
        return exc.code in (404, 410)
    except (urllib.error.URLError, ValueError):
        return False
    return True
