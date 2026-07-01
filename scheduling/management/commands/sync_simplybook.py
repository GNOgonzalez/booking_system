from django.core.management.base import BaseCommand

from integrations.simplybook.adapter import upsert_booking
from integrations.simplybook.client import SimplyBookClient


class Command(BaseCommand):
    help = 'Sync bookings from SimplyBook (no-op unless SIMPLYBOOK_API_KEY is set).'

    def handle(self, *args, **options):
        client = SimplyBookClient()
        if not client.enabled:
            self.stdout.write(
                self.style.WARNING('SimplyBook not configured — nothing to sync.')
            )
            return

        count = 0
        for raw in client.fetch_bookings():
            if upsert_booking(raw):
                count += 1
        self.stdout.write(self.style.SUCCESS(f'Synced {count} bookings.'))
