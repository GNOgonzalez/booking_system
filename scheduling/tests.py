from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.utils import timezone

from scheduling.models import Booking, Membership, Session
from scheduling.services.booking import cancel_booking, create_booking
from scheduling.services.calendar import session_to_ics
from scheduling.services.payments import purchase_membership


class BookingServiceTests(TestCase):
    def setUp(self):
        Group.objects.create(name='student')
        Group.objects.create(name='teacher')
        self.teacher = User.objects.create_user('t1', password='pass')
        self.teacher.groups.add(Group.objects.get(name='teacher'))
        self.student = User.objects.create_user('s1', password='pass')
        self.student.groups.add(Group.objects.get(name='student'))
        Membership.objects.create(user=self.student, is_active=True)
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
        self.assertTrue(cancel_booking(self.student, booking))
        booking.refresh_from_db()
        self.session.refresh_from_db()
        self.assertEqual(booking.status, 'cancelled')
        self.assertEqual(self.session.status, 'cancelled')

    def test_booking_requires_membership(self):
        Membership.objects.filter(user=self.student).update(is_active=False)
        self.assertFalse(create_booking(self.student, self.session))

    def test_full_session_blocks_booking(self):
        self.session.capacity = 1
        self.session.save()
        other = User.objects.create_user('s2', password='pass')
        other.groups.add(Group.objects.get(name='student'))
        Membership.objects.create(user=other, is_active=True)
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

    def test_purchase_membership_activates(self):
        membership, error = purchase_membership(self.student, 'basic')
        self.assertIsNone(error)
        self.assertTrue(membership.is_active)
        self.assertIsNotNone(membership.valid_until)

    def test_purchase_unknown_plan(self):
        membership, error = purchase_membership(self.student, 'gold')
        self.assertIsNone(membership)
        self.assertIsNotNone(error)


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
