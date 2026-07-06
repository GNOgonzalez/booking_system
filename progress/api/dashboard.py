from django.contrib.auth import get_user_model
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from progress.api.serializers import (
    ProgressReportSerializer,
    SessionFeedbackSerializer,
)
from progress.models import ProgressReport, SessionFeedback
from progress.services import (
    student_dashboard,
)
from scheduling.api.permissions import IsStudent, IsTeacher

User = get_user_model()

class MyProgressListView(generics.ListAPIView):
    permission_classes = [IsStudent]
    serializer_class = ProgressReportSerializer

    def get_queryset(self):
        return ProgressReport.objects.filter(student=self.request.user)



class MySessionFeedbackListView(generics.ListAPIView):
    """Chronological per-skill feedback for the logged-in student (for charts)."""

    permission_classes = [IsStudent]
    serializer_class = SessionFeedbackSerializer

    def get_queryset(self):
        return SessionFeedback.objects.filter(student=self.request.user)



class MyStudentDashboardView(APIView):
    """Student progress grouped by subject — metrics and class history."""

    permission_classes = [IsStudent]

    def get(self, request):
        sections = student_dashboard(request.user)
        serializer = SessionFeedbackSerializer()
        payload = []
        for section in sections:
            payload.append({
                'subject': section['subject'],
                'metrics': section['metrics'],
                'feedback_count': section['feedback_count'],
                'session_count': section['session_count'],
                'class_count': section['class_count'],
                'classes': section['classes'],
                'feedback': [
                    serializer.to_representation(fb) for fb in section['feedback']
                ],
            })
        return Response(payload)



class TeacherProgressListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsTeacher]
    serializer_class = ProgressReportSerializer

    def get_queryset(self):
        return ProgressReport.objects.filter(teacher=self.request.user)

    def perform_create(self, serializer):
        serializer.save(teacher=self.request.user)


