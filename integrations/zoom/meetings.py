"""Zoom meeting creation.

Scaffold: when Zoom Server-to-Server OAuth credentials are configured (settings.ZOOM),
a real implementation would call the Zoom Meetings API and return the join URL.
Until then we return a deterministic placeholder link so the rest of the app
(email, ICS, UI) has something to show.
"""

import uuid

from django.conf import settings


def create_zoom_meeting(session):
    """Return a Zoom join URL for a session, or '' if we can't/shouldn't create one."""
    if settings.ZOOM.get('ENABLED'):
        # TODO: OAuth token + POST https://api.zoom.us/v2/users/me/meetings
        #   with topic, start_time, duration from session.
        pass

    token = uuid.uuid5(uuid.NAMESPACE_URL, f'zoom-session-{session.id}').hex[:10]
    return f'https://zoom.us/j/{token}'
