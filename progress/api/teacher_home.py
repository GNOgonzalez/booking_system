from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from progress.teacher_home import teacher_home
from scheduling.api.permissions import IsStaff, IsTeacher
from scheduling.services.staff import get_teacher


class TeacherHomeView(APIView):
    """Recently taught lessons and the report backlog for the logged-in teacher."""

    permission_classes = [IsTeacher]

    def get(self, request):
        return Response(teacher_home(request.user))


class StaffTeacherHomeView(APIView):
    """Same queues for staff reviewing one teacher."""

    permission_classes = [IsStaff]

    def get(self, request, teacher_id):
        teacher = get_teacher(teacher_id)
        if teacher is None:
            return Response({'detail': 'Teacher not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(teacher_home(teacher))
