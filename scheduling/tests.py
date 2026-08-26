from datetime import timedelta
from unittest.mock import patch

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
    StaffActionLog,
    StaffAlert,
)
from scheduling.services.blog import create_blog_post
from scheduling.services.booking import booking_block_reason, cancel_booking, create_booking
from scheduling.services.calendar import session_to_ics
from scheduling.services.class_requests import approve_class_request, create_class_request, deny_class_request
from scheduling.services.payments import fulfill_payment, purchase_membership
from scheduling.services.registration import register_student
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

    @patch('scheduling.services.notifications.send_mail')
    def test_booking_emails_student_and_teacher(self, mock_send_mail):
        self.student.email = 'student@example.com'
        self.student.save(update_fields=['email'])
        self.teacher.email = 'teacher@example.com'
        self.teacher.save(update_fields=['email'])
        self.assertTrue(create_booking(self.student, self.session))
        self.assertEqual(mock_send_mail.call_count, 2)
        recipients = [call.args[3][0] for call in mock_send_mail.call_args_list]
        self.assertIn('student@example.com', recipients)
        self.assertIn('teacher@example.com', recipients)
        teacher_call = next(
            call for call in mock_send_mail.call_args_list if call.args[3][0] == 'teacher@example.com'
        )
        self.assertIn('New booking:', teacher_call.args[0])
        self.assertIn('s1 booked', teacher_call.args[1])

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

    def test_subject_membership_covers_any_teacher_class(self):
        other_teacher = User.objects.create_user('t2', password='pass')
        other_teacher.groups.add(Group.objects.get(name='teacher'))
        offering = self._create_offering(
            subject='Japanese',
            level='Beginner',
            focus='Speaking',
            topics='Greetings',
        )
        offering.teacher = other_teacher
        offering.save()
        japanese_plan = MembershipPlan.objects.create(
            name='Japanese',
            subject='Japanese',
            price_cents=2000,
            ticket_allowance=10,
        )
        self.membership.plan = japanese_plan
        self.membership.save()
        self.session.class_offering = offering
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
        self.assertEqual(
            booking_block_reason(self.student, self.session),
            'This session is full.',
        )

    def test_duplicate_booking_reason(self):
        self.assertTrue(create_booking(self.student, self.session))
        self.assertEqual(
            booking_block_reason(self.student, self.session),
            'You already have a booking for this session.',
        )

    def test_ics_generation(self):
        ics = session_to_ics(self.session)
        self.assertIn('BEGIN:VCALENDAR', ics)
        self.assertIn('SUMMARY:Test', ics)


@override_settings(
    STRIPE={'SECRET_KEY': '', 'PUBLISHABLE_KEY': '', 'WEBHOOK_SECRET': '', 'ENABLED': False},
)
class PaymentServiceTests(TestCase):
    """Mock-payment flows — Stripe explicitly disabled so local .env keys don't leak in."""

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


class StaffAlertsTests(TestCase):
    def setUp(self):
        Group.objects.create(name='staff')
        Group.objects.create(name='student')
        self.staff = User.objects.create_user('staff1', password='pass')
        self.staff.groups.add(Group.objects.get(name='staff'))
        self.staff2 = User.objects.create_user('staff2', password='pass')
        self.staff2.groups.add(Group.objects.get(name='staff'))
        self.student = User.objects.create_user('s1', password='pass')
        self.student.groups.add(Group.objects.get(name='student'))
        self.plan = MembershipPlan.objects.create(
            name='Basic',
            price_cents=2000,
            ticket_allowance=8,
        )

    def _staff_token(self, user='staff1'):
        res = self.client.post(
            '/api/auth/token/',
            {'username': user, 'password': 'pass'},
            content_type='application/json',
        )
        return res.json()['access']

    def test_register_creates_users_alert(self):
        user, error = register_student(
            username='newbie',
            email='newbie@example.com',
            password='demo1234!',
            display_name='Newbie',
        )
        self.assertIsNone(error)
        self.assertIsNotNone(user)
        alert = StaffAlert.objects.get(category=StaffAlert.CATEGORY_USERS)
        self.assertEqual(alert.event_type, StaffAlert.EVENT_STUDENT_REGISTERED)
        self.assertEqual(alert.actor_id, user.id)

    def test_purchase_creates_financial_and_membership_alerts(self):
        with override_settings(
            STRIPE={
                'SECRET_KEY': '',
                'PUBLISHABLE_KEY': '',
                'WEBHOOK_SECRET': '',
                'ENABLED': False,
            },
            DEBUG=True,
            ALLOW_MOCK_PAYMENTS=True,
        ):
            membership, error = purchase_membership(self.student, self.plan.id)
            self.assertIsNone(error)
            self.assertIsNotNone(membership)
            financial = StaffAlert.objects.filter(category=StaffAlert.CATEGORY_FINANCIAL)
            membership_alerts = StaffAlert.objects.filter(category=StaffAlert.CATEGORY_MEMBERSHIP)
            self.assertEqual(financial.count(), 1)
            self.assertEqual(membership_alerts.count(), 1)
            self.assertEqual(financial.get().event_type, StaffAlert.EVENT_PAYMENT_COMPLETED)
            self.assertEqual(
                membership_alerts.get().event_type,
                StaffAlert.EVENT_MEMBERSHIP_ACTIVATED,
            )

            purchase_membership(self.student, self.plan.id)
            self.assertEqual(
                StaffAlert.objects.filter(
                    category=StaffAlert.CATEGORY_MEMBERSHIP,
                    event_type=StaffAlert.EVENT_MEMBERSHIP_RENEWED,
                ).count(),
                1,
            )

    def test_fulfill_payment_creates_alerts_once(self):
        payment = Payment.objects.create(
            user=self.student,
            plan=self.plan,
            amount_cents=2000,
            quantity=1,
            provider=Payment.PROVIDER_STRIPE,
            status=Payment.STATUS_PENDING,
        )
        fulfill_payment(payment.id)
        self.assertEqual(StaffAlert.objects.filter(category=StaffAlert.CATEGORY_FINANCIAL).count(), 1)
        fulfill_payment(payment.id)
        self.assertEqual(StaffAlert.objects.filter(category=StaffAlert.CATEGORY_FINANCIAL).count(), 1)

    def test_staff_alerts_requires_staff(self):
        res = self.client.get('/api/staff/alerts/')
        self.assertEqual(res.status_code, 401)

        student_token = self.client.post(
            '/api/auth/token/',
            {'username': 's1', 'password': 'pass'},
            content_type='application/json',
        ).json()['access']
        res = self.client.get(
            '/api/staff/alerts/',
            HTTP_AUTHORIZATION=f'Bearer {student_token}',
        )
        self.assertEqual(res.status_code, 403)

    def test_staff_alerts_list_and_mark_read_per_user(self):
        register_student(
            username='newbie',
            email='newbie@example.com',
            password='demo1234!',
        )
        with override_settings(
            STRIPE={
                'SECRET_KEY': '',
                'PUBLISHABLE_KEY': '',
                'WEBHOOK_SECRET': '',
                'ENABLED': False,
            },
            DEBUG=True,
            ALLOW_MOCK_PAYMENTS=True,
        ):
            purchase_membership(self.student, self.plan.id)

        token = self._staff_token('staff1')
        res = self.client.get(
            '/api/staff/alerts/',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data['users']), 1)
        self.assertEqual(len(data['financial']), 1)
        self.assertEqual(len(data['membership']), 1)
        self.assertEqual(data['unread']['total'], 3)
        self.assertTrue(data['users'][0]['is_unread'])

        res = self.client.post(
            '/api/staff/alerts/mark-read/',
            {'all': True},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['unread']['total'], 0)

        token2 = self._staff_token('staff2')
        res = self.client.get(
            '/api/staff/alerts/',
            HTTP_AUTHORIZATION=f'Bearer {token2}',
        )
        self.assertEqual(res.json()['unread']['total'], 3)


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

    @override_settings(
        DEBUG=False,
        ALLOW_MOCK_PAYMENTS=False,
        STRIPE={'SECRET_KEY': '', 'PUBLISHABLE_KEY': '', 'WEBHOOK_SECRET': '', 'ENABLED': False},
    )
    def test_mock_purchase_blocked_in_production_without_stripe(self):
        membership, error = purchase_membership(self.student, self.plan.id)
        self.assertIsNone(membership)
        self.assertIn('mock payments are disabled', error.lower())

    @override_settings(
        DEBUG=False,
        ALLOW_MOCK_PAYMENTS=True,
        STRIPE={'SECRET_KEY': '', 'PUBLISHABLE_KEY': '', 'WEBHOOK_SECRET': '', 'ENABLED': False},
    )
    def test_mock_purchase_allowed_when_explicitly_enabled_in_production(self):
        membership, error = purchase_membership(self.student, self.plan.id)
        self.assertIsNone(error)
        self.assertTrue(membership.is_active)

    @override_settings(
        DEBUG=False,
        ALLOW_MOCK_PAYMENTS=False,
        STRIPE={'SECRET_KEY': '', 'PUBLISHABLE_KEY': '', 'WEBHOOK_SECRET': '', 'ENABLED': False},
    )
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

    def test_payment_status_for_owner(self):
        payment = Payment.objects.create(
            user=self.student,
            plan=self.plan,
            amount_cents=2000,
            quantity=1,
            provider=Payment.PROVIDER_STRIPE,
            status=Payment.STATUS_PENDING,
        )
        token_res = self.client.post(
            '/api/auth/token/',
            {'username': 's1', 'password': 'pass'},
            content_type='application/json',
        )
        token = token_res.json()['access']
        res = self.client.get(
            f'/api/membership/payments/{payment.id}/',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body['status'], Payment.STATUS_PENDING)
        self.assertEqual(body['plan_name'], self.plan.name)

    def test_payment_status_hidden_from_other_users(self):
        other = User.objects.create_user('other', password='pass')
        other.groups.add(Group.objects.get(name='student'))
        payment = Payment.objects.create(
            user=self.student,
            plan=self.plan,
            amount_cents=2000,
            quantity=1,
            provider=Payment.PROVIDER_STRIPE,
            status=Payment.STATUS_PENDING,
        )
        token_res = self.client.post(
            '/api/auth/token/',
            {'username': 'other', 'password': 'pass'},
            content_type='application/json',
        )
        token = token_res.json()['access']
        res = self.client.get(
            f'/api/membership/payments/{payment.id}/',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(res.status_code, 404)


class StripeWebhookSignatureTests(TestCase):
    @override_settings(
        STRIPE={
            'SECRET_KEY': 'sk_test',
            'PUBLISHABLE_KEY': 'pk_test',
            'WEBHOOK_SECRET': 'whsec_test_secret',
            'ENABLED': True,
        },
    )
    def test_verify_webhook_signature_accepts_valid_signature(self):
        import hashlib
        import hmac
        import time

        from integrations.stripe.client import verify_webhook_signature

        secret = 'whsec_test_secret'
        payload = b'{"id":"evt_test"}'
        timestamp = str(int(time.time()))
        signed_payload = f'{timestamp}.{payload.decode()}'
        signature = hmac.new(
            secret.encode('utf-8'),
            signed_payload.encode('utf-8'),
            hashlib.sha256,
        ).hexdigest()
        header = f't={timestamp},v1={signature}'
        self.assertTrue(verify_webhook_signature(payload, header))

    @override_settings(
        STRIPE={
            'SECRET_KEY': 'sk_test',
            'PUBLISHABLE_KEY': 'pk_test',
            'WEBHOOK_SECRET': 'whsec_test_secret',
            'ENABLED': True,
        },
    )
    def test_verify_webhook_signature_rejects_tampered_payload(self):
        import hashlib
        import hmac
        import time

        from integrations.stripe.client import verify_webhook_signature

        secret = 'whsec_test_secret'
        payload = b'{"id":"evt_test"}'
        timestamp = str(int(time.time()))
        signed_payload = f'{timestamp}.{payload.decode()}'
        signature = hmac.new(
            secret.encode('utf-8'),
            signed_payload.encode('utf-8'),
            hashlib.sha256,
        ).hexdigest()
        header = f't={timestamp},v1={signature}'
        self.assertFalse(verify_webhook_signature(b'{"id":"evt_bad"}', header))


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


class BookingApiTests(TestCase):
    def setUp(self):
        Group.objects.create(name='student')
        Group.objects.create(name='teacher')
        self.teacher = User.objects.create_user('t1', password='pass')
        self.teacher.groups.add(Group.objects.get(name='teacher'))
        self.student = User.objects.create_user('s1', password='pass')
        self.student.groups.add(Group.objects.get(name='student'))
        plan = MembershipPlan.objects.create(name='All access', price_cents=1000, ticket_allowance=10)
        Membership.objects.create(
            user=self.student,
            plan=plan,
            is_active=True,
            tickets_remaining=10,
        )
        self.session = Session.objects.create(
            teacher=self.teacher,
            title='Open lesson',
            start_time=timezone.now() + timedelta(days=2),
            end_time=timezone.now() + timedelta(days=2, hours=1),
            capacity=4,
            status='open',
        )
        res = self.client.post(
            '/api/auth/token/',
            {'username': 's1', 'password': 'pass'},
            content_type='application/json',
        )
        self.auth = f'Bearer {res.json()["access"]}'

    def test_open_sessions_include_student_booked_flag(self):
        create_booking(self.student, self.session)
        res = self.client.get('/api/sessions/open/', HTTP_AUTHORIZATION=self.auth)
        self.assertEqual(res.status_code, 200)
        row = next(item for item in res.json() if item['id'] == self.session.id)
        self.assertTrue(row['student_booked'])

    def test_duplicate_booking_returns_clear_error(self):
        create_booking(self.student, self.session)
        res = self.client.post(
            '/api/bookings/create/',
            {'session_id': self.session.id},
            content_type='application/json',
            HTTP_AUTHORIZATION=self.auth,
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn('already have a booking', res.json()['detail'].lower())

    def test_booking_create_includes_confirmation_email_fields(self):
        self.student.email = 'student@example.com'
        self.student.save(update_fields=['email'])
        res = self.client.post(
            '/api/bookings/create/',
            {'session_id': self.session.id},
            content_type='application/json',
            HTTP_AUTHORIZATION=self.auth,
        )
        self.assertEqual(res.status_code, 201)
        body = res.json()
        self.assertTrue(body['confirmation_email_sent'])
        self.assertEqual(body['confirmation_email'], 'student@example.com')


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
        self.student.email = 'student@example.com'
        self.student.save(update_fields=['email'])
        self.teacher.email = 'teacher@example.com'
        self.teacher.save(update_fields=['email'])
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
        body = res.json()
        self.assertNotIn('confirmation_email_sent', body)
        self.assertTrue(body['teacher_email_sent'])
        self.assertEqual(body['notification_email'], 'student@example.com')
        self.membership.refresh_from_db()
        self.assertEqual(self.membership.tickets_remaining, 3)

    def test_availability_includes_slots(self):
        token = self._token(self.student)
        res = self.client.get(
            f'/api/class-requests/availability/?teacher={self.teacher.id}&include_slots=true',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn('slots', res.json())
        self.assertTrue(len(res.json()['slots']) >= 1)

    def test_open_class_request_any_teacher(self):
        from scheduling.services.class_requests import create_open_class_request, pending_requests_for_teacher

        request, error = create_open_class_request(
            self.student,
            subject='Piano',
            level='Beginner',
            focus='Technique',
            start_time=self.start,
            end_time=self.end,
            tickets_requested=2,
        )
        self.assertIsNone(error)
        self.assertTrue(request.open_to_any_teacher)
        self.assertIsNone(request.teacher_id)
        self.assertEqual(pending_requests_for_teacher(self.teacher).count(), 1)

        approved, error = approve_class_request(self.teacher, request)
        self.assertIsNone(error)
        self.assertEqual(approved.teacher_id, self.teacher.id)
        self.assertEqual(approved.class_offering_id, self.offering.id)

    def test_open_class_request_via_api(self):
        token = self._token(self.student)
        res = self.client.post(
            '/api/class-requests/',
            {
                'open_to_any_teacher': True,
                'subject': 'Piano',
                'level': 'Beginner',
                'focus': 'Technique',
                'start_time': self.start.isoformat(),
                'end_time': self.end.isoformat(),
                'tickets_requested': 2,
            },
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(res.status_code, 201)
        self.assertTrue(res.json()['open_to_any_teacher'])
        self.assertIsNone(res.json()['teacher'])


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

    def test_create_session_with_add_special_availability(self):
        from datetime import time

        from scheduling.models import AvailabilityBlock, ClassOffering, SpecialAvailability

        day = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=5)
        AvailabilityBlock.objects.create(
            teacher=self.teacher,
            weekday=day.weekday(),
            start_time=time(10, 0),
            end_time=time(12, 0),
        )
        offering = ClassOffering.objects.create(
            teacher=self.teacher,
            subject='Japanese',
            level='Beginner',
            focus='Speaking',
            default_capacity=4,
        )
        session_start = day.replace(hour=14)
        session_end = session_start + timedelta(hours=1)
        token = self._token(self.teacher)
        body = {
            'class_offering': offering.id,
            'start_time': session_start.isoformat(),
            'end_time': session_end.isoformat(),
        }
        denied = self.client.post(
            '/api/teacher/sessions/',
            body,
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(denied.status_code, 400)
        self.assertEqual(denied.json()['code'], 'outside_availability')
        self.assertFalse(SpecialAvailability.objects.filter(teacher=self.teacher, date=day.date()).exists())

        created = self.client.post(
            '/api/teacher/sessions/',
            {
                **body,
                'add_special_availability': True,
                'special_availability_note': 'Makeup lesson',
            },
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(created.status_code, 201)
        special = SpecialAvailability.objects.get(teacher=self.teacher, date=day.date())
        self.assertEqual(special.start_time, session_start.time())
        self.assertEqual(special.end_time, session_end.time())
        self.assertEqual(special.note, 'Makeup lesson')


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

    @override_settings(
        GOOGLE={'CLIENT_ID': '', 'CLIENT_SECRET': '', 'ENABLED': False, 'REDIRECT_URI': ''},
    )
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
            '/api/integrations/google/connect/?frontend_origin=http%3A%2F%2F127.0.0.1%3A5173',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(res.status_code, 200)
        url = res.json()['authorization_url']
        self.assertIn('accounts.google.com', url)
        self.assertIn('test-client', url)
        self.assertIn('state=', url)

    @override_settings(
        GOOGLE={
            'CLIENT_ID': 'test-client',
            'CLIENT_SECRET': 'test-secret',
            'ENABLED': True,
            'REDIRECT_URI': 'http://127.0.0.1:8000/integrations/google/callback/',
        },
    )
    def test_oauth_state_round_trips_frontend_origin_with_colons(self):
        from integrations.google.oauth import make_state, parse_oauth_state

        state = make_state(self.teacher, 'http://127.0.0.1:5173')
        user_id, origin = parse_oauth_state(state)
        self.assertEqual(user_id, self.teacher.id)
        self.assertEqual(origin, 'http://127.0.0.1:5173')

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


class GoogleCalendarSyncTests(TestCase):
    """Calendar event sync on session create / update / cancel."""

    GOOGLE_SETTINGS = {
        'CLIENT_ID': 'test-client',
        'CLIENT_SECRET': 'test-secret',
        'ENABLED': True,
        'REDIRECT_URI': 'http://127.0.0.1:8000/integrations/google/callback/',
    }

    def setUp(self):
        Group.objects.create(name='teacher')
        self.teacher = User.objects.create_user('cal_teacher', password='pass')
        self.teacher.groups.add(Group.objects.get(name='teacher'))

    def _connect_teacher(self):
        from scheduling.models import GoogleCredential

        GoogleCredential.objects.create(
            user=self.teacher,
            access_token='ya29.test',
            refresh_token='1//refresh',
            token_expires_at=timezone.now() + timedelta(hours=1),
        )

    def _session(self, **extra):
        start = timezone.now() + timedelta(days=1)
        return Session.objects.create(
            teacher=self.teacher,
            title='Calendar session',
            start_time=start,
            end_time=start + timedelta(hours=1),
            capacity=2,
            status='open',
            meeting_provider='google_meet',
            **extra,
        )

    @override_settings(GOOGLE=GOOGLE_SETTINGS)
    def test_attach_meeting_link_stores_event_id(self):
        from unittest.mock import patch

        from scheduling.services.meetings import attach_meeting_link

        self._connect_teacher()
        session = self._session()
        with patch(
            'integrations.google.meet._insert_calendar_event',
            return_value={
                'id': 'evt_123',
                'hangoutLink': 'https://meet.google.com/abc-defg-hij',
            },
        ):
            attach_meeting_link(session)
        session.refresh_from_db()
        self.assertEqual(session.meeting_url, 'https://meet.google.com/abc-defg-hij')
        self.assertEqual(session.google_calendar_event_id, 'evt_123')

    def test_attach_meeting_link_placeholder_has_no_event_id(self):
        from scheduling.services.meetings import attach_meeting_link

        session = self._session()
        attach_meeting_link(session)
        session.refresh_from_db()
        self.assertTrue(session.meeting_url.startswith('https://meet.google.com/lookup/'))
        self.assertEqual(session.google_calendar_event_id, '')

    @override_settings(GOOGLE=GOOGLE_SETTINGS)
    def test_cancel_session_deletes_calendar_event(self):
        from unittest.mock import patch

        from scheduling.services.sessions import cancel_session

        self._connect_teacher()
        session = self._session(google_calendar_event_id='evt_123')
        with patch('integrations.google.meet._calendar_request', return_value={}) as mock_request:
            ok, error = cancel_session(session, self.teacher)
        self.assertTrue(ok)
        self.assertIsNone(error)
        mock_request.assert_called_once()
        self.assertEqual(mock_request.call_args.args[0], 'DELETE')
        self.assertEqual(mock_request.call_args.kwargs['event_id'], 'evt_123')
        session.refresh_from_db()
        self.assertEqual(session.status, 'cancelled')
        self.assertEqual(session.google_calendar_event_id, '')

    @override_settings(GOOGLE=GOOGLE_SETTINGS)
    def test_update_session_patches_calendar_event(self):
        from unittest.mock import patch

        from scheduling.services.sessions import update_session

        self._connect_teacher()
        session = self._session(google_calendar_event_id='evt_123')
        new_start = timezone.now() + timedelta(days=2)
        with patch('integrations.google.meet._calendar_request', return_value={}) as mock_request:
            ok, error = update_session(
                session,
                self.teacher,
                start_time=new_start,
                end_time=new_start + timedelta(hours=1),
            )
        self.assertTrue(ok)
        self.assertIsNone(error)
        mock_request.assert_called_once()
        self.assertEqual(mock_request.call_args.args[0], 'PATCH')
        self.assertEqual(mock_request.call_args.kwargs['event_id'], 'evt_123')
        body = mock_request.call_args.kwargs['body']
        self.assertEqual(body['start']['dateTime'], new_start.isoformat())

    def test_cancel_session_without_event_id_makes_no_api_call(self):
        from unittest.mock import patch

        from scheduling.services.sessions import cancel_session

        session = self._session()
        with patch('integrations.google.meet._calendar_request') as mock_request:
            ok, _ = cancel_session(session, self.teacher)
        self.assertTrue(ok)
        mock_request.assert_not_called()

    @override_settings(GOOGLE=GOOGLE_SETTINGS)
    def test_cancel_session_survives_google_api_failure(self):
        import urllib.error
        from unittest.mock import patch

        from scheduling.services.sessions import cancel_session

        self._connect_teacher()
        session = self._session(google_calendar_event_id='evt_123')
        with patch(
            'integrations.google.meet._calendar_request',
            side_effect=urllib.error.URLError('network down'),
        ):
            ok, error = cancel_session(session, self.teacher)
        self.assertTrue(ok)
        self.assertIsNone(error)
        session.refresh_from_db()
        self.assertEqual(session.status, 'cancelled')
        # Event id kept so a later retry/manual cleanup is possible.
        self.assertEqual(session.google_calendar_event_id, 'evt_123')


class SchedulingSlotTests(TestCase):
    def setUp(self):
        Group.objects.create(name='teacher')
        self.teacher = User.objects.create_user('slot_teacher', password='pass')
        self.teacher.groups.add(Group.objects.get(name='teacher'))
        self.slot_start = timezone.now().replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=3)
        self.slot_end = self.slot_start + timedelta(hours=2)
        AvailabilityBlock.objects.create(
            teacher=self.teacher,
            weekday=self.slot_start.weekday(),
            start_time=self.slot_start.time(),
            end_time=self.slot_end.time(),
        )

    def test_scheduling_slots_within_availability_window(self):
        from scheduling.services.scheduling_slots import scheduling_slot_options

        slots = scheduling_slot_options(self.teacher, duration_minutes=60, step_minutes=60)
        matching = [slot for slot in slots if slot['start'].startswith(self.slot_start.date().isoformat())]
        self.assertGreaterEqual(len(matching), 2)

    def test_scheduling_slots_api(self):
        token = self.client.post(
            '/api/auth/token/',
            {'username': 'slot_teacher', 'password': 'pass'},
            content_type='application/json',
        ).json()['access']
        res = self.client.get(
            '/api/teacher/scheduling-slots/?duration_minutes=60',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn('slots', res.json())


class StudentRegistrationTests(TestCase):
    def setUp(self):
        Group.objects.create(name='student')

    def test_register_creates_student_and_returns_tokens(self):
        res = self.client.post(
            '/api/auth/register/',
            {
                'username': 'new_student',
                'email': 'new@example.com',
                'password': 'validpass123',
                'display_name': 'New Student',
            },
            content_type='application/json',
        )
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertIn('access', data)
        self.assertIn('refresh', data)
        self.assertEqual(data['user']['username'], 'new_student')
        self.assertEqual(data['user']['roles'], ['student'])

        user = User.objects.get(username='new_student')
        self.assertTrue(user.check_password('validpass123'))
        self.assertTrue(user.groups.filter(name='student').exists())

    def test_register_rejects_duplicate_username(self):
        User.objects.create_user('taken', email='a@example.com', password='pass')
        res = self.client.post(
            '/api/auth/register/',
            {
                'username': 'taken',
                'email': 'b@example.com',
                'password': 'validpass123',
            },
            content_type='application/json',
        )
        self.assertEqual(res.status_code, 400)


class ClassCatalogTests(TestCase):
    def setUp(self):
        Group.objects.create(name='staff')
        Group.objects.create(name='teacher')
        self.staff = User.objects.create_user('staff_catalog', password='pass')
        self.staff.groups.add(Group.objects.get(name='staff'))
        self.teacher = User.objects.create_user('teacher_catalog', password='pass')
        self.teacher.groups.add(Group.objects.get(name='teacher'))

    def _token(self, user):
        return self.client.post(
            '/api/auth/token/',
            {'username': user.username, 'password': 'pass'},
            content_type='application/json',
        ).json()['access']

    def test_bulk_add_topics_and_read_catalog(self):
        from scheduling.services.class_catalog import create_catalog_focus, create_catalog_level, create_catalog_subject

        subject, _ = create_catalog_subject('Japanese')
        level, _ = create_catalog_level(subject.id, 'Beginner')
        focus, _ = create_catalog_focus(level.id, 'Grammar')

        staff_auth = {'HTTP_AUTHORIZATION': f'Bearer {self._token(self.staff)}'}
        res = self.client.post(
            f'/api/staff/class-catalog/focuses/{focus.id}/topics/bulk/',
            {'topics': 'Verbs\nParticles\nAdjectives'},
            content_type='application/json',
            **staff_auth,
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(len(res.json()['topics']), 3)

        teacher_auth = {'HTTP_AUTHORIZATION': f'Bearer {self._token(self.teacher)}'}
        tree = self.client.get('/api/class-catalog/', **teacher_auth).json()
        self.assertEqual(tree['subjects'][0]['name'], 'Japanese')
        topics = tree['subjects'][0]['levels'][0]['focuses'][0]['topics']
        self.assertEqual([topic['title'] for topic in topics], ['Verbs', 'Particles', 'Adjectives'])


class LLMUrlValidationTests(TestCase):
    def test_rejects_private_openai_compatible_url(self):
        from integrations.llm.errors import LLMError
        from integrations.llm.url_validation import validate_llm_url

        with self.assertRaises(LLMError):
            validate_llm_url('http://127.0.0.1:8080/v1', provider='openai_compatible')

    def test_allows_ollama_localhost(self):
        from integrations.llm.url_validation import validate_llm_url

        validate_llm_url('http://127.0.0.1:11434', provider='ollama')


class StudentHomeTests(TestCase):
    def setUp(self):
        Group.objects.create(name='student')
        Group.objects.create(name='teacher')
        self.teacher = User.objects.create_user('t1', password='pass')
        self.teacher.groups.add(Group.objects.get(name='teacher'))
        self.student = User.objects.create_user('s1', password='pass')
        self.student.groups.add(Group.objects.get(name='student'))
        self.plan = MembershipPlan.objects.create(name='Japanese', price_cents=2000, ticket_allowance=8)
        Membership.objects.create(
            user=self.student,
            plan=self.plan,
            is_active=True,
            tickets_remaining=2,
            valid_until=timezone.now().date() + timedelta(days=30),
        )
        self.session = Session.objects.create(
            teacher=self.teacher,
            title='Next lesson',
            start_time=timezone.now() + timedelta(days=3),
            end_time=timezone.now() + timedelta(days=3, hours=1),
            capacity=2,
            status='open',
        )
        Booking.objects.create(student=self.student, session=self.session, status='confirmed')

    def _token(self):
        res = self.client.post(
            '/api/auth/token/',
            {'username': 's1', 'password': 'pass'},
            content_type='application/json',
        )
        return res.json()['access']

    def test_student_home_returns_next_lesson_and_low_ticket_warning(self):
        res = self.client.get(
            '/api/student/home/',
            HTTP_AUTHORIZATION=f'Bearer {self._token()}',
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data['has_membership'])
        self.assertTrue(data['low_ticket_warning'])
        self.assertEqual(data['tickets_remaining'], 2)
        self.assertIsNotNone(data['next_lesson'])
        self.assertEqual(data['next_lesson']['session_title'], 'Next lesson')


class ShowcaseSeedTests(TestCase):
    def test_showcase_grants_demo_student_membership_and_booking(self):
        from django.core.management import call_command

        call_command('bootstrap_sandbox', '--demo', '--showcase')
        student = User.objects.get(username='demo_student')
        self.assertTrue(
            Membership.objects.filter(user=student, is_active=True, tickets_remaining__gt=0).exists()
        )
        self.assertTrue(
            Booking.objects.filter(
                student=student,
                status='confirmed',
                session__start_time__gte=timezone.now(),
            ).exists()
        )

    def test_demo_staff_has_no_django_admin_access_by_default(self):
        from django.core.management import call_command

        call_command('bootstrap_sandbox', '--demo')
        staff = User.objects.get(username='demo_staff')
        self.assertFalse(staff.is_superuser)
        self.assertFalse(staff.is_staff)
        self.assertTrue(staff.groups.filter(name='staff').exists())

    def test_staff_superuser_flag_grants_admin_access(self):
        from django.core.management import call_command

        call_command('bootstrap_sandbox', '--demo', '--staff-superuser')
        staff = User.objects.get(username='demo_staff')
        self.assertTrue(staff.is_superuser)
        self.assertTrue(staff.is_staff)


class StaffSandboxAuditTests(TestCase):
    """Staff can run the studio from the app: manage the roadmap and add teachers."""

    def setUp(self):
        Group.objects.create(name='staff')
        Group.objects.create(name='teacher')
        Group.objects.create(name='student')
        self.staff = User.objects.create_user('staff_sandbox', password='pass')
        self.staff.groups.add(Group.objects.get(name='staff'))
        self.teacher = User.objects.create_user('teacher_sandbox', password='pass')
        self.teacher.groups.add(Group.objects.get(name='teacher'))

    def _auth(self, user):
        token = self.client.post(
            '/api/auth/token/',
            {'username': user.username, 'password': 'pass'},
            content_type='application/json',
        ).json()['access']
        return {'HTTP_AUTHORIZATION': f'Bearer {token}'}

    def _seed_roadmap(self):
        from scheduling.services.class_catalog import (
            bulk_add_catalog_topics,
            create_catalog_focus,
            create_catalog_level,
            create_catalog_subject,
        )

        subject, _ = create_catalog_subject('Japanese')
        level, _ = create_catalog_level(subject.id, 'Beginner')
        focus, _ = create_catalog_focus(level.id, 'Grammar')
        bulk_add_catalog_topics(focus.id, 'Verbs')
        return subject, level, focus, focus.topics.first()

    def test_staff_deletes_unused_roadmap_entry(self):
        subject, level, focus, _ = self._seed_roadmap()
        res = self.client.delete(
            f'/api/staff/class-catalog/focus/{focus.id}/',
            **self._auth(self.staff),
        )
        self.assertEqual(res.status_code, 200)
        self.assertFalse(level.focuses.filter(pk=focus.id).exists())

    def test_delete_blocked_while_a_class_uses_the_entry(self):
        subject, level, focus, _ = self._seed_roadmap()
        ClassOffering.objects.create(
            teacher=self.teacher,
            subject='Japanese',
            level='Beginner',
            focus='Grammar',
        )
        res = self.client.delete(
            f'/api/staff/class-catalog/subject/{subject.id}/',
            **self._auth(self.staff),
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn('Deactivate it instead', res.json()['detail'])

    def test_deactivate_hides_entry_from_teacher_pickers(self):
        subject, _, _, _ = self._seed_roadmap()
        res = self.client.patch(
            f'/api/staff/class-catalog/subject/{subject.id}/',
            {'is_active': False},
            content_type='application/json',
            **self._auth(self.staff),
        )
        self.assertEqual(res.status_code, 200)
        tree = self.client.get('/api/class-catalog/', **self._auth(self.teacher)).json()
        self.assertEqual(tree['subjects'], [])

    def test_rename_keeps_existing_classes_in_sync(self):
        _, level, _, _ = self._seed_roadmap()
        offering = ClassOffering.objects.create(
            teacher=self.teacher,
            subject='Japanese',
            level='Beginner',
            focus='Grammar',
        )
        res = self.client.patch(
            f'/api/staff/class-catalog/level/{level.id}/',
            {'name': 'Foundations'},
            content_type='application/json',
            **self._auth(self.staff),
        )
        self.assertEqual(res.status_code, 200)
        offering.refresh_from_db()
        self.assertEqual(offering.level, 'Foundations')

    def test_rename_rejects_duplicate_sibling(self):
        subject, level, _, _ = self._seed_roadmap()
        from scheduling.services.class_catalog import create_catalog_level

        create_catalog_level(subject.id, 'Advanced')
        res = self.client.patch(
            f'/api/staff/class-catalog/level/{level.id}/',
            {'name': 'Advanced'},
            content_type='application/json',
            **self._auth(self.staff),
        )
        self.assertEqual(res.status_code, 400)

    def test_roadmap_edits_require_staff(self):
        subject, _, _, _ = self._seed_roadmap()
        res = self.client.delete(
            f'/api/staff/class-catalog/subject/{subject.id}/',
            **self._auth(self.teacher),
        )
        self.assertEqual(res.status_code, 403)

    def test_staff_creates_teacher_with_all_permissions(self):
        res = self.client.post(
            '/api/staff/teachers/',
            {
                'username': 'new_teacher',
                'email': 'new@example.com',
                'display_name': 'Aiko',
                'password': 'studio-pass-9182',
            },
            content_type='application/json',
            **self._auth(self.staff),
        )
        self.assertEqual(res.status_code, 201)
        created = User.objects.get(username='new_teacher')
        self.assertTrue(created.groups.filter(name='teacher').exists())
        self.assertFalse(created.is_staff)

        from scheduling.services.teacher_permissions import teacher_can

        self.assertTrue(teacher_can(created, 'manage_schedule'))
        self.assertTrue(teacher_can(created, 'write_reports'))

        listed = self.client.get('/api/staff/teachers/', **self._auth(self.staff)).json()
        self.assertIn('new_teacher', [row['username'] for row in listed])

    def test_create_teacher_rejects_weak_password_and_duplicate_username(self):
        weak = self.client.post(
            '/api/staff/teachers/',
            {'username': 'another_teacher', 'password': '123'},
            content_type='application/json',
            **self._auth(self.staff),
        )
        self.assertEqual(weak.status_code, 400)
        self.assertFalse(User.objects.filter(username='another_teacher').exists())

        duplicate = self.client.post(
            '/api/staff/teachers/',
            {'username': 'teacher_sandbox', 'password': 'studio-pass-9182'},
            content_type='application/json',
            **self._auth(self.staff),
        )
        self.assertEqual(duplicate.status_code, 400)

    def test_create_teacher_requires_staff(self):
        res = self.client.post(
            '/api/staff/teachers/',
            {'username': 'sneaky', 'password': 'studio-pass-9182'},
            content_type='application/json',
            **self._auth(self.teacher),
        )
        self.assertEqual(res.status_code, 403)
        self.assertFalse(User.objects.filter(username='sneaky').exists())


class StaffUserAdminTests(TestCase):
    """Staff creates students and resets passwords without Django admin."""

    def setUp(self):
        Group.objects.create(name='staff')
        Group.objects.create(name='teacher')
        Group.objects.create(name='student')
        self.staff = User.objects.create_user('staff_users', password='pass')
        self.staff.groups.add(Group.objects.get(name='staff'))
        self.teacher = User.objects.create_user('teacher_users', password='pass')
        self.teacher.groups.add(Group.objects.get(name='teacher'))
        self.student = User.objects.create_user('student_users', password='pass')
        self.student.groups.add(Group.objects.get(name='student'))

    def _auth(self, user):
        token = self.client.post(
            '/api/auth/token/',
            {'username': user.username, 'password': 'pass'},
            content_type='application/json',
        ).json()['access']
        return {'HTTP_AUTHORIZATION': f'Bearer {token}'}

    def test_staff_creates_student(self):
        res = self.client.post(
            '/api/staff/students/',
            {
                'username': 'walk_in',
                'email': 'walkin@example.com',
                'display_name': 'Walk In',
                'password': 'studio-pass-9182',
            },
            content_type='application/json',
            **self._auth(self.staff),
        )
        self.assertEqual(res.status_code, 201)
        created = User.objects.get(username='walk_in')
        self.assertTrue(created.groups.filter(name='student').exists())
        self.assertTrue(
            StaffActionLog.objects.filter(
                action=StaffActionLog.ACTION_USER_CREATED,
                target_user=created,
                actor=self.staff,
            ).exists()
        )

    def test_create_student_requires_staff(self):
        res = self.client.post(
            '/api/staff/students/',
            {'username': 'nope', 'password': 'studio-pass-9182'},
            content_type='application/json',
            **self._auth(self.teacher),
        )
        self.assertEqual(res.status_code, 403)
        self.assertFalse(User.objects.filter(username='nope').exists())

    def test_staff_resets_student_password(self):
        res = self.client.post(
            f'/api/staff/students/{self.student.id}/password/',
            {'password': 'studio-pass-9182', 'note': 'forgot at front desk'},
            content_type='application/json',
            **self._auth(self.staff),
        )
        self.assertEqual(res.status_code, 200)

        token_res = self.client.post(
            '/api/auth/token/',
            {'username': 'student_users', 'password': 'studio-pass-9182'},
            content_type='application/json',
        )
        self.assertEqual(token_res.status_code, 200)
        entry = StaffActionLog.objects.get(action=StaffActionLog.ACTION_PASSWORD_RESET)
        self.assertEqual(entry.target_user, self.student)
        self.assertEqual(entry.note, 'forgot at front desk')

    def test_staff_resets_teacher_password(self):
        res = self.client.post(
            f'/api/staff/teachers/{self.teacher.id}/password/',
            {'password': 'studio-pass-9182'},
            content_type='application/json',
            **self._auth(self.staff),
        )
        self.assertEqual(res.status_code, 200)
        self.teacher.refresh_from_db()
        self.assertTrue(self.teacher.check_password('studio-pass-9182'))

    def test_password_reset_rejects_weak_password(self):
        res = self.client.post(
            f'/api/staff/students/{self.student.id}/password/',
            {'password': '123'},
            content_type='application/json',
            **self._auth(self.staff),
        )
        self.assertEqual(res.status_code, 400)
        self.student.refresh_from_db()
        self.assertTrue(self.student.check_password('pass'))

    def test_staff_cannot_reset_another_staff_password(self):
        other = User.objects.create_user('staff_two', password='pass')
        other.groups.add(Group.objects.get(name='staff'))
        # Staff accounts are not teachers or students, so the lookup 404s before the guard.
        res = self.client.post(
            f'/api/staff/students/{other.id}/password/',
            {'password': 'studio-pass-9182'},
            content_type='application/json',
            **self._auth(self.staff),
        )
        self.assertEqual(res.status_code, 404)
        other.refresh_from_db()
        self.assertTrue(other.check_password('pass'))

    def test_password_reset_requires_staff(self):
        res = self.client.post(
            f'/api/staff/students/{self.student.id}/password/',
            {'password': 'studio-pass-9182'},
            content_type='application/json',
            **self._auth(self.teacher),
        )
        self.assertEqual(res.status_code, 403)


class StaffMembershipAdminTests(TestCase):
    """Staff can comp a plan, fix a ticket balance, extend, and cancel."""

    def setUp(self):
        Group.objects.create(name='staff')
        Group.objects.create(name='student')
        self.staff = User.objects.create_user('staff_money', password='pass')
        self.staff.groups.add(Group.objects.get(name='staff'))
        self.student = User.objects.create_user('student_money', password='pass')
        self.student.groups.add(Group.objects.get(name='student'))
        self.plan = MembershipPlan.objects.create(
            name='Japanese',
            price_cents=5000,
            ticket_allowance=8,
            billing_period_days=30,
        )

    def _auth(self, user):
        token = self.client.post(
            '/api/auth/token/',
            {'username': user.username, 'password': 'pass'},
            content_type='application/json',
        ).json()['access']
        return {'HTTP_AUTHORIZATION': f'Bearer {token}'}

    def _grant(self, **overrides):
        payload = {'plan_id': self.plan.id, 'months': 1}
        payload.update(overrides)
        return self.client.post(
            f'/api/staff/students/{self.student.id}/membership/',
            payload,
            content_type='application/json',
            **self._auth(self.staff),
        )

    def test_overview_is_empty_before_any_membership(self):
        res = self.client.get(
            f'/api/staff/students/{self.student.id}/membership/',
            **self._auth(self.staff),
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data['has_active_membership'])
        self.assertEqual(data['tickets_remaining'], 0)
        self.assertEqual(data['memberships'], [])
        self.assertIn('plans', data)

    def test_staff_comps_a_membership(self):
        res = self._grant(note='comped for referral')
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertTrue(data['has_active_membership'])
        self.assertEqual(data['tickets_remaining'], 8)

        payment = Payment.objects.get(user=self.student)
        self.assertEqual(payment.provider, Payment.PROVIDER_STAFF)
        self.assertEqual(payment.amount_cents, 0)
        entry = StaffActionLog.objects.get(action=StaffActionLog.ACTION_MEMBERSHIP_GRANTED)
        self.assertEqual(entry.note, 'comped for referral')
        self.assertEqual(entry.detail['months'], 1)

    def test_staff_records_a_cash_sale(self):
        res = self._grant(months=2, amount_cents=10000)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()['tickets_remaining'], 16)
        payment = Payment.objects.get(user=self.student)
        self.assertEqual(payment.amount_cents, 10000)
        self.assertEqual(payment.quantity, 2)

    def test_grant_rejects_inactive_plan(self):
        self.plan.is_active = False
        self.plan.save(update_fields=['is_active'])
        res = self._grant()
        self.assertEqual(res.status_code, 400)
        self.assertFalse(Membership.objects.filter(user=self.student).exists())

    def test_staff_adjusts_tickets_up_and_down(self):
        self._grant()
        membership = Membership.objects.get(user=self.student)

        add = self.client.patch(
            f'/api/staff/students/{self.student.id}/membership/{membership.id}/',
            {'tickets_delta': 3, 'note': 'make-up lesson'},
            content_type='application/json',
            **self._auth(self.staff),
        )
        self.assertEqual(add.status_code, 200)
        self.assertEqual(add.json()['tickets_remaining'], 11)

        remove = self.client.patch(
            f'/api/staff/students/{self.student.id}/membership/{membership.id}/',
            {'tickets_delta': -5},
            content_type='application/json',
            **self._auth(self.staff),
        )
        self.assertEqual(remove.status_code, 200)
        self.assertEqual(remove.json()['tickets_remaining'], 6)

        entries = StaffActionLog.objects.filter(action=StaffActionLog.ACTION_TICKETS_ADJUSTED)
        self.assertEqual(entries.count(), 2)

    def test_ticket_adjustment_cannot_go_negative(self):
        self._grant()
        membership = Membership.objects.get(user=self.student)
        res = self.client.patch(
            f'/api/staff/students/{self.student.id}/membership/{membership.id}/',
            {'tickets_delta': -99},
            content_type='application/json',
            **self._auth(self.staff),
        )
        self.assertEqual(res.status_code, 400)
        membership.refresh_from_db()
        self.assertEqual(membership.tickets_remaining, 8)

    def test_staff_cancels_and_reactivates_membership(self):
        self._grant()
        membership = Membership.objects.get(user=self.student)
        url = f'/api/staff/students/{self.student.id}/membership/{membership.id}/'

        cancel = self.client.patch(
            url,
            {'is_active': False, 'note': 'moved away'},
            content_type='application/json',
            **self._auth(self.staff),
        )
        self.assertEqual(cancel.status_code, 200)
        self.assertFalse(cancel.json()['has_active_membership'])

        restore = self.client.patch(
            url,
            {'is_active': True},
            content_type='application/json',
            **self._auth(self.staff),
        )
        self.assertEqual(restore.status_code, 200)
        self.assertTrue(restore.json()['has_active_membership'])

    def test_staff_extends_expiry(self):
        self._grant()
        membership = Membership.objects.get(user=self.student)
        before = membership.valid_until
        res = self.client.patch(
            f'/api/staff/students/{self.student.id}/membership/{membership.id}/',
            {'extend_days': 14},
            content_type='application/json',
            **self._auth(self.staff),
        )
        self.assertEqual(res.status_code, 200)
        membership.refresh_from_db()
        self.assertEqual(membership.valid_until, before + timedelta(days=14))

    def test_membership_update_needs_an_action(self):
        self._grant()
        membership = Membership.objects.get(user=self.student)
        res = self.client.patch(
            f'/api/staff/students/{self.student.id}/membership/{membership.id}/',
            {'note': 'nothing to do'},
            content_type='application/json',
            **self._auth(self.staff),
        )
        self.assertEqual(res.status_code, 400)

    def test_membership_admin_requires_staff(self):
        res = self.client.get(
            f'/api/staff/students/{self.student.id}/membership/',
            **self._auth(self.student),
        )
        self.assertEqual(res.status_code, 403)

    def test_membership_of_another_student_is_not_reachable(self):
        other = User.objects.create_user('other_student', password='pass')
        other.groups.add(Group.objects.get(name='student'))
        self._grant()
        membership = Membership.objects.get(user=self.student)
        res = self.client.patch(
            f'/api/staff/students/{other.id}/membership/{membership.id}/',
            {'tickets_delta': 5},
            content_type='application/json',
            **self._auth(self.staff),
        )
        self.assertEqual(res.status_code, 400)


class StaffBookingOverrideTests(TestCase):
    """Staff cancels a student's booking, choosing whether the ticket comes back."""

    def setUp(self):
        Group.objects.create(name='staff')
        Group.objects.create(name='teacher')
        Group.objects.create(name='student')
        self.staff = User.objects.create_user('staff_booking', password='pass')
        self.staff.groups.add(Group.objects.get(name='staff'))
        self.teacher = User.objects.create_user('teacher_booking', password='pass')
        self.teacher.groups.add(Group.objects.get(name='teacher'))
        self.student = User.objects.create_user('student_booking', password='pass')
        self.student.groups.add(Group.objects.get(name='student'))
        self.plan = MembershipPlan.objects.create(name='All access', price_cents=1000, ticket_allowance=10)
        self.membership = Membership.objects.create(
            user=self.student,
            plan=self.plan,
            is_active=True,
            tickets_remaining=5,
        )
        self.session = Session.objects.create(
            teacher=self.teacher,
            title='Grammar drill',
            start_time=timezone.now() + timedelta(days=2),
            end_time=timezone.now() + timedelta(days=2, hours=1),
            capacity=4,
            status='open',
        )
        self.booking = Booking.objects.create(
            student=self.student,
            session=self.session,
            membership=self.membership,
            status='confirmed',
            tickets_spent=1,
        )

    def _auth(self, user):
        token = self.client.post(
            '/api/auth/token/',
            {'username': user.username, 'password': 'pass'},
            content_type='application/json',
        ).json()['access']
        return {'HTTP_AUTHORIZATION': f'Bearer {token}'}

    def test_staff_cancels_with_refund(self):
        res = self.client.post(
            f'/api/staff/bookings/{self.booking.id}/cancel/',
            {'refund': True, 'note': 'teacher sick'},
            content_type='application/json',
            **self._auth(self.staff),
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()['refunded'])
        self.booking.refresh_from_db()
        self.membership.refresh_from_db()
        self.assertEqual(self.booking.status, 'cancelled')
        self.assertEqual(self.membership.tickets_remaining, 6)
        entry = StaffActionLog.objects.get(action=StaffActionLog.ACTION_BOOKING_CANCELLED)
        self.assertEqual(entry.target_user, self.student)
        self.assertTrue(entry.detail['refunded'])

    def test_staff_cancels_without_refund(self):
        res = self.client.post(
            f'/api/staff/bookings/{self.booking.id}/cancel/',
            {'refund': False},
            content_type='application/json',
            **self._auth(self.staff),
        )
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.json()['refunded'])
        self.membership.refresh_from_db()
        self.assertEqual(self.membership.tickets_remaining, 5)

    def test_cancelling_twice_is_rejected(self):
        self.client.post(
            f'/api/staff/bookings/{self.booking.id}/cancel/',
            {'refund': True},
            content_type='application/json',
            **self._auth(self.staff),
        )
        again = self.client.post(
            f'/api/staff/bookings/{self.booking.id}/cancel/',
            {'refund': True},
            content_type='application/json',
            **self._auth(self.staff),
        )
        self.assertEqual(again.status_code, 400)
        self.membership.refresh_from_db()
        self.assertEqual(self.membership.tickets_remaining, 6)

    def test_missing_booking_returns_404(self):
        res = self.client.post(
            '/api/staff/bookings/9999/cancel/',
            {'refund': True},
            content_type='application/json',
            **self._auth(self.staff),
        )
        self.assertEqual(res.status_code, 404)

    def test_booking_cancel_requires_staff(self):
        res = self.client.post(
            f'/api/staff/bookings/{self.booking.id}/cancel/',
            {'refund': True},
            content_type='application/json',
            **self._auth(self.teacher),
        )
        self.assertEqual(res.status_code, 403)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, 'confirmed')

    def test_student_self_cancel_still_refunds(self):
        res = self.client.post(
            f'/api/bookings/{self.booking.id}/cancel/',
            content_type='application/json',
            **self._auth(self.student),
        )
        self.assertEqual(res.status_code, 200)
        self.membership.refresh_from_db()
        self.assertEqual(self.membership.tickets_remaining, 6)


class StaffPaymentSettingsTests(TestCase):
    def setUp(self):
        Group.objects.create(name='staff')
        Group.objects.create(name='student')
        self.staff = User.objects.create_user('staff_pay', password='pass')
        self.staff.groups.add(Group.objects.get(name='staff'))
        self.student = User.objects.create_user('student_pay', password='pass')
        self.student.groups.add(Group.objects.get(name='student'))

    def _auth(self, user):
        token = self.client.post(
            '/api/auth/token/',
            {'username': user.username, 'password': 'pass'},
            content_type='application/json',
        ).json()['access']
        return {'HTTP_AUTHORIZATION': f'Bearer {token}'}

    def test_mock_mode_reported_without_stripe(self):
        res = self.client.get('/api/staff/payments/', **self._auth(self.staff))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['mode'], 'mock')
        self.assertFalse(data['is_live'])
        self.assertFalse(data['stripe']['secret_key_configured'])
        self.assertIn('/api/payments/stripe/webhook/', data['stripe']['webhook_url'])

    @override_settings(
        STRIPE={
            'SECRET_KEY': 'sk_test_51ABCDEFghijklmnop',
            'PUBLISHABLE_KEY': 'pk_test_123',
            'WEBHOOK_SECRET': 'whsec_123',
            'ENABLED': True,
        },
    )
    def test_live_mode_masks_the_secret_key(self):
        res = self.client.get('/api/staff/payments/', **self._auth(self.staff))
        data = res.json()
        self.assertEqual(data['mode'], 'stripe')
        self.assertTrue(data['is_live'])
        self.assertTrue(data['stripe']['webhook_secret_configured'])
        self.assertNotIn('sk_test_51ABCDEFghijklmnop', res.content.decode())
        self.assertTrue(data['stripe']['secret_key_hint'].endswith('mnop'))

    def test_payment_settings_require_staff(self):
        res = self.client.get('/api/staff/payments/', **self._auth(self.student))
        self.assertEqual(res.status_code, 403)


class StaffActivityLogTests(TestCase):
    def setUp(self):
        Group.objects.create(name='staff')
        Group.objects.create(name='student')
        self.staff = User.objects.create_user('staff_log', password='pass')
        self.staff.groups.add(Group.objects.get(name='staff'))
        self.student = User.objects.create_user('student_log', password='pass')
        self.student.groups.add(Group.objects.get(name='student'))

    def _auth(self, user):
        token = self.client.post(
            '/api/auth/token/',
            {'username': user.username, 'password': 'pass'},
            content_type='application/json',
        ).json()['access']
        return {'HTTP_AUTHORIZATION': f'Bearer {token}'}

    def test_activity_log_lists_staff_overrides(self):
        self.client.post(
            f'/api/staff/students/{self.student.id}/password/',
            {'password': 'studio-pass-9182', 'note': 'front desk'},
            content_type='application/json',
            **self._auth(self.staff),
        )
        res = self.client.get('/api/staff/activity/', **self._auth(self.staff))
        self.assertEqual(res.status_code, 200)
        actions = res.json()['actions']
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['action'], StaffActionLog.ACTION_PASSWORD_RESET)
        self.assertEqual(actions[0]['actor'], 'staff_log')
        self.assertEqual(actions[0]['target_user'], 'student_log')
        self.assertEqual(actions[0]['note'], 'front desk')

    def test_activity_log_requires_staff(self):
        res = self.client.get('/api/staff/activity/', **self._auth(self.student))
        self.assertEqual(res.status_code, 403)
