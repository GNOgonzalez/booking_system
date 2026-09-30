from django.core.management.base import BaseCommand

from scheduling.services.checkin import send_due_checkin_reminders


class Command(BaseCommand):
    help = 'Email teachers and students who have not checked in once the staff reminder time is reached.'

    def handle(self, *args, **options):
        result = send_due_checkin_reminders()
        self.stdout.write(
            self.style.SUCCESS(
                f"Check-in reminders sent: {result['sent']} (skipped {result['skipped']})."
            )
        )
