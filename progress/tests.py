"""Homework media privacy — files must only be reachable through the authenticated API."""

import shutil
import tempfile
from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone

from progress.homework_services import create_homework_assignment
from progress.models import ProgressReport, SessionFeedback
from scheduling.models import Booking, ClassOffering, ClassTopic, Session
from scheduling.services.teacher_permissions import (
    ensure_default_permissions,
    set_teacher_permissions,
)

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


class TeacherWriteReportsPermissionTests(TestCase):
    """Every teacher write gated by `write_reports` must honour the staff-set flag."""

    def setUp(self):
        Group.objects.create(name='student')
        Group.objects.create(name='teacher')
        self.teacher = User.objects.create_user('perm_teacher', password='pass')
        self.teacher.groups.add(Group.objects.get(name='teacher'))
        self.student = User.objects.create_user('perm_student', password='pass')
        self.student.groups.add(Group.objects.get(name='student'))
        ensure_default_permissions(self.teacher)

    def _token(self, user):
        return self.client.post(
            '/api/auth/token/',
            {'username': user.username, 'password': 'pass'},
            content_type='application/json',
        ).json()['access']

    def _post_progress_report(self):
        return self.client.post(
            '/api/progress/teacher/',
            {'student': self.student.id, 'rating': 4, 'note': 'Good progress.'},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self._token(self.teacher)}',
        )

    def test_progress_report_allowed_with_permission(self):
        res = self._post_progress_report()
        self.assertEqual(res.status_code, 201)
        self.assertEqual(ProgressReport.objects.filter(teacher=self.teacher).count(), 1)

    def test_progress_report_denied_without_permission(self):
        set_teacher_permissions(self.teacher, {'write_reports': False})
        res = self._post_progress_report()
        self.assertEqual(res.status_code, 403)
        self.assertFalse(ProgressReport.objects.filter(teacher=self.teacher).exists())

    def test_session_feedback_denied_without_permission(self):
        set_teacher_permissions(self.teacher, {'write_reports': False})
        res = self.client.post(
            '/api/progress/feedback/teacher/',
            {'student': self.student.id, 'summary': 'Nice work.'},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self._token(self.teacher)}',
        )
        self.assertEqual(res.status_code, 403)


class TeacherHomeQueueTests(TestCase):
    """The teacher home lists lessons just taught and the reports still owed."""

    def setUp(self):
        Group.objects.create(name='student')
        Group.objects.create(name='teacher')
        Group.objects.create(name='staff')
        self.teacher = User.objects.create_user('queue_teacher', password='pass')
        self.teacher.groups.add(Group.objects.get(name='teacher'))
        self.other_teacher = User.objects.create_user('queue_other', password='pass')
        self.other_teacher.groups.add(Group.objects.get(name='teacher'))
        self.student = User.objects.create_user('queue_student', password='pass')
        self.student.groups.add(Group.objects.get(name='student'))
        self.staff = User.objects.create_user('queue_staff', password='pass')
        self.staff.groups.add(Group.objects.get(name='staff'))

        self.past_session = self._session(self.teacher, 'Finished lesson', days_ago=2)
        Booking.objects.create(session=self.past_session, student=self.student, status='confirmed')

    def _session(self, teacher, title, *, days_ago=None, days_ahead=None):
        if days_ago is not None:
            start = timezone.now() - timedelta(days=days_ago)
        else:
            start = timezone.now() + timedelta(days=days_ahead)
        return Session.objects.create(
            teacher=teacher,
            title=title,
            start_time=start,
            end_time=start + timedelta(hours=1),
            capacity=2,
            status='open',
        )

    def _token(self, user):
        return self.client.post(
            '/api/auth/token/',
            {'username': user.username, 'password': 'pass'},
            content_type='application/json',
        ).json()['access']

    def _home(self, user=None):
        user = user or self.teacher
        res = self.client.get(
            '/api/teacher/home/',
            HTTP_AUTHORIZATION=f'Bearer {self._token(user)}',
        )
        self.assertEqual(res.status_code, 200)
        return res.json()

    def test_past_lesson_without_feedback_is_in_the_queue(self):
        data = self._home()
        self.assertEqual(data['missing_reports_total'], 1)
        row = data['missing_reports'][0]
        self.assertEqual(row['student_name'], 'queue_student')
        self.assertEqual(row['session']['id'], self.past_session.id)
        self.assertEqual(data['recent_sessions'][0]['reported_count'], 0)

    def test_writing_feedback_clears_the_queue(self):
        SessionFeedback.objects.create(
            teacher=self.teacher,
            student=self.student,
            session=self.past_session,
        )
        data = self._home()
        self.assertEqual(data['missing_reports'], [])
        self.assertEqual(data['recent_sessions'][0]['reported_count'], 1)

    def test_upcoming_lessons_are_not_owed_a_report(self):
        upcoming = self._session(self.teacher, 'Next week', days_ahead=5)
        Booking.objects.create(session=upcoming, student=self.student, status='confirmed')
        data = self._home()
        self.assertEqual(data['missing_reports_total'], 1)
        session_ids = [row['session']['id'] for row in data['missing_reports']]
        self.assertNotIn(upcoming.id, session_ids)

    def test_cancelled_bookings_and_sessions_are_skipped(self):
        cancelled_session = self._session(self.teacher, 'Called off', days_ago=1)
        cancelled_session.status = 'cancelled'
        cancelled_session.save(update_fields=['status'])
        Booking.objects.create(
            session=cancelled_session,
            student=self.student,
            status='confirmed',
        )
        dropped = self._session(self.teacher, 'Student dropped', days_ago=1)
        Booking.objects.create(session=dropped, student=self.student, status='cancelled')

        data = self._home()
        self.assertEqual(data['missing_reports_total'], 1)
        self.assertEqual(data['missing_reports'][0]['session']['id'], self.past_session.id)

    def test_another_teachers_lesson_is_not_listed(self):
        theirs = self._session(self.other_teacher, 'Not mine', days_ago=1)
        Booking.objects.create(session=theirs, student=self.student, status='confirmed')
        data = self._home()
        session_ids = [row['session']['id'] for row in data['missing_reports']]
        self.assertNotIn(theirs.id, session_ids)

    def test_staff_can_read_a_teachers_queue(self):
        res = self.client.get(
            f'/api/staff/teachers/{self.teacher.id}/home/',
            HTTP_AUTHORIZATION=f'Bearer {self._token(self.staff)}',
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['missing_reports_total'], 1)

    def test_student_cannot_read_the_teacher_queue(self):
        res = self.client.get(
            '/api/teacher/home/',
            HTTP_AUTHORIZATION=f'Bearer {self._token(self.student)}',
        )
        self.assertEqual(res.status_code, 403)


class StaffStudioFeedbackListTests(TestCase):
    """Staff can browse completed reports across every teacher."""

    def setUp(self):
        Group.objects.create(name='student')
        Group.objects.create(name='teacher')
        Group.objects.create(name='staff')
        self.teacher = User.objects.create_user('studio_teacher', password='pass')
        self.teacher.groups.add(Group.objects.get(name='teacher'))
        self.other_teacher = User.objects.create_user('studio_teacher_2', password='pass')
        self.other_teacher.groups.add(Group.objects.get(name='teacher'))
        self.student = User.objects.create_user('studio_student', password='pass')
        self.student.groups.add(Group.objects.get(name='student'))
        self.staff = User.objects.create_user('studio_staff', password='pass')
        self.staff.groups.add(Group.objects.get(name='staff'))

        SessionFeedback.objects.create(
            teacher=self.teacher,
            student=self.student,
            class_notes='Great pronunciation work.',
        )
        SessionFeedback.objects.create(
            teacher=self.other_teacher,
            student=self.student,
            class_notes='Needs more reading practice.',
        )

    def _token(self, user):
        return self.client.post(
            '/api/auth/token/',
            {'username': user.username, 'password': 'pass'},
            content_type='application/json',
        ).json()['access']

    def test_staff_sees_every_teachers_reports(self):
        res = self.client.get(
            '/api/progress/staff/feedback/',
            HTTP_AUTHORIZATION=f'Bearer {self._token(self.staff)}',
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['total'], 2)
        self.assertEqual(
            {row['teacher_name'] for row in data['reports']},
            {'studio_teacher', 'studio_teacher_2'},
        )

    def test_teacher_filter_narrows_the_list(self):
        res = self.client.get(
            f'/api/progress/staff/feedback/?teacher_id={self.teacher.id}',
            HTTP_AUTHORIZATION=f'Bearer {self._token(self.staff)}',
        )
        data = res.json()
        self.assertEqual(data['total'], 1)
        self.assertEqual(data['reports'][0]['notes_excerpt'], 'Great pronunciation work.')

    def test_teachers_and_students_are_refused(self):
        for user in (self.teacher, self.student):
            res = self.client.get(
                '/api/progress/staff/feedback/',
                HTTP_AUTHORIZATION=f'Bearer {self._token(user)}',
            )
            self.assertEqual(res.status_code, 403)
