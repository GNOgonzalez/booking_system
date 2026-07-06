from django.core.management.base import BaseCommand

from progress.homework_services import purge_expired_homework_attachments


class Command(BaseCommand):
    help = 'Delete homework file attachments older than 7 days (journal text is kept).'

    def handle(self, *args, **options):
        removed = purge_expired_homework_attachments()
        self.stdout.write(self.style.SUCCESS(f'Purged {removed} expired homework file(s).'))
