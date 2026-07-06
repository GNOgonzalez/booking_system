from django.contrib.auth import get_user_model
from rest_framework import generics

from progress.api.serializers import (
    SessionFeedbackSerializer,
)
from progress.models import SessionFeedback
from scheduling.api.permissions import IsTeacher
from scheduling.services.teacher_permissions import permission_denied_response, teacher_can

User = get_user_model()

class TeacherSessionFeedbackListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsTeacher]
    serializer_class = SessionFeedbackSerializer

    def get_queryset(self):
        return SessionFeedback.objects.filter(teacher=self.request.user)

    def perform_create(self, serializer):
        if not teacher_can(self.request.user, 'write_reports'):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('You do not have permission to write reports.')
        serializer.save(teacher=self.request.user)



class TeacherSessionFeedbackDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsTeacher]
    serializer_class = SessionFeedbackSerializer
    http_method_names = ['patch', 'put', 'delete', 'options', 'head']

    def get_queryset(self):
        return SessionFeedback.objects.filter(teacher=self.request.user)

    def update(self, request, *args, **kwargs):
        if not teacher_can(request.user, 'write_reports'):
            return permission_denied_response('write_reports')
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not teacher_can(request.user, 'write_reports'):
            return permission_denied_response('write_reports')
        return super().destroy(request, *args, **kwargs)


