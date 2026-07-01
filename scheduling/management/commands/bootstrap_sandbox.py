from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.utils import timezone

from progress.models import ProgressReport, Skill
from scheduling.models import ClassType, CurriculumItem, Membership, Message, Session


class Command(BaseCommand):
    help = 'Create auth groups and optional sandbox demo data.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--demo',
            action='store_true',
            help='Create sample class types, membership, curriculum, and a future session.',
        )

    def handle(self, *args, **options):
        for name in ('student', 'teacher', 'staff'):
            Group.objects.get_or_create(name=name)
            self.stdout.write(f'Group ready: {name}')

        if not options['demo']:
            self.stdout.write(self.style.SUCCESS('Groups ready. Pass --demo to seed sample data.'))
            return

        teacher, _ = User.objects.get_or_create(username='demo_teacher', defaults={'email': 'teacher@example.com'})
        teacher.set_password('demo1234')
        teacher.save()

        student, _ = User.objects.get_or_create(username='demo_student', defaults={'email': 'student@example.com'})
        student.set_password('demo1234')
        student.save()

        teacher.groups.add(Group.objects.get(name='teacher'))
        student.groups.add(Group.objects.get(name='student'))

        Membership.objects.get_or_create(
            user=student,
            defaults={'plan_type': 'basic', 'is_active': True, 'valid_until': timezone.now().date() + timedelta(days=365)},
        )

        piano, _ = ClassType.objects.get_or_create(
            teacher=teacher,
            name='Piano',
            defaults={'description': 'Beginner piano', 'default_capacity': 4},
        )

        session, _ = Session.objects.get_or_create(
            teacher=teacher,
            title='Piano — intro group',
            start_time=timezone.now() + timedelta(days=2),
            end_time=timezone.now() + timedelta(days=2, hours=1),
            defaults={'class_type': piano, 'capacity': 4, 'status': 'open'},
        )
        if not session.meeting_url:
            from integrations.google.meet import create_meet_link

            session.meeting_url = create_meet_link(session)
            session.save(update_fields=['meeting_url'])

        rhythm, _ = Skill.objects.get_or_create(name='Rhythm')
        Skill.objects.get_or_create(name='Sight-reading')
        if not ProgressReport.objects.filter(student=student, teacher=teacher).exists():
            ProgressReport.objects.create(
                student=student,
                teacher=teacher,
                skill=rhythm,
                rating=4,
                note='Great progress on timing.',
            )

        CurriculumItem.objects.get_or_create(
            title='Welcome to the studio',
            defaults={
                'content': 'Practice daily. Bring your notebook.',
                'sort_order': 1,
                'is_published': True,
            },
        )

        if not Message.objects.filter(subject='Welcome').exists():
            Message.objects.create(
                sender=teacher,
                recipient=student,
                subject='Welcome',
                body='Glad you joined. Book an open session when you are ready.',
            )

        self.stdout.write(self.style.SUCCESS('Demo data ready.'))
        self.stdout.write('  demo_teacher / demo1234')
        self.stdout.write('  demo_student / demo1234')
