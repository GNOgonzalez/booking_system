from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone

from scheduling.models import (
    AvailabilityBlock,
    Booking,
    ClassOffering,
    ClassRequest,
    ClassTopic,
    Membership,
    MembershipPlan,
    Payment,
    Session,
)
from scheduling.services.blog import create_blog_post
from scheduling.services.booking import cancel_booking, create_booking
from scheduling.services.calendar import session_to_ics
from scheduling.services.class_requests import approve_class_request, create_class_request, deny_class_request
from scheduling.services.payments import fulfill_payment, purchase_membership
from scheduling.services.uploads import validate_blog_image, validate_homework_file


class BookingServiceTests(TestCase):
    def setUp(self):
        Group.objects.create(name='student')
        Group.objects.create(name='teacher')
        self.teacher = User.objects.create_user('t1', password='pass')
        self.teacher.groups.add(Group.objects.get(name='teacher'))
        self.student = User.objects.create_user('s1', password='pass')
        self.student.groups.add(Group.objects.get(name='student'))
        self.plan = MembershipPlan.objects.create(name='All access', price_cents=1000, ticket_allowance=10)
        self.membership = Membership.objects.create(
            user=self.student,
            plan=self.plan,
            is_active=True,
            tickets_remaining=10,
        )
        self.session = Session.objects.create(
            teacher=self.teacher,
            title='Test',
            start_time=timezone.now() + timedelta(days=1),
            end_time=timezone.now() + timedelta(days=1, hours=1),
            capacity=2,
            status='open',
        )

    def test_create_and_cancel_booking(self):
        self.assertTrue(create_booking(self.student, self.session))
        booking = Booking.objects.get(student=self.student, session=self.session)
        self.assertEqual(booking.status, 'confirmed')
        self.assertEqual(booking.tickets_spent, 1)
        self.membership.refresh_from_db()
        self.assertEqual(self.membership.tickets_remaining, 9)
        self.assertTrue(cancel_booking(self.student, booking))
        self.membership.refresh_from_db()
        self.assertEqual(self.membership.tickets_remaining, 10)
        booking.refresh_from_db()
        self.session.refresh_from_db()
        self.assertEqual(booking.status, 'cancelled')
        self.assertEqual(self.session.status, 'cancelled')

    def test_booking_requires_membership(self):
        Membership.objects.filter(user=self.student).update(is_active=False)
        self.assertFalse(create_booking(self.student, self.session))

    def test_booking_requires_tickets(self):
        self.membership.tickets_remaining = 0
        self.membership.save()
        self.assertFalse(create_booking(self.student, self.session))
        self.membership.tickets_remaining = 1
        self.membership.save()
        self.assertTrue(create_booking(self.student, self.session))

    def _create_offering(self, *, subject, level, focus, topics, ticket_cost=1):
        offering = ClassOffering.objects.create(
            teacher=self.teacher,
            subject=subject,
            level=level,
            focus=focus,
            ticket_cost=ticket_cost,
        )
        if isinstance(topics, str):
            topics = [topics]
        for index, title in enumerate(topics):
            ClassTopic.objects.create(class_offering=offering, title=title, sort_order=index)
        return offering

    def test_premium_class_costs_two_tickets(self):
        offering = self._create_offering(
            subject='Piano',
            level='Advanced',
            focus='Performance',
            topics='Recital prep',
            ticket_cost=2,
        )
        self.session.class_offering = offering
        self.session.save()
        self.membership.tickets_remaining = 1
        self.membership.save()
        self.assertFalse(create_booking(self.student, self.session))
        self.membership.tickets_remaining = 2
        self.membership.save()
        self.assertTrue(create_booking(self.student, self.session))
        booking = Booking.objects.get(student=self.student, session=self.session)
        self.assertEqual(booking.tickets_spent, 2)

    def test_booking_requires_plan_class_access(self):
        included = self._create_offering(
            subject='Piano',
            level='Beginner',
            focus='Technique',
            topics='Scales',
        )
        excluded = self._create_offering(
            subject='Piano',
            level='Beginner',
            focus='Repertoire',
            topics='Arpeggios',
        )
        restricted_plan = MembershipPlan.objects.create(name='Limited', price_cents=500, ticket_allowance=5)
        restricted_plan.allowed_classes.add(included)
        self.membership.plan = restricted_plan
        self.membership.save()
        self.session.class_offering = excluded
        self.session.save()
        self.assertFalse(create_booking(self.student, self.session))
        self.session.class_offering = included
        self.session.save()
        self.assertTrue(create_booking(self.student, self.session))

    def test_full_session_blocks_booking(self):
        self.session.capacity = 1
        self.session.save()
        other = User.objects.create_user('s2', password='pass')
        other.groups.add(Group.objects.get(name='student'))
        Membership.objects.create(user=other, plan=self.plan, is_active=True, tickets_remaining=10)
        self.assertTrue(create_booking(other, self.session))
        self.assertFalse(create_booking(self.student, self.session))

    def test_ics_generation(self):
        ics = session_to_ics(self.session)
        self.assertIn('BEGIN:VCALENDAR', ics)
        self.assertIn('SUMMARY:Test', ics)


class PaymentServiceTests(TestCase):
    def setUp(self):
        Group.objects.create(name='student')
        self.student = User.objects.create_user('s1', password='pass')
        self.student.groups.add(Group.objects.get(name='student'))
        self.plan = MembershipPlan.objects.create(name='Basic', price_cents=2000, ticket_allowance=8)

    def test_purchase_membership_activates(self):
        membership, error = purchase_membership(self.student, self.plan.id)
        self.assertIsNone(error)
        self.assertTrue(membership.is_active)
        self.assertIsNotNone(membership.valid_until)
        self.assertEqual(membership.tickets_remaining, 8)
        payment = Payment.objects.filter(user=self.student, plan=self.plan).first()
        self.assertIsNotNone(payment)
        self.assertEqual(payment.amount_cents, self.plan.price_cents)
        self.assertEqual(payment.status, Payment.STATUS_COMPLETED)
        self.assertEqual(payment.provider, Payment.PROVIDER_MOCK)

    def test_purchase_extends_tickets(self):
        purchase_membership(self.student, self.plan.id, months=1)
        membership, error = purchase_membership(self.student, self.plan.id, months=1)
        self.assertIsNone(error)
        self.assertEqual(membership.tickets_remaining, 16)

    def test_purchase_second_subject_membership(self):
        english = MembershipPlan.objects.create(name='English', price_cents=2200, ticket_allowance=8)
        purchase_membership(self.student, self.plan.id)
        membership, error = purchase_membership(self.student, english.id)
        self.assertIsNone(error)
        self.assertEqual(membership.plan_id, english.id)
        self.assertEqual(
            Membership.objects.filter(user=self.student, is_active=True).count(),
            2,
        )

    def test_purchase_ticket_pack_requires_membership(self):
        pack = MembershipPlan.objects.create(
            name='Single ticket',
            plan_type=MembershipPlan.PLAN_TICKET_PACK,
            price_cents=500,
            ticket_allowance=1,
            billing_period_days=0,
        )
        membership, error = purchase_membership(self.student, pack.id)
        self.assertIsNone(membership)
        self.assertIn('membership', error.lower())

    def test_purchase_ticket_pack_adds_tickets(self):
        purchase_membership(self.student, self.plan.id)
        sub = Membership.objects.get(user=self.student, plan=self.plan)
        pack = MembershipPlan.objects.create(
            name='Single ticket',
            plan_type=MembershipPlan.PLAN_TICKET_PACK,
            price_cents=500,
            ticket_allowance=1,
            billing_period_days=0,
        )
        membership, error = purchase_membership(self.student, pack.id, membership_id=sub.id)
        self.assertIsNone(error)
        sub.refresh_from_db()
        self.assertEqual(sub.tickets_remaining, 9)

    def test_purchase_unknown_plan(self):
        membership, error = purchase_membership(self.student, 99999)
        self.assertIsNone(membership)
        self.assertIsNotNone(error)


class StaffReportsTests(TestCase):
    def setUp(self):
        Group.objects.create(name='staff')
        Group.objects.create(name='student')
        self.staff = User.objects.create_user('staff1', password='pass')
        self.staff.groups.add(Group.objects.get(name='staff'))

    def test_staff_reports_requires_staff(self):
        res = self.client.get('/api/staff/reports/')
        self.assertEqual(res.status_code, 401)

    def test_staff_reports_returns_sections(self):
        res = self.client.post(
            '/api/auth/token/',
            {'username': 'staff1', 'password': 'pass'},
            content_type='application/json',
        )
        token = res.json()['access']
        res = self.client.get(
            '/api/staff/reports/?days=30',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn('financials', data)
        self.assertIn('bookings', data)
        self.assertIn('teachers', data)
        self.assertIn('students', data)


class StripePaymentTests(TestCase):
    def setUp(self):
        Group.objects.create(name='student')
        self.student = User.objects.create_user('s1', password='pass')
        self.student.groups.add(Group.objects.get(name='student'))
        self.plan = MembershipPlan.objects.create(name='Basic', price_cents=2000, ticket_allowance=8)

    def test_fulfill_pending_payment(self):
        payment = Payment.objects.create(
            user=self.student,
            plan=self.plan,
            amount_cents=2000,
            quantity=1,
            provider=Payment.PROVIDER_STRIPE,
            status=Payment.STATUS_PENDING,
        )
        membership, error = fulfill_payment(payment.id, stripe_checkout_session_id='cs_test')
        self.assertIsNone(error)
        self.assertTrue(membership.is_active)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.STATUS_COMPLETED)
        self.assertEqual(payment.stripe_checkout_session_id, 'cs_test')

    def test_fulfill_payment_is_idempotent(self):
        payment = Payment.objects.create(
            user=self.student,
            plan=self.plan,
            amount_cents=2000,
            quantity=1,
            provider=Payment.PROVIDER_STRIPE,
            status=Payment.STATUS_PENDING,
        )
        fulfill_payment(payment.id)
        membership, error = fulfill_payment(payment.id)
        self.assertIsNone(error)
        self.assertEqual(Membership.objects.filter(user=self.student).count(), 1)

    @override_settings(
        STRIPE={
            'SECRET_KEY': 'sk_test',
            'PUBLISHABLE_KEY': 'pk_test',
            'WEBHOOK_SECRET': '',
            'ENABLED': True,
        },
    )
    def test_mock_purchase_blocked_when_stripe_enabled(self):
        membership, error = purchase_membership(self.student, self.plan.id)
        self.assertIsNone(membership)
        self.assertIn('checkout', error.lower())

    @override_settings(DEBUG=False, ALLOW_MOCK_PAYMENTS=False)
    def test_mock_purchase_blocked_in_production_without_stripe(self):
        membership, error = purchase_membership(self.student, self.plan.id)
        self.assertIsNone(membership)
        self.assertIn('mock payments are disabled', error.lower())

    @override_settings(DEBUG=False, ALLOW_MOCK_PAYMENTS=True)
    def test_mock_purchase_allowed_when_explicitly_enabled_in_production(self):
        membership, error = purchase_membership(self.student, self.plan.id)
        self.assertIsNone(error)
        self.assertTrue(membership.is_active)

    @override_settings(DEBUG=False, ALLOW_MOCK_PAYMENTS=False)
    def test_api_membership_post_blocked_in_production(self):
        res = self.client.post(
            '/api/auth/token/',
            {'username': 's1', 'password': 'pass'},
            content_type='application/json',
        )
        token = res.json()['access']
        res = self.client.post(
            '/api/membership/',
            {'plan_id': self.plan.id, 'months': 1},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn('mock payments are disabled', res.json()['detail'].lower())

    @override_settings(
        STRIPE={
            'SECRET_KEY': 'sk_test',
            'PUBLISHABLE_KEY': 'pk_test',
            'WEBHOOK_SECRET': 'whsec_test',
            'ENABLED': True,
        },
    )
    def test_webhook_checkout_completed_fulfills_payment(self):
        import json
        from unittest.mock import patch

        payment = Payment.objects.create(
            user=self.student,
            plan=self.plan,
            amount_cents=2000,
            quantity=1,
            provider=Payment.PROVIDER_STRIPE,
            status=Payment.STATUS_PENDING,
        )
        payload = json.dumps({
            'type': 'checkout.session.completed',
            'data': {
                'object': {
                    'id': 'cs_test_webhook',
                    'metadata': {'payment_id': str(payment.id)},
                    'payment_intent': 'pi_test',
                },
            },
        })
        with patch('integrations.stripe.webhooks.verify_webhook_signature', return_value=True):
            res = self.client.post(
                '/api/payments/stripe/webhook/',
                payload,
                content_type='application/json',
                HTTP_STRIPE_SIGNATURE='t=1,v1=test',
            )
        self.assertEqual(res.status_code, 200, res.content)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.STATUS_COMPLETED)
        self.assertTrue(Membership.objects.filter(user=self.student, is_active=True).exists())


class OnboardingApiTests(TestCase):
    def setUp(self):
        Group.objects.create(name='student')
        self.student = User.objects.create_user('onboard_student', password='pass')
        self.student.groups.add(Group.objects.get(name='student'))

    def _token(self):
        res = self.client.post(
            '/api/auth/token/',
            {'username': self.student.username, 'password': 'pass'},
            content_type='application/json',
        )
        return res.json()['access']

    def test_onboarding_lists_student_steps(self):
        token = self._token()
        res = self.client.get('/api/me/onboarding/', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertFalse(body['dismissed'])
        self.assertGreaterEqual(len(body['steps']), 3)

    def test_onboarding_dismiss(self):
        token = self._token()
        res = self.client.patch(
            '/api/me/onboarding/',
            {'dismissed': True},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()['dismissed'])


class ThemeApiTests(TestCase):
    def setUp(self):
        Group.objects.create(name='student')
        self.student = User.objects.create_user('theme_student', password='pass')
        self.student.groups.add(Group.objects.get(name='student'))

    def test_patch_theme_persists(self):
        res = self.client.post(
            '/api/auth/token/',
            {'username': self.student.username, 'password': 'pass'},
            content_type='application/json',
        )
        token = res.json()['access']
        res = self.client.patch(
            '/api/me/',
            {'theme': 'dark'},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['theme'], 'dark')


class SessionListQueryTests(TestCase):
    """Session list APIs should not query bookings once per row (Phase 7)."""

    def setUp(self):
        Group.objects.create(name='student')
        Group.objects.create(name='teacher')
        self.teacher = User.objects.create_user('list_teacher', password='pass')
        self.teacher.groups.add(Group.objects.get(name='teacher'))
        self.student = User.objects.create_user('list_student', password='pass')
        self.student.groups.add(Group.objects.get(name='student'))
        plan = MembershipPlan.objects.create(name='All access', price_cents=1000, ticket_allowance=10)
        Membership.objects.create(user=self.student, plan=plan, is_active=True, tickets_remaining=10)
        start = timezone.now() + timedelta(days=1)
        for i in range(5):
            session = Session.objects.create(
                teacher=self.teacher,
                title=f'Session {i}',
                start_time=start + timedelta(hours=i),
                end_time=start + timedelta(hours=i + 1),
                capacity=3,
                status='open',
            )
            Booking.objects.create(session=session, student=self.student, status='confirmed')

    def test_sessions_for_list_uses_one_query(self):
        from scheduling.services.sessions import sessions_for_list

        with self.assertNumQueries(1):
            rows = list(sessions_for_list(Session.objects.all()))
        self.assertEqual(len(rows), 5)

    def test_serializer_uses_annotated_count(self):
        from scheduling.api.serializers import SessionSerializer
        from scheduling.services.sessions import sessions_for_list

        session = sessions_for_list(Session.objects.all()).first()
        data = SessionSerializer(session).data
        self.assertEqual(data['confirmed_count'], 1)


class IdorPermissionTests(TestCase):
    """Cross-user object access must 404; cross-role endpoint access must 403 (Phase 8)."""

    def setUp(self):
        Group.objects.create(name='student')
        Group.objects.create(name='teacher')
        Group.objects.create(name='staff')
        self.student_a = User.objects.create_user('idor_student_a', password='pass')
        self.student_a.groups.add(Group.objects.get(name='student'))
        self.student_b = User.objects.create_user('idor_student_b', password='pass')
        self.student_b.groups.add(Group.objects.get(name='student'))
        self.teacher_a = User.objects.create_user('idor_teacher_a', password='pass')
        self.teacher_a.groups.add(Group.objects.get(name='teacher'))
        self.teacher_b = User.objects.create_user('idor_teacher_b', password='pass')
        self.teacher_b.groups.add(Group.objects.get(name='teacher'))

        plan = MembershipPlan.objects.create(name='Plan', price_cents=1000, ticket_allowance=10)
        Membership.objects.create(user=self.student_b, plan=plan, is_active=True, tickets_remaining=10)

        start = timezone.now() + timedelta(days=1)
        self.session_b = Session.objects.create(
            teacher=self.teacher_b,
            title='Teacher B session',
            start_time=start,
            end_time=start + timedelta(hours=1),
            capacity=2,
            status='open',
        )
        self.booking_b = Booking.objects.create(
            session=self.session_b,
            student=self.student_b,
            status='confirmed',
        )
        self.availability_b = AvailabilityBlock.objects.create(
            teacher=self.teacher_b,
            weekday=0,
            start_time='09:00',
            end_time='17:00',
        )
        self.offering_b = ClassOffering.objects.create(
            teacher=self.teacher_b,
            subject='Piano',
            level='Beginner',
            focus='Technique',
        )

        # Journal homework from teacher B to student B (no file upload needed)
        past = timezone.now() - timedelta(days=1)
        self.past_session_b = Session.objects.create(
            teacher=self.teacher_b,
            title='Past session',
            start_time=past,
            end_time=past + timedelta(hours=1),
            capacity=1,
            status='open',
        )
        Booking.objects.create(session=self.past_session_b, student=self.student_b, status='confirmed')
        from progress.homework_services import create_homework_assignment

        self.homework_b, error = create_homework_assignment(
            teacher=self.teacher_b,
            student=self.student_b,
            session=self.past_session_b,
            kind='journal',
            prompt='Reflect on the lesson.',
        )
        self.assertIsNone(error)

        from progress.models import SessionFeedback

        self.feedback_b = SessionFeedback.objects.create(
            student=self.student_b,
            teacher=self.teacher_b,
            session=self.past_session_b,
            class_notes='Private notes',
        )

    def _token(self, user):
        res = self.client.post(
            '/api/auth/token/',
            {'username': user.username, 'password': 'pass'},
            content_type='application/json',
        )
        self.assertEqual(res.status_code, 200)
        return res.json()['access']

    def _get(self, user, path):
        return self.client.get(path, HTTP_AUTHORIZATION=f'Bearer {self._token(user)}')

    def _post(self, user, path, data=None):
        return self.client.post(
            path,
            data or {},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self._token(user)}',
        )

    def _patch(self, user, path, data):
        return self.client.patch(
            path,
            data,
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self._token(user)}',
        )

    # --- IDOR: object ownership ---

    def test_student_cannot_read_another_students_homework(self):
        res = self._get(self.student_a, f'/api/progress/homework/{self.homework_b.id}/')
        self.assertEqual(res.status_code, 404)

    def test_student_cannot_post_entry_on_another_students_homework(self):
        res = self.client.post(
            f'/api/progress/homework/{self.homework_b.id}/entries/',
            {'body': 'Injected entry'},
            HTTP_AUTHORIZATION=f'Bearer {self._token(self.student_a)}',
        )
        self.assertEqual(res.status_code, 404)

    def test_student_cannot_cancel_another_students_booking(self):
        res = self._post(self.student_a, f'/api/bookings/{self.booking_b.id}/cancel/')
        self.assertEqual(res.status_code, 404)
        self.booking_b.refresh_from_db()
        self.assertEqual(self.booking_b.status, 'confirmed')

    def test_teacher_cannot_read_another_teachers_homework(self):
        res = self._get(self.teacher_a, f'/api/progress/homework/teacher/{self.homework_b.id}/')
        self.assertEqual(res.status_code, 404)

    def test_teacher_cannot_edit_another_teachers_availability(self):
        res = self._patch(
            self.teacher_a,
            f'/api/teacher/availability/{self.availability_b.id}/',
            {'end_time': '18:00'},
        )
        self.assertEqual(res.status_code, 404)

    def test_teacher_cannot_edit_another_teachers_class(self):
        res = self._patch(
            self.teacher_a,
            f'/api/teacher/classes/{self.offering_b.id}/',
            {'focus': 'Hijacked'},
        )
        self.assertEqual(res.status_code, 404)
        self.offering_b.refresh_from_db()
        self.assertEqual(self.offering_b.focus, 'Technique')

    def test_teacher_cannot_edit_another_teachers_feedback(self):
        res = self._patch(
            self.teacher_a,
            f'/api/progress/feedback/teacher/{self.feedback_b.id}/',
            {'class_notes': 'Tampered'},
        )
        self.assertEqual(res.status_code, 404)
        self.feedback_b.refresh_from_db()
        self.assertEqual(self.feedback_b.class_notes, 'Private notes')

    # --- Role boundaries ---

    def test_student_cannot_list_staff_teachers(self):
        res = self._get(self.student_a, '/api/staff/teachers/')
        self.assertEqual(res.status_code, 403)

    def test_teacher_cannot_list_staff_teachers(self):
        res = self._get(self.teacher_a, '/api/staff/teachers/')
        self.assertEqual(res.status_code, 403)

    def test_student_cannot_use_teacher_session_api(self):
        res = self._get(self.student_a, '/api/teacher/sessions/')
        self.assertEqual(res.status_code, 403)

    def test_teacher_cannot_use_student_booking_api(self):
        res = self._get(self.teacher_a, '/api/bookings/')
        self.assertEqual(res.status_code, 403)

    def test_unauthenticated_rejected_everywhere(self):
        for path in ('/api/bookings/', '/api/teacher/sessions/', '/api/staff/teachers/'):
            res = self.client.get(path)
            self.assertEqual(res.status_code, 401, path)


class AuthRateLimitTests(TestCase):
    """Brute-force protection on JWT obtain and refresh (Phase 6)."""

    def setUp(self):
        from django.core.cache import cache

        cache.clear()
        Group.objects.create(name='student')
        self.user = User.objects.create_user('ratelimit_user', password='pass')
        self.user.groups.add(Group.objects.get(name='student'))

    def tearDown(self):
        from django.core.cache import cache

        cache.clear()

    def _post_token(self, password='wrong'):
        return self.client.post(
            '/api/auth/token/',
            {'username': 'ratelimit_user', 'password': password},
            content_type='application/json',
        )

    def test_login_rate_throttle_blocks_eleventh_attempt(self):
        from unittest.mock import patch

        from django.core.cache import cache
        from rest_framework.test import APIRequestFactory

        from scheduling.api.auth_views import ThrottledTokenObtainPairView
        from scheduling.api.throttling import LoginRateThrottle

        cache.clear()
        request = APIRequestFactory().post('/api/auth/token/')
        view = ThrottledTokenObtainPairView()
        with patch.object(LoginRateThrottle, 'get_rate', return_value='10/minute'):
            throttle = LoginRateThrottle()
            for _ in range(10):
                self.assertTrue(
                    throttle.allow_request(request, view),
                    'Expected attempt to be allowed',
                )
            self.assertFalse(
                throttle.allow_request(request, view),
                'Expected 11th attempt to be throttled',
            )

    def test_token_obtain_view_uses_login_throttle(self):
        from scheduling.api.auth_views import ThrottledTokenObtainPairView
        from scheduling.api.throttling import LoginRateThrottle

        self.assertIn(LoginRateThrottle, ThrottledTokenObtainPairView.throttle_classes)


class SecurityHeaderTests(TestCase):
    """CSP middleware — on for production responses, off in DEBUG (Phase 5)."""

    def test_csp_header_present_when_debug_off(self):
        with override_settings(DEBUG=False):
            res = self.client.get('/accounts/login/')
        self.assertIn('Content-Security-Policy', res.headers)
        self.assertIn("script-src 'self'", res.headers['Content-Security-Policy'])

    def test_csp_header_absent_in_debug(self):
        with override_settings(DEBUG=True):
            res = self.client.get('/accounts/login/')
        self.assertNotIn('Content-Security-Policy', res.headers)


class ApiSmokeTests(TestCase):
    def setUp(self):
        Group.objects.create(name='student')
        self.student = User.objects.create_user('s1', password='pass')
        self.student.groups.add(Group.objects.get(name='student'))

    def test_jwt_and_open_sessions(self):
        res = self.client.post(
            '/api/auth/token/',
            {'username': 's1', 'password': 'pass'},
            content_type='application/json',
        )
        self.assertEqual(res.status_code, 200)
        token = res.json()['access']
        res = self.client.get(
            '/api/sessions/open/',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(res.status_code, 200)


class UploadValidationTests(TestCase):
    def test_homework_rejects_oversized_file(self):
        big = SimpleUploadedFile('big.pdf', b'x' * (10 * 1024 * 1024 + 1))
        error = validate_homework_file(big)
        self.assertIn('10 MB', error)

    def test_homework_rejects_bad_extension(self):
        bad = SimpleUploadedFile('notes.exe', b'ok', content_type='application/octet-stream')
        error = validate_homework_file(bad)
        self.assertIn('not allowed', error.lower())

    def test_blog_image_rejects_bad_extension(self):
        bad = SimpleUploadedFile('pic.bmp', b'ok', content_type='image/bmp')
        error = validate_blog_image(bad)
        self.assertIn('not allowed', error.lower())


class BlogApiTests(TestCase):
    def setUp(self):
        Group.objects.create(name='student')
        Group.objects.create(name='teacher')
        Group.objects.create(name='staff')
        self.student = User.objects.create_user('student', password='pass')
        self.student.groups.add(Group.objects.get(name='student'))
        self.teacher = User.objects.create_user('teacher', password='pass')
        self.teacher.groups.add(Group.objects.get(name='teacher'))
        self.staff = User.objects.create_user('staff', password='pass')
        self.staff.groups.add(Group.objects.get(name='staff'))

    def _token(self, user):
        res = self.client.post(
            '/api/auth/token/',
            {'username': user.username, 'password': 'pass'},
            content_type='application/json',
        )
        self.assertEqual(res.status_code, 200)
        return res.json()['access']

    def test_staff_can_create_and_list_blog_post(self):
        token = self._token(self.staff)
        res = self.client.post(
            '/api/blog/manage/',
            {
                'title': 'Welcome',
                'body': 'Studio news for everyone.',
                'is_published': 'true',
            },
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(res.status_code, 201)
        res = self.client.get('/api/blog/', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()), 1)
        self.assertEqual(res.json()[0]['title'], 'Welcome')

    def test_student_cannot_create_blog_post(self):
        token = self._token(self.student)
        res = self.client.post(
            '/api/blog/manage/',
            {'title': 'Nope', 'body': 'Should fail'},
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(res.status_code, 403)

    def test_upload_limits_endpoint(self):
        token = self._token(self.student)
        res = self.client.get('/api/upload-limits/', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['homework_max_mb'], 10)
        self.assertEqual(data['blog_image_max_mb'], 5)
        self.assertEqual(data['logo_max_mb'], 2)

    def test_unpublished_post_hidden_from_feed(self):
        post, _ = create_blog_post(self.staff, title='Draft', body='Hidden', is_published=False)
        token = self._token(self.student)
        res = self.client.get('/api/blog/', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(res.json(), [])
        res = self.client.get(f'/api/blog/{post.id}/', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(res.status_code, 404)


class BrandingApiTests(TestCase):
    def setUp(self):
        Group.objects.create(name='staff')
        self.staff = User.objects.create_user('staff', password='pass')
        self.staff.groups.add(Group.objects.get(name='staff'))

    def _token(self, user):
        res = self.client.post(
            '/api/auth/token/',
            {'username': user.username, 'password': 'pass'},
            content_type='application/json',
        )
        return res.json()['access']

    def test_public_branding_endpoint(self):
        res = self.client.get('/api/branding/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['display_name'], 'Booking Studio')
        self.assertIsNone(res.json()['logo_url'])

    def test_staff_can_update_display_name(self):
        token = self._token(self.staff)
        res = self.client.patch(
            '/api/staff/branding/',
            {'display_name': 'Acme Music Studio'},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['display_name'], 'Acme Music Studio')
        res = self.client.get('/api/branding/')
        self.assertEqual(res.json()['display_name'], 'Acme Music Studio')


class ClassRequestTests(TestCase):
    def setUp(self):
        Group.objects.create(name='student')
        Group.objects.create(name='teacher')
        self.teacher = User.objects.create_user('teacher', password='pass')
        self.teacher.groups.add(Group.objects.get(name='teacher'))
        self.student = User.objects.create_user('student', password='pass')
        self.student.groups.add(Group.objects.get(name='student'))
        self.plan = MembershipPlan.objects.create(name='All access', price_cents=1000, ticket_allowance=10)
        self.membership = Membership.objects.create(
            user=self.student,
            plan=self.plan,
            is_active=True,
            tickets_remaining=5,
        )
        self.offering = ClassOffering.objects.create(
            teacher=self.teacher,
            subject='Piano',
            level='Beginner',
            focus='Technique',
            ticket_cost=2,
            default_capacity=3,
        )
        self.topic = ClassTopic.objects.create(class_offering=self.offering, title='Scales', sort_order=0)
        self.start = timezone.now() + timedelta(days=2)
        self.start = self.start.replace(hour=10, minute=0, second=0, microsecond=0)
        self.end = self.start + timedelta(hours=1)
        AvailabilityBlock.objects.create(
            teacher=self.teacher,
            weekday=self.start.weekday(),
            start_time=self.start.time(),
            end_time=self.end.time(),
        )

    def _token(self, user):
        res = self.client.post(
            '/api/auth/token/',
            {'username': user.username, 'password': 'pass'},
            content_type='application/json',
        )
        self.assertEqual(res.status_code, 200)
        return res.json()['access']

    def test_request_holds_tickets_until_approved(self):
        request, error = create_class_request(
            self.student,
            teacher=self.teacher,
            class_offering=self.offering,
            class_topic=self.topic,
            start_time=self.start,
            end_time=self.end,
            tickets_requested=2,
        )
        self.assertIsNone(error)
        self.membership.refresh_from_db()
        self.assertEqual(self.membership.tickets_remaining, 3)

        approved, error = approve_class_request(self.teacher, request)
        self.assertIsNone(error)
        self.assertEqual(approved.status, ClassRequest.STATUS_APPROVED)
        self.membership.refresh_from_db()
        self.assertEqual(self.membership.tickets_remaining, 3)
        booking = Booking.objects.get(class_request=request)
        self.assertEqual(booking.tickets_spent, 2)

    def test_denied_request_returns_tickets(self):
        request, _ = create_class_request(
            self.student,
            teacher=self.teacher,
            class_offering=self.offering,
            class_topic=None,
            start_time=self.start,
            end_time=self.end,
            tickets_requested=2,
        )
        deny_class_request(self.teacher, request)
        self.membership.refresh_from_db()
        self.assertEqual(self.membership.tickets_remaining, 5)

    def test_cancel_approved_request_booking_does_not_refund(self):
        request, _ = create_class_request(
            self.student,
            teacher=self.teacher,
            class_offering=self.offering,
            class_topic=None,
            start_time=self.start,
            end_time=self.end,
            tickets_requested=2,
        )
        approve_class_request(self.teacher, request)
        booking = Booking.objects.get(class_request=request)
        cancel_booking(self.student, booking)
        self.membership.refresh_from_db()
        self.assertEqual(self.membership.tickets_remaining, 3)
        request.session.refresh_from_db()
        self.assertEqual(request.session.status, 'cancelled')

    def test_cancel_keeps_session_when_other_students_booked(self):
        request, _ = create_class_request(
            self.student,
            teacher=self.teacher,
            class_offering=self.offering,
            class_topic=None,
            start_time=self.start,
            end_time=self.end,
            tickets_requested=2,
        )
        approve_class_request(self.teacher, request, capacity=3)
        session = request.session
        other = User.objects.create_user('other', password='pass')
        other.groups.add(Group.objects.get(name='student'))
        Membership.objects.create(user=other, plan=self.plan, is_active=True, tickets_remaining=5)
        create_booking(other, session)
        booking = Booking.objects.get(class_request=request)
        cancel_booking(self.student, booking)
        session.refresh_from_db()
        self.assertEqual(session.status, 'open')
        self.assertEqual(session.bookings.filter(status='confirmed').count(), 1)

    def test_student_can_create_request_via_api(self):
        token = self._token(self.student)
        res = self.client.post(
            '/api/class-requests/',
            {
                'teacher': self.teacher.id,
                'class_offering': self.offering.id,
                'class_topic': self.topic.id,
                'start_time': self.start.isoformat(),
                'end_time': self.end.isoformat(),
                'tickets_requested': 2,
            },
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(res.status_code, 201)
        self.membership.refresh_from_db()
        self.assertEqual(self.membership.tickets_remaining, 3)


class TeacherSessionApiTests(TestCase):
    def setUp(self):
        Group.objects.create(name='teacher')
        self.teacher = User.objects.create_user('teacher', password='pass')
        self.teacher.groups.add(Group.objects.get(name='teacher'))
        self.other = User.objects.create_user('other', password='pass')
        self.other.groups.add(Group.objects.get(name='teacher'))
        start = timezone.now() + timedelta(days=2)
        end = start + timedelta(hours=1)
        self.session = Session.objects.create(
            teacher=self.teacher,
            title='Patch me',
            start_time=start,
            end_time=end,
            capacity=2,
            status='open',
        )
        self.other_session = Session.objects.create(
            teacher=self.other,
            title='Not yours',
            start_time=start,
            end_time=end,
            capacity=1,
            status='open',
        )

    def _token(self, user):
        res = self.client.post(
            '/api/auth/token/',
            {'username': user.username, 'password': 'pass'},
            content_type='application/json',
        )
        self.assertEqual(res.status_code, 200)
        return res.json()['access']

    def test_teacher_can_patch_own_session_capacity(self):
        token = self._token(self.teacher)
        res = self.client.patch(
            f'/api/teacher/sessions/{self.session.id}/',
            {'capacity': 5},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['capacity'], 5)
        self.session.refresh_from_db()
        self.assertEqual(self.session.capacity, 5)

    def test_teacher_can_delete_own_session(self):
        token = self._token(self.teacher)
        res = self.client.delete(
            f'/api/teacher/sessions/{self.session.id}/',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['status'], 'cancelled')
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, 'cancelled')

    def test_teacher_cannot_patch_another_teachers_session(self):
        token = self._token(self.teacher)
        res = self.client.patch(
            f'/api/teacher/sessions/{self.other_session.id}/',
            {'capacity': 5},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(res.status_code, 404)
        self.other_session.refresh_from_db()
        self.assertEqual(self.other_session.capacity, 1)


class InactiveUserApiTests(TestCase):
    """Deactivated users must lose API access immediately, even with a valid JWT."""

    def setUp(self):
        Group.objects.create(name='student')
        Group.objects.create(name='teacher')
        self.student = User.objects.create_user('inactive_student', password='pass')
        self.student.groups.add(Group.objects.get(name='student'))
        self.teacher = User.objects.create_user('inactive_teacher', password='pass')
        self.teacher.groups.add(Group.objects.get(name='teacher'))

    def _token(self, user):
        res = self.client.post(
            '/api/auth/token/',
            {'username': user.username, 'password': 'pass'},
            content_type='application/json',
        )
        self.assertEqual(res.status_code, 200)
        return res.json()['access']

    def test_deactivated_student_blocked_with_valid_token(self):
        token = self._token(self.student)
        # Token works while active
        res = self.client.get('/api/bookings/', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(res.status_code, 200)
        # Staff deactivates the account; same token must now be rejected
        self.student.is_active = False
        self.student.save(update_fields=['is_active'])
        res = self.client.get('/api/bookings/', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertIn(res.status_code, (401, 403))

    def test_deactivated_teacher_blocked_with_valid_token(self):
        token = self._token(self.teacher)
        res = self.client.get('/api/teacher/sessions/', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(res.status_code, 200)
        self.teacher.is_active = False
        self.teacher.save(update_fields=['is_active'])
        res = self.client.get('/api/teacher/sessions/', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertIn(res.status_code, (401, 403))

    def test_deactivated_user_blocked_on_authenticated_only_view(self):
        """Views using plain IsAuthenticated (e.g. /api/me/) rely on the auth layer."""
        token = self._token(self.student)
        res = self.client.get('/api/me/', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(res.status_code, 200)
        self.student.is_active = False
        self.student.save(update_fields=['is_active'])
        res = self.client.get('/api/me/', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertIn(res.status_code, (401, 403))

    def test_inactive_user_cannot_obtain_token(self):
        self.student.is_active = False
        self.student.save(update_fields=['is_active'])
        res = self.client.post(
            '/api/auth/token/',
            {'username': self.student.username, 'password': 'pass'},
            content_type='application/json',
        )
        self.assertEqual(res.status_code, 401)

    def test_inactive_user_cannot_refresh_token(self):
        res = self.client.post(
            '/api/auth/token/',
            {'username': self.student.username, 'password': 'pass'},
            content_type='application/json',
        )
        refresh = res.json()['refresh']
        self.student.is_active = False
        self.student.save(update_fields=['is_active'])
        res = self.client.post(
            '/api/auth/token/refresh/',
            {'refresh': refresh},
            content_type='application/json',
        )
        self.assertEqual(res.status_code, 401)


class LLMConfigApiTests(TestCase):
    """Staff LLM config must never expose raw API keys; unsafe URLs rejected."""

    def setUp(self):
        Group.objects.create(name='staff')
        self.staff = User.objects.create_user('llm_staff', password='pass')
        self.staff.groups.add(Group.objects.get(name='staff'))
        self.token = self.client.post(
            '/api/auth/token/',
            {'username': self.staff.username, 'password': 'pass'},
            content_type='application/json',
        ).json()['access']
        self.auth = {'HTTP_AUTHORIZATION': f'Bearer {self.token}'}

    def test_get_never_returns_raw_api_key(self):
        from scheduling.models import StudioLLMConfig

        config = StudioLLMConfig.load()
        config.api_key = 'sk-secret-test-key-12345'
        config.save()
        res = self.client.get('/api/staff/llm/', **self.auth)
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertNotIn('api_key', body)
        self.assertTrue(body['has_api_key'])
        self.assertNotIn('sk-secret', body['api_key_masked'])

    def test_patch_rejects_file_url(self):
        res = self.client.patch(
            '/api/staff/llm/',
            {'base_url': 'file:///etc/passwd'},
            content_type='application/json',
            **self.auth,
        )
        self.assertEqual(res.status_code, 400)


class MarkdownRenderTests(TestCase):
    """Markdown pipeline must allow basic formatting and strip anything dangerous."""

    def test_renders_basic_formatting(self):
        from scheduling.services.markdown import render_safe_markdown

        html = render_safe_markdown('**bold** and *italic*\n\n- item one\n- item two')
        self.assertIn('<strong>bold</strong>', html)
        self.assertIn('<em>italic</em>', html)
        self.assertIn('<li>item one</li>', html)

    def test_strips_script_tags(self):
        from scheduling.services.markdown import render_safe_markdown

        html = render_safe_markdown('hello <script>alert(1)</script> world')
        self.assertNotIn('<script', html)
        self.assertNotIn('alert(1)</script>', html)

    def test_strips_javascript_urls(self):
        from scheduling.services.markdown import render_safe_markdown

        html = render_safe_markdown('[click me](javascript:alert(1))')
        self.assertNotIn('javascript:', html)

    def test_strips_event_handlers_and_iframes(self):
        from scheduling.services.markdown import render_safe_markdown

        html = render_safe_markdown('<img src=x onerror=alert(1)> <iframe src="https://evil"></iframe>')
        self.assertNotIn('onerror', html)
        self.assertNotIn('<iframe', html)
        self.assertNotIn('<img', html)

    def test_links_get_nofollow(self):
        from scheduling.services.markdown import render_safe_markdown

        html = render_safe_markdown('[site](https://example.com)')
        self.assertIn('rel="nofollow', html)

    def test_blank_input_returns_empty(self):
        from scheduling.services.markdown import render_safe_markdown

        self.assertEqual(render_safe_markdown(''), '')
        self.assertEqual(render_safe_markdown('   \n  '), '')

    def test_preview_endpoint_requires_auth(self):
        res = self.client.post(
            '/api/markdown/preview/',
            {'body': '**hi**'},
            content_type='application/json',
        )
        self.assertIn(res.status_code, (401, 403))

    def test_preview_endpoint_returns_sanitized_html(self):
        Group.objects.create(name='student')
        user = User.objects.create_user('md_student', password='pass')
        user.groups.add(Group.objects.get(name='student'))
        token = self.client.post(
            '/api/auth/token/',
            {'username': 'md_student', 'password': 'pass'},
            content_type='application/json',
        ).json()['access']
        res = self.client.post(
            '/api/markdown/preview/',
            {'body': '**bold** <script>alert(1)</script>'},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(res.status_code, 200)
        html = res.json()['html']
        self.assertIn('<strong>bold</strong>', html)
        self.assertNotIn('<script', html)


class GoogleOAuthTests(TestCase):
    def setUp(self):
        Group.objects.create(name='teacher')
        Group.objects.create(name='student')
        self.teacher = User.objects.create_user('g_teacher', password='pass')
        self.teacher.groups.add(Group.objects.get(name='teacher'))
        self.student = User.objects.create_user('g_student', password='pass')
        self.student.groups.add(Group.objects.get(name='student'))

    def _token(self, user):
        res = self.client.post(
            '/api/auth/token/',
            {'username': user.username, 'password': 'pass'},
            content_type='application/json',
        )
        return res.json()['access']

    def test_connect_returns_503_when_not_configured(self):
        token = self._token(self.teacher)
        res = self.client.get(
            '/api/integrations/google/connect/',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(res.status_code, 503)

    @override_settings(
        GOOGLE={
            'CLIENT_ID': 'test-client',
            'CLIENT_SECRET': 'test-secret',
            'ENABLED': True,
            'REDIRECT_URI': 'http://127.0.0.1:8000/integrations/google/callback/',
        },
    )
    def test_connect_returns_authorization_url(self):
        token = self._token(self.teacher)
        res = self.client.get(
            '/api/integrations/google/connect/',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(res.status_code, 200)
        url = res.json()['authorization_url']
        self.assertIn('accounts.google.com', url)
        self.assertIn('test-client', url)
        self.assertIn('state=', url)

    def test_student_cannot_connect(self):
        token = self._token(self.student)
        res = self.client.get(
            '/api/integrations/google/connect/',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(res.status_code, 403)

    def test_status_reports_not_connected(self):
        token = self._token(self.teacher)
        res = self.client.get(
            '/api/integrations/google/status/',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.json()['connected'])

    @override_settings(
        GOOGLE={
            'CLIENT_ID': 'test-client',
            'CLIENT_SECRET': 'test-secret',
            'ENABLED': True,
            'REDIRECT_URI': 'http://127.0.0.1:8000/integrations/google/callback/',
        },
    )
    def test_callback_stores_credential_and_redirects(self):
        from unittest.mock import patch

        from integrations.google.oauth import make_state
        from scheduling.models import GoogleCredential

        state = make_state(self.teacher)
        token_data = {
            'access_token': 'ya29.test',
            'refresh_token': '1//refresh',
            'expires_in': 3600,
            'scope': 'https://www.googleapis.com/auth/calendar.events',
        }
        with patch('scheduling.api.google_views.exchange_code', return_value=token_data):
            res = self.client.get(
                '/integrations/google/callback/',
                {'code': 'auth-code', 'state': state},
            )
        self.assertEqual(res.status_code, 302)
        self.assertIn('google=connected', res['Location'])
        credential = GoogleCredential.objects.get(user=self.teacher)
        self.assertEqual(credential.refresh_token, '1//refresh')

    def test_callback_with_bad_state_redirects_to_error(self):
        res = self.client.get(
            '/integrations/google/callback/',
            {'code': 'auth-code', 'state': 'tampered'},
        )
        self.assertEqual(res.status_code, 302)
        self.assertIn('google=error', res['Location'])

    def test_meet_link_falls_back_to_placeholder_without_credential(self):
        from integrations.google.meet import create_meet_link

        start = timezone.now() + timedelta(days=1)
        session = Session.objects.create(
            teacher=self.teacher,
            title='Google session',
            start_time=start,
            end_time=start + timedelta(hours=1),
            capacity=2,
            status='open',
        )
        link = create_meet_link(session)
        self.assertTrue(link.startswith('https://meet.google.com/'))

    @override_settings(
        GOOGLE={
            'CLIENT_ID': 'test-client',
            'CLIENT_SECRET': 'test-secret',
            'ENABLED': True,
            'REDIRECT_URI': 'http://127.0.0.1:8000/integrations/google/callback/',
        },
    )
    def test_meet_link_uses_calendar_event_when_connected(self):
        from unittest.mock import patch

        from integrations.google.meet import create_meet_link
        from scheduling.models import GoogleCredential

        GoogleCredential.objects.create(
            user=self.teacher,
            access_token='ya29.test',
            refresh_token='1//refresh',
            token_expires_at=timezone.now() + timedelta(hours=1),
        )
        start = timezone.now() + timedelta(days=1)
        session = Session.objects.create(
            teacher=self.teacher,
            title='Google session',
            start_time=start,
            end_time=start + timedelta(hours=1),
            capacity=2,
            status='open',
        )
        with patch(
            'integrations.google.meet._insert_calendar_event',
            return_value={'hangoutLink': 'https://meet.google.com/abc-defg-hij'},
        ):
            link = create_meet_link(session)
        self.assertEqual(link, 'https://meet.google.com/abc-defg-hij')


class LLMUrlValidationTests(TestCase):
    def test_rejects_private_openai_compatible_url(self):
        from integrations.llm.errors import LLMError
        from integrations.llm.url_validation import validate_llm_url

        with self.assertRaises(LLMError):
            validate_llm_url('http://127.0.0.1:8080/v1', provider='openai_compatible')

    def test_allows_ollama_localhost(self):
        from integrations.llm.url_validation import validate_llm_url

        validate_llm_url('http://127.0.0.1:11434', provider='ollama')
