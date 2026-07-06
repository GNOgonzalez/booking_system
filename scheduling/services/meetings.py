"""Create video meeting links for sessions based on the chosen provider."""

from integrations.google.meet import create_meet_link
from integrations.zoom.meetings import create_zoom_meeting


def create_meeting_link(session):
    """Return a meeting URL for the session's provider, or '' for none."""
    provider = session.meeting_provider or 'none'
    if provider == 'google_meet':
        return create_meet_link(session)
    if provider == 'zoom':
        return create_zoom_meeting(session)
    return ''
