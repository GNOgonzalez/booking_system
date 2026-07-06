from django.contrib.auth import get_user_model
from django.http import FileResponse, Http404
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from progress.homework_services import (
    add_homework_entry,
    assignments_for_student,
    assignments_for_teacher,
    create_homework_assignment,
    entry_attachment_active,
    purge_expired_homework_attachments,
    serialize_assignment,
    user_can_view_assignment,
)
from progress.models import HomeworkAssignment, HomeworkEntry
from scheduling.api.permissions import IsStudent, IsTeacher
from scheduling.models import Session
from scheduling.services.teacher_permissions import permission_denied_response, teacher_can

User = get_user_model()

class HomeworkAttachmentDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, entry_id):
        purge_expired_homework_attachments()
        entry = (
            HomeworkEntry.objects.select_related('assignment', 'author')
            .filter(pk=entry_id)
            .first()
        )
        if entry is None or not user_can_view_assignment(request.user, entry.assignment):
            raise Http404
        if not entry_attachment_active(entry):
            return Response({'detail': 'File expired or unavailable.'}, status=status.HTTP_404_NOT_FOUND)
        filename = entry.attachment_name or entry.attachment.name.split('/')[-1]
        return FileResponse(entry.attachment.open('rb'), as_attachment=True, filename=filename)



class MyHomeworkListView(APIView):
    permission_classes = [IsStudent]

    def get(self, request):
        rows = assignments_for_student(request.user)
        return Response([
            serialize_assignment(row, request=request, include_entries=False) for row in rows
        ])



class MyHomeworkDetailView(APIView):
    permission_classes = [IsStudent]

    def get(self, request, pk):
        assignment = (
            HomeworkAssignment.objects.select_related('teacher', 'student', 'session', 'session__class_offering')
            .prefetch_related('entries', 'entries__author')
            .filter(pk=pk, student=request.user)
            .first()
        )
        if assignment is None:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(serialize_assignment(assignment, request=request))



class MyHomeworkEntryCreateView(APIView):
    permission_classes = [IsStudent]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        assignment = HomeworkAssignment.objects.filter(pk=pk, student=request.user).first()
        if assignment is None:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        body = request.data.get('body', '')
        uploaded = request.FILES.get('attachment')
        ok, error = add_homework_entry(
            assignment,
            author=request.user,
            body=body,
            uploaded_file=uploaded,
        )
        if not ok:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
        assignment.refresh_from_db()
        return Response(serialize_assignment(assignment, request=request), status=status.HTTP_201_CREATED)



class TeacherHomeworkListCreateView(APIView):
    permission_classes = [IsTeacher]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        rows = assignments_for_teacher(request.user)
        return Response([
            serialize_assignment(row, request=request, include_entries=False) for row in rows
        ])

    def post(self, request):
        if not teacher_can(request.user, 'assign_homework'):
            return permission_denied_response('assign_homework')
        User = get_user_model()
        student_id = request.data.get('student')
        if not student_id:
            return Response({'detail': 'Student is required.'}, status=status.HTTP_400_BAD_REQUEST)
        student = User.objects.filter(pk=student_id, groups__name='student', is_active=True).first()
        if student is None:
            return Response({'detail': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)
        session_id = request.data.get('session')
        if not session_id:
            return Response({'detail': 'Session is required.'}, status=status.HTTP_400_BAD_REQUEST)
        session = Session.objects.filter(pk=session_id, teacher=request.user).first()
        if session is None:
            return Response({'detail': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)
        kind = request.data.get('kind', HomeworkAssignment.KIND_FILE)
        assignment, error = create_homework_assignment(
            teacher=request.user,
            student=student,
            session=session,
            kind=kind,
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



class TeacherHomeworkDetailView(APIView):
    permission_classes = [IsTeacher]

    def get(self, request, pk):
        assignment = (
            HomeworkAssignment.objects.select_related('teacher', 'student', 'session', 'session__class_offering')
            .prefetch_related('entries', 'entries__author')
            .filter(pk=pk, teacher=request.user)
            .first()
        )
        if assignment is None:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(serialize_assignment(assignment, request=request))



class TeacherHomeworkEntryCreateView(APIView):
    permission_classes = [IsTeacher]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        if not teacher_can(request.user, 'assign_homework'):
            return permission_denied_response('assign_homework')
        assignment = HomeworkAssignment.objects.filter(pk=pk, teacher=request.user).first()
        if assignment is None:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        ok, error = add_homework_entry(
            assignment,
            author=request.user,
            body=request.data.get('body', ''),
            uploaded_file=request.FILES.get('attachment'),
        )
        if not ok:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
        assignment.refresh_from_db()
        return Response(serialize_assignment(assignment, request=request), status=status.HTTP_201_CREATED)


