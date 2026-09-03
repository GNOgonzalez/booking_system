"""Curriculum tracks and per-student enrollment APIs."""

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from scheduling.api.permissions import IsStaff, IsStudent, IsTeacherOrStaff
from scheduling.api.serializers import StudentOptionSerializer
from scheduling.models import CurriculumModule, Profile
from scheduling.services.curriculum import (
    create_custom_track_for_students,
    create_track,
    delete_track,
    enroll_student,
    enroll_student_on_template,
    get_active_enrollment,
    get_track,
    list_staff_tracks,
    list_templates,
    serialize_enrollment,
    serialize_track,
    set_module_progress,
    update_track,
)
from scheduling.services.roster import roster_students_for_teacher, teacher_can_manage_student
from scheduling.services.teacher_permissions import permission_denied_response, teacher_can, user_is_staff
from scheduling.services.users import get_student

User = get_user_model()


def _teacher_from_request(request, teacher_id=None):
    if teacher_id is not None:
        return User.objects.filter(pk=teacher_id, groups__name='teacher').first()
    if request.user.groups.filter(name='teacher').exists():
        return request.user
    return None


def _student_payload(student, teacher=None):
    profile = Profile.objects.filter(user=student).first()
    display = profile.display_name if profile else ''
    enrollment = get_active_enrollment(student)
    assigned = False
    if teacher is not None:
        from scheduling.services.roster import is_assigned

        assigned = is_assigned(teacher, student)
    return {
        'id': student.id,
        'username': student.username,
        'label': StudentOptionSerializer(student).data['label'],
        'display_name': display,
        'assigned': assigned,
        'enrollment': serialize_enrollment(enrollment, student=student),
    }


class StudentCurriculumMeView(APIView):
    permission_classes = [IsStudent]

    def get(self, request):
        enrollment = get_active_enrollment(request.user)
        return Response({'enrollment': serialize_enrollment(enrollment, student=request.user)})

    def post(self, request):
        """Enroll in a premade template: { track_id }."""
        track = get_track(request.data.get('track_id'))
        enrollment, err = enroll_student_on_template(request.user, track)
        if err:
            return Response({'detail': err}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {'enrollment': serialize_enrollment(enrollment, student=request.user)},
            status=status.HTTP_201_CREATED,
        )


class CurriculumTemplateListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tracks = list_templates()
        return Response([serialize_track(track) for track in tracks])


class StaffCurriculumTrackListCreateView(APIView):
    permission_classes = [IsStaff]

    def get(self, request):
        return Response([serialize_track(track) for track in list_staff_tracks()])

    def post(self, request):
        track, err = create_track(
            title=request.data.get('title', ''),
            description=request.data.get('description', ''),
            is_template=request.data.get('is_template', True),
            is_active=request.data.get('is_active', True),
            created_by=request.user,
            modules=request.data.get('modules'),
        )
        if err:
            return Response({'detail': err}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serialize_track(track), status=status.HTTP_201_CREATED)


class StaffCurriculumTrackDetailView(APIView):
    permission_classes = [IsStaff]

    def get(self, request, pk):
        track = get_track(pk)
        if track is None:
            return Response({'detail': 'Curriculum not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(serialize_track(track))

    def patch(self, request, pk):
        track = get_track(pk)
        if track is None:
            return Response({'detail': 'Curriculum not found.'}, status=status.HTTP_404_NOT_FOUND)
        data = request.data
        updated, err = update_track(
            track,
            title=data['title'] if 'title' in data else None,
            description=data['description'] if 'description' in data else None,
            is_template=data['is_template'] if 'is_template' in data else None,
            is_active=data['is_active'] if 'is_active' in data else None,
            modules=data['modules'] if 'modules' in data else None,
        )
        if err:
            return Response({'detail': err}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serialize_track(updated))

    def delete(self, request, pk):
        track = get_track(pk)
        if track is None:
            return Response({'detail': 'Curriculum not found.'}, status=status.HTTP_404_NOT_FOUND)
        delete_track(track)
        return Response(status=status.HTTP_204_NO_CONTENT)


class TeacherCurriculumStudentsView(APIView):
    permission_classes = [IsTeacherOrStaff]

    def get(self, request, teacher_id=None):
        teacher = _teacher_from_request(request, teacher_id)
        if teacher is None:
            return Response({'detail': 'Teacher not found.'}, status=status.HTTP_404_NOT_FOUND)
        students = roster_students_for_teacher(teacher)
        return Response([_student_payload(student, teacher=teacher) for student in students])


class TeacherCurriculumTrackCreateView(APIView):
    permission_classes = [IsTeacherOrStaff]

    def post(self, request, teacher_id=None):
        teacher = _teacher_from_request(request, teacher_id)
        if teacher is None:
            return Response({'detail': 'Teacher not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not user_is_staff(request.user) and not teacher_can(request.user, 'manage_curriculum'):
            return permission_denied_response('manage_curriculum')
        student_ids = request.data.get('student_ids') or []
        students = [get_student(sid) for sid in student_ids]
        students = [s for s in students if s is not None]
        track, err, summary = create_custom_track_for_students(
            teacher=teacher,
            title=request.data.get('title', ''),
            description=request.data.get('description', ''),
            modules=request.data.get('modules'),
            students=students,
        )
        if err:
            return Response({'detail': err}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {**serialize_track(track), **summary},
            status=status.HTTP_201_CREATED,
        )


class TeacherCurriculumEnrollView(APIView):
    permission_classes = [IsTeacherOrStaff]

    def post(self, request, student_id, teacher_id=None):
        teacher = _teacher_from_request(request, teacher_id)
        if teacher is None:
            return Response({'detail': 'Teacher not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not user_is_staff(request.user) and not teacher_can(request.user, 'manage_curriculum'):
            return permission_denied_response('manage_curriculum')
        student = get_student(student_id)
        if student is None:
            return Response({'detail': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not teacher_can_manage_student(teacher, student):
            return Response({'detail': 'You are not assigned to this student.'}, status=status.HTTP_403_FORBIDDEN)
        track = get_track(request.data.get('track_id'))
        enrollment, err = enroll_student(student, track, actor=request.user)
        if err:
            return Response({'detail': err}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'enrollment': serialize_enrollment(enrollment, student=student)})


class TeacherCurriculumModuleProgressView(APIView):
    permission_classes = [IsTeacherOrStaff]

    def post(self, request, module_id, teacher_id=None):
        teacher = _teacher_from_request(request, teacher_id)
        if teacher is None:
            return Response({'detail': 'Teacher not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not user_is_staff(request.user) and not teacher_can(request.user, 'manage_curriculum'):
            return permission_denied_response('manage_curriculum')
        module = CurriculumModule.objects.filter(pk=module_id).select_related('track').first()
        if module is None:
            return Response({'detail': 'Module not found.'}, status=status.HTTP_404_NOT_FOUND)
        student = get_student(request.data.get('student_id'))
        if student is None:
            return Response({'detail': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not teacher_can_manage_student(teacher, student):
            return Response({'detail': 'You are not assigned to this student.'}, status=status.HTTP_403_FORBIDDEN)
        action = (request.data.get('status') or request.data.get('action') or '').strip()
        if action == 'skip':
            action = 'skipped'
        if action == 'complete':
            action = 'completed'
        row, err = set_module_progress(student, module, action, actor=request.user)
        if err:
            return Response({'detail': err}, status=status.HTTP_400_BAD_REQUEST)
        enrollment = get_active_enrollment(student)
        return Response({
            'status': row.status,
            'enrollment': serialize_enrollment(enrollment, student=student),
        })
