from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from progress.session_history import (
    STAFF_PRIVACY_DISCLAIMER,
    privacy_flags,
    set_session_history_privacy,
    student_history_for_staff,
    student_history_for_teacher,
    teacher_shares_student,
)
from scheduling.api.permissions import IsStaff, IsStudent, IsTeacher
from scheduling.models import Session
from scheduling.services.staff import get_teacher

User = get_user_model()


class TeacherStudentHistoryView(APIView):
    permission_classes = [IsTeacher]

    def get(self, request, student_id):
        student = User.objects.filter(pk=student_id, groups__name='student', is_active=True).first()
        if student is None:
            return Response({'detail': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)
        sections, error = student_history_for_teacher(request.user, student)
        if error:
            return Response({'detail': error}, status=status.HTTP_403_FORBIDDEN)
        return Response({'sections': sections, 'privacy_disclaimer': STAFF_PRIVACY_DISCLAIMER})


class TeacherSessionHistoryPrivacyView(APIView):
    permission_classes = [IsTeacher]

    def patch(self, request, session_id):
        session = Session.objects.filter(pk=session_id, teacher=request.user).first()
        if session is None:
            return Response({'detail': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)
        hidden = request.data.get('hidden_by_teacher')
        if hidden is None:
            return Response({'detail': 'hidden_by_teacher is required.'}, status=status.HTTP_400_BAD_REQUEST)
        _, error = set_session_history_privacy(
            request.user,
            session,
            hidden_by_teacher=bool(hidden),
        )
        if error:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'privacy': privacy_flags(session), 'privacy_disclaimer': STAFF_PRIVACY_DISCLAIMER})


class StudentSessionHistoryPrivacyView(APIView):
    permission_classes = [IsStudent]

    def patch(self, request, session_id):
        session = (
            Session.objects.filter(
                pk=session_id,
                bookings__student=request.user,
                bookings__status='confirmed',
            )
            .distinct()
            .first()
        )
        if session is None:
            return Response({'detail': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)
        hidden = request.data.get('hidden_by_student')
        if hidden is None:
            return Response({'detail': 'hidden_by_student is required.'}, status=status.HTTP_400_BAD_REQUEST)
        _, error = set_session_history_privacy(
            request.user,
            session,
            hidden_by_student=bool(hidden),
        )
        if error:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'privacy': privacy_flags(session), 'privacy_disclaimer': STAFF_PRIVACY_DISCLAIMER})


class StaffTeacherStudentHistoryView(APIView):
    permission_classes = [IsStaff]

    def get(self, request, teacher_id, student_id):
        teacher = get_teacher(teacher_id)
        if teacher is None:
            return Response({'detail': 'Teacher not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not teacher_shares_student(teacher, User.objects.filter(pk=student_id).first()):
            pass  # staff sees full student history regardless of teacher link
        student = User.objects.filter(pk=student_id, groups__name='student', is_active=True).first()
        if student is None:
            return Response({'detail': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)
        sections, error = student_history_for_staff(request.user, student)
        if error:
            return Response({'detail': error}, status=status.HTTP_403_FORBIDDEN)
        return Response({'sections': sections, 'teacher_id': teacher.id})
