"""Homework media privacy — files must only be reachable through the authenticated API."""

import shutil
import tempfile
from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone

from progress.homework_services import create_homework_assignment
from scheduling.models import Booking, ClassOffering, ClassTopic, Session

TEMP_MEDIA = tempfile.mkdtemp(prefix='booking_test_media_')


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class HomeworkDownloadPrivacyTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def setUp(self):
        Group.objects.create(name='student')
        Group.objects.create(name='teacher')
        Group.objects.create(name='staff')
        self.teacher = User.objects.create_user('hw_teacher', password='pass')
        self.teacher.groups.add(Group.objects.get(name='teacher'))
        self.student = User.objects.create_user('hw_student', password='pass')
        self.student.groups.add(Group.objects.get(name='student'))
        self.other_student = User.objects.create_user('hw_other', password='pass')
        self.other_student.groups.add(Group.objects.get(name='student'))
        self.staff = User.objects.create_user('hw_staff', password='pass')
        self.staff.groups.add(Group.objects.get(name='staff'))

        start = timezone.now() - timedelta(days=1)
        self.session = Session.objects.create(
            teacher=self.teacher,
            title='Past lesson',
            start_time=start,
            end_time=start + timedelta(hours=1),
            capacity=1,
            status='open',
        )
        Booking.objects.create(session=self.session, student=self.student, status='confirmed')

        assignment, error = create_homework_assignment(
            teacher=self.teacher,
            student=self.student,
            session=self.session,
            kind='file',
            title='Worksheet',
            prompt='Do the worksheet.',
            initial_file=SimpleUploadedFile('sheet.pdf', b'%PDF-1.4 secret'),
        )
        self.assertIsNone(error)
        self.assignment = assignment
        self.entry = assignment.entries.first()
        self.download_path = f'/api/progress/homework/entries/{self.entry.id}/download/'

    def _token(self, user):
        res = self.client.post(
            '/api/auth/token/',
            {'username': user.username, 'password': 'pass'},
            content_type='application/json',
        )
        self.assertEqual(res.status_code, 200)
        return res.json()['access']

    def test_unauthenticated_download_rejected(self):
        res = self.client.get(self.download_path)
        self.assertIn(res.status_code, (401, 403))

    def test_participant_student_can_download(self):
        token = self._token(self.student)
        res = self.client.get(self.download_path, HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(res.status_code, 200)

    def test_other_student_cannot_download(self):
        token = self._token(self.other_student)
        res = self.client.get(self.download_path, HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(res.status_code, 404)

    def test_staff_can_download(self):
        token = self._token(self.staff)
        res = self.client.get(self.download_path, HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(res.status_code, 200)

    def test_direct_media_url_not_served_outside_debug(self):
        """/media/ is only mounted when DEBUG=True; homework files have no public URL."""
        media_path = f'/media/{self.entry.attachment.name}'
        res = self.client.get(media_path)
        # DEBUG=False in tests (or the static() helper is inert) → no file handed out
        self.assertNotEqual(res.status_code, 200)


class SessionHistoryPrivacyTests(TestCase):
    def setUp(self):
        Group.objects.create(name='student')
        Group.objects.create(name='teacher')
        Group.objects.create(name='staff')
        self.teacher_a = User.objects.create_user('hist_teacher_a', password='pass')
        self.teacher_a.groups.add(Group.objects.get(name='teacher'))
        self.teacher_b = User.objects.create_user('hist_teacher_b', password='pass')
        self.teacher_b.groups.add(Group.objects.get(name='teacher'))
        self.student = User.objects.create_user('hist_student', password='pass')
        self.student.groups.add(Group.objects.get(name='student'))
        self.staff = User.objects.create_user('hist_staff', password='pass')
        self.staff.groups.add(Group.objects.get(name='staff'))

        past = timezone.now() - timedelta(days=2)
        offering = ClassOffering.objects.create(
            teacher=self.teacher_a,
            subject='Japanese',
            level='Beginner',
            focus='Conversation',
        )
        ClassTopic.objects.create(class_offering=offering, title='Greetings', sort_order=0)
        self.session_a = Session.objects.create(
            teacher=self.teacher_a,
            title='Lesson with A',
            start_time=past,
            end_time=past + timedelta(hours=1),
            capacity=2,
            status='open',
            class_offering=offering,
        )
        self.session_b = Session.objects.create(
            teacher=self.teacher_b,
            title='Lesson with B',
            start_time=past + timedelta(hours=2),
            end_time=past + timedelta(hours=3),
            capacity=2,
            status='open',
            class_offering=offering,
        )
        Booking.objects.create(session=self.session_a, student=self.student, status='confirmed')
        Booking.objects.create(session=self.session_b, student=self.student, status='confirmed')
        Booking.objects.create(
            session=self.session_b,
            student=User.objects.create_user('hist_peer', password='pass'),
            status='confirmed',
        )

    def _token(self, user):
        res = self.client.post(
            '/api/auth/token/',
            {'username': user.username, 'password': 'pass'},
            content_type='application/json',
        )
        return res.json()['access']

    def _session_ids_from_history(self, data):
        ids = []
        for section in data.get('sections', []):
            for cls in section.get('classes', []):
                for session in cls.get('sessions', []):
                    ids.append(session['id'])
        return ids

    def test_peer_teacher_sees_other_teacher_past_session(self):
        token = self._token(self.teacher_b)
        res = self.client.get(
            f'/api/teacher/students/{self.student.id}/history/',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn(self.session_a.id, self._session_ids_from_history(res.json()))

    def test_student_hide_blocks_peer_teacher(self):
        token = self._token(self.student)
        self.client.patch(
            f'/api/progress/sessions/{self.session_a.id}/history-privacy/',
            {'hidden_by_student': True},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        peer_token = self._token(self.teacher_b)
        res = self.client.get(
            f'/api/teacher/students/{self.student.id}/history/',
            HTTP_AUTHORIZATION=f'Bearer {peer_token}',
        )
        self.assertEqual(res.status_code, 200)
        self.assertNotIn(self.session_a.id, self._session_ids_from_history(res.json()))

    def test_teaching_teacher_still_sees_own_hidden_session(self):
        token = self._token(self.teacher_a)
        self.client.patch(
            f'/api/teacher/sessions/{self.session_a.id}/history-privacy/',
            {'hidden_by_teacher': True},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        res = self.client.get(
            f'/api/teacher/students/{self.student.id}/history/',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertIn(self.session_a.id, self._session_ids_from_history(res.json()))

    def test_staff_sees_hidden_session(self):
        token = self._token(self.student)
        self.client.patch(
            f'/api/progress/sessions/{self.session_a.id}/history-privacy/',
            {'hidden_by_student': True},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        staff_token = self._token(self.staff)
        res = self.client.get(
            f'/api/progress/staff/teachers/{self.teacher_a.id}/students/{self.student.id}/history/',
            HTTP_AUTHORIZATION=f'Bearer {staff_token}',
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn(self.session_a.id, self._session_ids_from_history(res.json()))
