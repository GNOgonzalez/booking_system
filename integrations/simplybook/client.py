"""SimplyBook.me JSON-RPC client (scaffold).

Only performs network calls when settings.SIMPLYBOOK['ENABLED'] is true. Otherwise
`fetch_bookings` returns an empty list so the sync command is a safe no-op locally.
"""

from django.conf import settings


class SimplyBookClient:
    def __init__(self):
        self.config = settings.SIMPLYBOOK
        self.enabled = self.config.get('ENABLED', False)

    def fetch_bookings(self):
        if not self.enabled:
            return []
        # TODO: real JSON-RPC calls:
        #   1) POST /login  -> token
        #   2) POST /admin  method 'getBookings' with token headers
        # Map each raw booking to the dict shape adapter.upsert_booking expects.
        raise NotImplementedError('SimplyBook API calls not implemented in sandbox.')
