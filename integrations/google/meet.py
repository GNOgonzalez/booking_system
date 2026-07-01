"""Google Meet link creation.

Scaffold: when Google OAuth/Calendar credentials are configured (settings.GOOGLE),
a real implementation would create a Calendar event with conferenceData and return
the generated Meet URL. Until then we return a deterministic placeholder link so the
rest of the app (email, ICS, UI) has something to show.
"""

import uuid

from django.conf import settings


def create_meet_link(session):
    """Return a Meet URL for a session, or '' if we can't/shouldn't create one."""
    if settings.GOOGLE.get('ENABLED'):
        # TODO: real Calendar API call using the teacher's stored OAuth token.
        #   service.events().insert(calendarId='primary', body={...},
        #       conferenceDataVersion=1).execute()
        # For now fall through to a placeholder so behaviour is predictable.
        pass

    token = uuid.uuid5(uuid.NAMESPACE_URL, f'session-{session.id}').hex[:10]
    return f'https://meet.google.com/lookup/{token}'
