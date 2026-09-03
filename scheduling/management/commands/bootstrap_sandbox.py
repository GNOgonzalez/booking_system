from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.utils import timezone

from progress.homework_services import add_homework_entry, create_homework_assignment
from progress.models import HomeworkAssignment, ProgressReport, SessionFeedback, Skill
from progress.services import ensure_default_score_dimensions
from scheduling.models import (
    AvailabilityBlock,
    Booking,
    ClassOffering,
    ClassTopic,
    CurriculumItem,
    CurriculumTrack,
    Membership,
    MembershipPlan,
    Message,
    Session,
    TeacherStudentAssignment,
)
from scheduling.services.class_catalog import ensure_default_catalog
from scheduling.services.curriculum import create_track, enroll_student
from scheduling.services.glossary import ensure_default_glossary
from scheduling.services.meetings import create_meeting_link
from scheduling.services.sessions import session_display_title
from scheduling.services.teacher_permissions import ensure_default_permissions


class Command(BaseCommand):
    help = 'Create auth groups and optional sandbox demo data.'

    DEMO_USERNAMES = (
        'demo_teacher',
        'demo_student',
        'demo_student_2',
        'demo_student_3',
        'demo_student_4',
        'demo_staff',
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--demo',
            action='store_true',
            help='Create sample class types, membership, curriculum, and a future session.',
        )
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Remove demo seed users and data before seeding (use with --demo).',
        )
        parser.add_argument(
            '--showcase',
            action='store_true',
            help='Grant demo_student membership, an upcoming booking, and showcase-ready state.',
        )
        parser.add_argument(
            '--staff-superuser',
            action='store_true',
            help='Give demo_staff Django admin access (local only — never on a public demo).',
        )

    def _ensure_class_offering(self, teacher, subject, level, focus, topics, *, topics_ordered=False, **extra):
        if isinstance(topics, str):
            topics = [topics]
        offering, created = ClassOffering.objects.update_or_create(
            teacher=teacher,
            subject=subject,
            level=level,
            focus=focus,
            defaults={
                'default_capacity': extra.pop('default_capacity', 4),
                'ticket_cost': extra.pop('ticket_cost', 1),
                'is_active': True,
                'topics_ordered': topics_ordered,
            },
        )
        if not created:
            offering.topics_ordered = topics_ordered
            offering.default_capacity = extra.get('default_capacity', offering.default_capacity)
            offering.ticket_cost = extra.get('ticket_cost', offering.ticket_cost)
            offering.is_active = True
            offering.save()
        for index, title in enumerate(topics):
            ClassTopic.objects.update_or_create(
                class_offering=offering,
                title=title,
                defaults={'sort_order': index},
            )
        return offering

    def _class_topic(self, offering, title):
        return ClassTopic.objects.get(class_offering=offering, title=title)

    def _ensure_subject_plan(self, name, subject, offerings, **kwargs):
        plan_type = kwargs.pop('plan_type', MembershipPlan.PLAN_SUBSCRIPTION)
        plan, _ = MembershipPlan.objects.update_or_create(
            name=name,
            defaults={
                'description': kwargs.get('description', ''),
                'plan_type': plan_type,
                'price_cents': kwargs.get('price_cents', 2000),
                'billing_period_days': kwargs.get('billing_period_days', 30),
                'ticket_allowance': kwargs.get('ticket_allowance', 10),
                'is_active': True,
                'subject': subject,
            },
        )
        subject_classes = [o for o in offerings if o.subject == subject]
        plan.allowed_classes.set(subject_classes)
        return plan

    def _ensure_demo_session(self, teacher, offering, external_id, start, end, *, class_topic=None, **extra):
        title = session_display_title(offering, class_topic)
        session, _ = Session.objects.update_or_create(
            teacher=teacher,
            external_id=external_id,
            defaults={
                'title': title,
                'class_offering': offering,
                'class_topic': class_topic,
                'start_time': start,
                'end_time': end,
                'capacity': extra.pop('capacity', offering.default_capacity),
                'status': extra.pop('status', 'open'),
                **extra,
            },
        )
        sync_fields = []
        if session.class_offering_id != offering.id:
            session.class_offering = offering
            sync_fields.append('class_offering')
        if session.class_topic_id != (class_topic.id if class_topic else None):
            session.class_topic = class_topic
            sync_fields.append('class_topic')
        if session.title != title:
            session.title = title
            sync_fields.append('title')
        if sync_fields:
            session.save(update_fields=sync_fields)
        if not session.meeting_url:
            session.meeting_url = create_meeting_link(session)
            session.save(update_fields=['meeting_url'])
        return session

    def _ensure_booking(self, student, session):
        booking, created = Booking.objects.get_or_create(
            student=student,
            session=session,
            defaults={'status': 'confirmed'},
        )
        if not created and booking.status != 'confirmed':
            booking.status = 'confirmed'
            booking.save(update_fields=['status'])
        return booking

    def _ensure_demo_student(self, username, email):
        user, _ = User.objects.get_or_create(username=username, defaults={'email': email})
        user.set_password('demo1234')
        user.save()
        user.groups.add(Group.objects.get(name='student'))
        return user

    def _apply_showcase_seed(self, student, teacher, catalog):
        """Portfolio demo: demo_student can log in and see a full student UI immediately."""
        japanese_plan = MembershipPlan.objects.filter(name='Japanese', is_active=True).first()
        if japanese_plan is None:
            self.stdout.write(self.style.WARNING('Showcase skipped: Japanese plan not found.'))
            return

        valid_until = timezone.now().date() + timedelta(days=30)
        membership, _ = Membership.objects.update_or_create(
            user=student,
            plan=japanese_plan,
            defaults={
                'is_active': True,
                'valid_until': valid_until,
                'tickets_remaining': 8,
            },
        )
        membership.is_active = True
        membership.valid_until = valid_until
        membership.tickets_remaining = 8
        membership.save(update_fields=['is_active', 'valid_until', 'tickets_remaining'])

        now = timezone.now()
        start = now + timedelta(days=3, hours=2)
        end = start + timedelta(hours=1)
        session = self._ensure_demo_session(
            teacher,
            catalog['pronunciation'],
            'demo_showcase_next',
            start,
            end,
        )
        self._ensure_booking(student, session)
        self.stdout.write('  Showcase: demo_student has Japanese membership + upcoming lesson.')

    def _book_students(self, session, students):
        for student in students:
            self._ensure_booking(student, session)

    def _reset_demo_seed(self):
        deleted, _ = User.objects.filter(username__in=self.DEMO_USERNAMES).delete()
        CurriculumItem.objects.filter(title='Welcome to the studio').delete()
        Message.objects.filter(subject='Welcome').delete()
        self.stdout.write(f'Removed demo seed data ({deleted} related rows).')

    def _ensure_owner_teacher(self):
        user, created = User.objects.get_or_create(
            username='gnogonzalez',
            defaults={'email': 'gnogonzalez@gmail.com'},
        )
        user.email = 'gnogonzalez@gmail.com'
        if created:
            user.set_password('demo1234')
        user.save()
        user.groups.add(Group.objects.get(name='teacher'))
        ensure_default_permissions(user)
        return user, created

    def handle(self, *args, **options):
        for name in ('student', 'teacher', 'staff'):
            Group.objects.get_or_create(name=name)
            self.stdout.write(f'Group ready: {name}')

        if not options['demo']:
            owner, created = self._ensure_owner_teacher()
            if created:
                self.stdout.write('  gnogonzalez / demo1234  (teacher)')
            else:
                self.stdout.write('  gnogonzalez@gmail.com — teacher role ensured')
            self.stdout.write(self.style.SUCCESS('Groups ready. Pass --demo to seed sample data.'))
            ensure_default_catalog()
            return

        if options['reset']:
            self._reset_demo_seed()

        ensure_default_score_dimensions()
        ensure_default_glossary()
        ensure_default_catalog()

        # Django admin access is opt-in: a public demo should not expose /admin/.
        grant_admin = options['staff_superuser']
        staff_user, _ = User.objects.get_or_create(
            username='demo_staff',
            defaults={'email': 'staff@example.com'},
        )
        staff_user.set_password('demo1234')
        staff_user.is_staff = grant_admin
        staff_user.is_superuser = grant_admin
        staff_user.save()
        staff_user.groups.add(Group.objects.get(name='staff'))

        teacher, _ = User.objects.get_or_create(username='demo_teacher', defaults={'email': 'teacher@example.com'})
        teacher.set_password('demo1234')
        teacher.save()

        student, _ = User.objects.get_or_create(username='demo_student', defaults={'email': 'student@example.com'})
        student.set_password('demo1234')
        student.save()

        teacher.groups.add(Group.objects.get(name='teacher'))
        student.groups.add(Group.objects.get(name='student'))
        ensure_default_permissions(teacher)

        student_2 = self._ensure_demo_student('demo_student_2', 'alex@example.com')
        student_3 = self._ensure_demo_student('demo_student_3', 'sam@example.com')
        student_4 = self._ensure_demo_student('demo_student_4', 'jordan@example.com')
        demo_students = (student, student_2, student_3, student_4)
        # No pre-granted membership — students purchase via mock checkout or Stripe in dev.
        Membership.objects.filter(user__in=demo_students).delete()

        # Teacher class catalog — session titles come from this list.
        catalog = {
            'grammar_vocab': self._ensure_class_offering(
                teacher,
                'Japanese',
                'Beginner',
                'Grammar and Vocabulary',
                ['Present Tense Verbs', 'Hiragana Review'],
                topics_ordered=True,
            ),
            'dialogues': self._ensure_class_offering(
                teacher, 'Japanese', 'Beginner', 'Reading', 'Short Dialogues',
            ),
            'pronunciation': self._ensure_class_offering(
                teacher, 'Japanese', 'Beginner', 'Speaking', 'Pronunciation Drills',
            ),
            'daily_routines': self._ensure_class_offering(
                teacher, 'Japanese', 'Intermediate', 'Conversation', 'Daily Routines',
                default_capacity=6,
            ),
            'formal_email': self._ensure_class_offering(
                teacher, 'Japanese', 'Advanced', 'Writing', 'Formal Email',
            ),
            'greetings': self._ensure_class_offering(
                teacher, 'Japanese', 'Beginner', 'Listening', 'Greetings and Introductions',
            ),
            'english_grammar': self._ensure_class_offering(
                teacher,
                'English',
                'Beginner',
                'Grammar',
                ['Present Simple', 'Articles', 'Questions'],
                topics_ordered=True,
            ),
            'english_speaking': self._ensure_class_offering(
                teacher, 'English', 'Beginner', 'Speaking', 'Conversation Practice',
            ),
            'english_writing': self._ensure_class_offering(
                teacher, 'English', 'Intermediate', 'Writing', 'Essay Structure',
            ),
            'english_workshop': self._ensure_class_offering(
                teacher, 'English', 'Advanced', 'Events', 'Workshop: Public Speaking',
                ticket_cost=2,
                default_capacity=8,
            ),
        }

        all_offerings = list(catalog.values())
        self._ensure_subject_plan(
            'Japanese',
            'Japanese',
            all_offerings,
            description='Book Japanese classes. Includes 10 tickets per billing period.',
            price_cents=2000,
            ticket_allowance=10,
        )
        self._ensure_subject_plan(
            'English',
            'English',
            all_offerings,
            description='Book English classes. Includes 10 tickets per billing period.',
            price_cents=2200,
            ticket_allowance=10,
        )
        self._ensure_subject_plan(
            'Japanese — 1 ticket',
            'Japanese',
            all_offerings,
            plan_type=MembershipPlan.PLAN_TICKET_PACK,
            description='Add one booking ticket to your Japanese membership.',
            price_cents=500,
            ticket_allowance=1,
            billing_period_days=0,
        )
        self._ensure_subject_plan(
            'English — 1 ticket',
            'English',
            all_offerings,
            plan_type=MembershipPlan.PLAN_TICKET_PACK,
            description='Add one booking ticket to your English membership.',
            price_cents=500,
            ticket_allowance=1,
            billing_period_days=0,
        )
        MembershipPlan.objects.filter(name__in=('Basic', 'Premium')).update(is_active=False)

        for weekday, start, end in ((0, '09:00', '12:00'), (2, '14:00', '17:00'), (4, '10:00', '13:00')):
            AvailabilityBlock.objects.get_or_create(
                teacher=teacher,
                weekday=weekday,
                start_time=start,
                end_time=end,
            )

        now = timezone.now()

        report_sessions = [
            (
                'demo_report_scales',
                catalog['grammar_vocab'],
                now - timedelta(days=1, hours=2),
                [student],
                self._class_topic(catalog['grammar_vocab'], 'Present Tense Verbs'),
            ),
            ('demo_report_repertoire', catalog['dialogues'], now - timedelta(days=3, hours=1), [student, student_2], None),
            (
                'demo_report_theory',
                catalog['grammar_vocab'],
                now - timedelta(days=6),
                [student, student_2, student_3],
                self._class_topic(catalog['grammar_vocab'], 'Hiragana Review'),
            ),
            (
                'demo_report_upcoming',
                catalog['pronunciation'],
                now + timedelta(days=2, hours=3),
                [student_2, student_4],
                None,
            ),
            (
                'demo_report_group',
                catalog['daily_routines'],
                now + timedelta(days=5),
                [student_2, student_3, student_4],
                None,
            ),
            (
                'demo_multi_ensemble',
                catalog['formal_email'],
                now + timedelta(days=9, hours=1),
                [student_2, student_3, student_4],
                None,
            ),
        ]
        for external_id, offering, start, students, class_topic in report_sessions:
            end = start + timedelta(hours=1)
            capacity = max(len(students) + 2, offering.default_capacity)
            session = self._ensure_demo_session(
                teacher, offering, external_id, start, end, capacity=capacity, class_topic=class_topic,
            )
            self._book_students(session, students)

        intro = self._ensure_demo_session(
            teacher,
            catalog['greetings'],
            'demo_intro_group',
            now + timedelta(days=7, hours=2),
            now + timedelta(days=7, hours=3),
            capacity=6,
        )
        self._book_students(intro, [student_2, student_3])

        # Past demo bookings stay for progress charts; leave upcoming slots for demo_student to book.
        removed, _ = Booking.objects.filter(
            student=student,
            session__start_time__gte=now,
            status='confirmed',
        ).delete()
        if removed:
            self.stdout.write(f'  Cleared {removed} upcoming demo_student booking(s) for open calendar.')

        self._ensure_demo_session(
            teacher,
            catalog['english_speaking'],
            'demo_english_open',
            now + timedelta(days=4, hours=2),
            now + timedelta(days=4, hours=3),
        )
        self._ensure_demo_session(
            teacher,
            catalog['english_workshop'],
            'demo_english_workshop',
            now + timedelta(days=10, hours=5),
            now + timedelta(days=10, hours=7),
        )

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

        trend = [
            (2, 1, 1, 2),
            (3, 2, 2, 3),
            (3, 3, 3, 3),
            (4, 4, 3, 4),
            (5, 4, 4, 5),
        ]
        chart_offerings = [
            (catalog['grammar_vocab'], self._class_topic(catalog['grammar_vocab'], 'Present Tense Verbs')),
            (catalog['grammar_vocab'], self._class_topic(catalog['grammar_vocab'], 'Hiragana Review')),
            (catalog['dialogues'], None),
            (catalog['pronunciation'], None),
            (catalog['greetings'], None),
        ]
        for i, scores in enumerate(trend):
            weeks_ago = len(trend) - i
            past = now - timedelta(weeks=weeks_ago)
            offering, class_topic = chart_offerings[i]
            past_session = self._ensure_demo_session(
                teacher,
                offering,
                f'demo_chart_{i + 1}',
                past,
                past + timedelta(hours=1),
                class_topic=class_topic,
            )
            self._ensure_booking(student, past_session)
            g, r, w, s = scores
            topic_note = class_topic.title if class_topic else offering.display_name
            SessionFeedback.objects.get_or_create(
                student=student,
                session=past_session,
                defaults={
                    'teacher': teacher,
                    'grammar_stars': g,
                    'reading_stars': r,
                    'writing_stars': w,
                    'speaking_stars': s,
                    'scores': {
                        'grammar': g,
                        'reading': r,
                        'writing': w,
                        'speaking': s,
                    },
                    'class_notes': f'{topic_note}: steady improvement.',
                },
            )

        chart_session_1 = Session.objects.filter(teacher=teacher, external_id='demo_chart_1').first()
        chart_session_3 = Session.objects.filter(teacher=teacher, external_id='demo_chart_3').first()
        if chart_session_1 and not HomeworkAssignment.objects.filter(
            session=chart_session_1, student=student,
        ).exists():
            assignment, err = create_homework_assignment(
                teacher=teacher,
                student=student,
                session=chart_session_1,
                kind=HomeworkAssignment.KIND_FILE,
                title='Hiragana practice sheet',
                prompt='Review these characters before our next session. Reply with your completed worksheet photo or notes.',
            )
            if assignment and not err:
                add_homework_entry(
                    assignment,
                    author=student,
                    body='I practiced rows あ–そ. Still working on た row.',
                )
        if chart_session_3 and not HomeworkAssignment.objects.filter(
            session=chart_session_3, student=student,
        ).exists():
            assignment, err = create_homework_assignment(
                teacher=teacher,
                student=student,
                session=chart_session_3,
                kind=HomeworkAssignment.KIND_JOURNAL,
                title='Dialogue reflection',
                prompt='After each short dialogue we covered, write 2–3 sentences: what new phrase did you learn, and where could you use it this week?',
            )
            if assignment and not err:
                add_homework_entry(
                    assignment,
                    author=student,
                    body='Learned 「〜てください」 for polite requests. I used it ordering at a café.',
                )

        CurriculumItem.objects.get_or_create(
            title='Welcome to the studio',
            defaults={
                'content': 'Practice daily. Bring your notebook.',
                'sort_order': 1,
                'is_published': True,
            },
        )

        TeacherStudentAssignment.objects.get_or_create(teacher=teacher, student=student)
        TeacherStudentAssignment.objects.get_or_create(teacher=teacher, student=student_2)
        track = CurriculumTrack.objects.filter(title='Beginner Japanese path').first()
        if track is None:
            track, _ = create_track(
                title='Beginner Japanese path',
                description='A studio starter sequence. Your teacher may skip a module if you already know it.',
                is_template=True,
                created_by=staff_user,
                modules=[
                    {'title': 'Greetings', 'content': 'Learn こんにちは, ありがとう, and self-introduction.', 'sort_order': 0},
                    {'title': 'Hiragana あ–そ', 'content': 'Read and write the first two rows.', 'sort_order': 1},
                    {'title': 'Classroom phrases', 'content': 'Please say, please listen, I don’t understand.', 'sort_order': 2},
                    {'title': 'Simple requests', 'content': 'Use 〜てください in a café or shop.', 'sort_order': 3},
                ],
            )
        if track is not None:
            enroll_student(student, track)

        if not Message.objects.filter(subject='Welcome').exists():
            Message.objects.create(
                sender=teacher,
                recipient=student,
                subject='Welcome',
                body='Glad you joined. Book an open session when you are ready.',
            )

        if options['showcase']:
            self._apply_showcase_seed(student, teacher, catalog)

        self.stdout.write(self.style.SUCCESS('Demo data ready.'))
        self.stdout.write('  demo_teacher / demo1234')
        self.stdout.write('  demo_student / demo1234')
        self.stdout.write('  demo_student_2, demo_student_3, demo_student_4 / demo1234')
        if grant_admin:
            self.stdout.write('  demo_staff / demo1234  (staff + Django admin at /admin/)')
        else:
            self.stdout.write('  demo_staff / demo1234  (staff app only — pass --staff-superuser for /admin/)')
        owner, owner_created = self._ensure_owner_teacher()
        if owner_created:
            self.stdout.write('  gnogonzalez / demo1234  (teacher)')
        else:
            self.stdout.write('  gnogonzalez@gmail.com — teacher role ensured')
        self.stdout.write('  7 Japanese + 4 English classes; membership plans (students start without one).')
        if options['showcase']:
            self.stdout.write('  Showcase mode: demo_student has membership + upcoming lesson.')
