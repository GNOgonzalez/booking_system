from rest_framework import generics, serializers

from progress.models import ProgressReport, Skill
from scheduling.api.permissions import IsStudent, IsTeacher


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ['id', 'name']


class ProgressReportSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.username', read_only=True)
    teacher_name = serializers.CharField(source='teacher.username', read_only=True)
    skill_name = serializers.CharField(source='skill.name', read_only=True, default=None)

    class Meta:
        model = ProgressReport
        fields = [
            'id',
            'student',
            'student_name',
            'teacher_name',
            'skill',
            'skill_name',
            'rating',
            'note',
            'created_at',
        ]
        read_only_fields = ['teacher_name', 'created_at']


class MyProgressListView(generics.ListAPIView):
    permission_classes = [IsStudent]
    serializer_class = ProgressReportSerializer

    def get_queryset(self):
        return ProgressReport.objects.filter(student=self.request.user)


class TeacherProgressListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsTeacher]
    serializer_class = ProgressReportSerializer

    def get_queryset(self):
        return ProgressReport.objects.filter(teacher=self.request.user)

    def perform_create(self, serializer):
        serializer.save(teacher=self.request.user)
