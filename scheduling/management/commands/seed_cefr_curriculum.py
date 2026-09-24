from django.core.management.base import BaseCommand

from scheduling.services.cefr_seed import seed_cefr_english_track


class Command(BaseCommand):
    help = 'Create the CEFR A1–C2 English template track (idempotent).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--refresh',
            action='store_true',
            help='Rewrite modules from the JSON file. Resets student progress on this track.',
        )

    def handle(self, *args, **options):
        track, created = seed_cefr_english_track(refresh=options['refresh'])
        count = track.modules.count()
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created "{track.title}" with {count} modules.'))
        elif options['refresh']:
            self.stdout.write(self.style.SUCCESS(f'Refreshed "{track.title}" ({count} modules).'))
        else:
            self.stdout.write(f'"{track.title}" already exists ({count} modules). Use --refresh to rewrite.')
