from django.contrib.auth import get_user_model
from rest_framework import generics, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from progress.api.serializers import (
    SessionFeedbackSerializer,
)
from progress.homework_services import (
    add_homework_entry,
    assignments_for_teacher,
    create_homework_assignment,
    serialize_assignment,
)
from progress.models import HomeworkAssignment, SessionFeedback
from scheduling.api.permissions import IsStaff
from scheduling.models import Session

User = get_user_model()

class StaffTeacherFeedbackListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsStaff]
    serializer_class = SessionFeedbackSerializer

    def get_teacher(self):
        from scheduling.services.staff import get_teacher
        return get_teacher(self.kwargs['teacher_id'])

    def get_queryset(self):
        teacher = self.get_teacher()
        if teacher is None:
            return SessionFeedback.objects.none()
        return SessionFeedback.objects.filter(teacher=teacher)

    def list(self, request, *args, **kwargs):
        if self.get_teacher() is None:
            return Response({'detail': 'Teacher not found.'}, status=status.HTTP_404_NOT_FOUND)
        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        teacher = self.get_teacher()
        serializer.save(teacher=teacher)



class StaffTeacherFeedbackDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsStaff]
    serializer_class = SessionFeedbackSerializer
    http_method_names = ['patch', 'put', 'delete', 'options', 'head']

    def get_teacher(self):
        from scheduling.services.staff import get_teacher
        return get_teacher(self.kwargs['teacher_id'])

    def get_queryset(self):
        teacher = self.get_teacher()
        if teacher is None:
            return SessionFeedback.objects.none()
        return SessionFeedback.objects.filter(teacher=teacher)



class StaffTeacherHomeworkListCreateView(APIView):
    permission_classes = [IsStaff]
    parser_classes = [MultiPartParser, FormParser]

    def get_teacher(self):
        from scheduling.services.staff import get_teacher
        return get_teacher(self.kwargs['teacher_id'])

    def get(self, request, teacher_id):
        teacher = self.get_teacher()
        if teacher is None:
            return Response({'detail': 'Teacher not found.'}, status=status.HTTP_404_NOT_FOUND)
        rows = assignments_for_teacher(teacher)
        return Response([
            serialize_assignment(row, request=request, include_entries=False) for row in rows
        ])

    def post(self, request, teacher_id):
        teacher = self.get_teacher()
        if teacher is None:
            return Response({'detail': 'Teacher not found.'}, status=status.HTTP_404_NOT_FOUND)
        User = get_user_model()
        student_id = request.data.get('student')
        student = User.objects.filter(pk=student_id, groups__name='student', is_active=True).first()
        if student is None:
            return Response({'detail': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)
        session_id = request.data.get('session')
        if not session_id:
            return Response({'detail': 'Session is required.'}, status=status.HTTP_400_BAD_REQUEST)
        session = Session.objects.filter(pk=session_id, teacher=teacher).first()
        if session is None:
            return Response({'detail': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)
        assignment, error = create_homework_assignment(
            teacher=teacher,
            student=student,
            session=session,
            kind=request.data.get('kind', HomeworkAssignment.KIND_FILE),
            title=request.data.get('title', ''),
            prompt=request.data.get('prompt', ''),
            initial_file=request.FILES.get('attachment'),
        )
        if error:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            serialize_assignment(assignment, request=request),
            status=status.HTTP_201_CREATED,
        )



class StaffTeacherHomeworkDetailView(APIView):
    permission_classes = [IsStaff]

    def get_teacher(self):
        from scheduling.services.staff import get_teacher
        return get_teacher(self.kwargs['teacher_id'])

    def get(self, request, teacher_id, pk):
        teacher = self.get_teacher()
        if teacher is None:
            return Response({'detail': 'Teacher not found.'}, status=status.HTTP_404_NOT_FOUND)
        assignment = (
            HomeworkAssignment.objects.select_related('teacher', 'student', 'session', 'session__class_offering')
            .prefetch_related('entries', 'entries__author')
            .filter(pk=pk, teacher=teacher)
            .first()
        )
        if assignment is None:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(serialize_assignment(assignment, request=request))



class StaffTeacherHomeworkEntryCreateView(APIView):
    permission_classes = [IsStaff]
    parser_classes = [MultiPartParser, FormParser]

    def get_teacher(self):
        from scheduling.services.staff import get_teacher
        return get_teacher(self.kwargs['teacher_id'])

    def post(self, request, teacher_id, pk):
        teacher = self.get_teacher()
        if teacher is None:
            return Response({'detail': 'Teacher not found.'}, status=status.HTTP_404_NOT_FOUND)
        assignment = HomeworkAssignment.objects.filter(pk=pk, teacher=teacher).first()
        if assignment is None:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        ok, error = add_homework_entry(
            assignment,
            author=teacher,
            body=request.data.get('body', ''),
            uploaded_file=request.FILES.get('attachment'),
        )
        if not ok:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
        assignment.refresh_from_db()
        return Response(serialize_assignment(assignment, request=request), status=status.HTTP_201_CREATED)
