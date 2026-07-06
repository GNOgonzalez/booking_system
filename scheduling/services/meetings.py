"""Create video meeting links for sessions based on the chosen provider."""

from integrations.google.meet import (
    create_meet_link,
    create_meet_meeting,
    delete_calendar_event,
    update_calendar_event,
)
from integrations.zoom.meetings import create_zoom_meeting


def create_meeting_link(session):
    """Return a meeting URL for the session's provider, or '' for none."""
    provider = session.meeting_provider or 'none'
    if provider == 'google_meet':
        return create_meet_link(session)
    if provider == 'zoom':
        return create_zoom_meeting(session)
    return ''


def attach_meeting_link(session):
    """Set meeting_url (and Calendar event id for Meet) on the session and save."""
    provider = session.meeting_provider or 'none'
    update_fields = ['meeting_url']
    if provider == 'google_meet':
        link, event_id = create_meet_meeting(session)
        session.meeting_url = link
        session.google_calendar_event_id = event_id
        update_fields.append('google_calendar_event_id')
    elif provider == 'zoom':
        session.meeting_url = create_zoom_meeting(session)
    else:
        session.meeting_url = ''
    session.save(update_fields=update_fields)
    return session.meeting_url


def sync_meeting_update(session):
    """Push title/time changes to the teacher's Calendar event, if one exists."""
    if session.meeting_provider == 'google_meet' and session.google_calendar_event_id:
        update_calendar_event(session)


def sync_meeting_cancel(session):
    """Remove the Calendar event for a cancelled session, if one exists."""
    if session.meeting_provider != 'google_meet' or not session.google_calendar_event_id:
        return
    if delete_calendar_event(session):
        session.google_calendar_event_id = ''
        session.save(update_fields=['google_calendar_event_id'])
