"""Class request API — students request times; teachers approve."""

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from scheduling.api.permissions import IsStudent, IsTeacherOrStaff
from scheduling.api.serializers import (
    ClassOfferingSerializer,
    ClassRequestCreateSerializer,
    ClassRequestSerializer,
    ClassRequestUpdateSerializer,
    TeacherRequestOptionSerializer,
)
from scheduling.models import ClassOffering, ClassRequest, ClassTopic
from scheduling.services.class_requests import (
    approve_class_request,
    availability_snapshot,
    cancel_pending_request,
    classes_for_teacher_request,
    create_class_request,
    delete_class_request,
    deny_class_request,
    pending_requests_for_teacher,
    requests_for_student,
    teachers_for_student_requests,
    update_pending_request,
)

User = get_user_model()


def _teacher_from_request(request, teacher_id=None):
    if teacher_id is not None:
        return User.objects.filter(pk=teacher_id, groups__name='teacher', is_active=True).first()
    if request.user.groups.filter(name='teacher').exists():
        return request.user
    return None


class ClassRequestTeacherListView(APIView):
    permission_classes = [IsStudent]

    def get(self, request):
        teachers = teachers_for_student_requests(request.user)
        rows = [
            {'id': t.id, 'username': t.username, 'label': t.username}
            for t in teachers
        ]
        return Response(TeacherRequestOptionSerializer(rows, many=True).data)


class ClassRequestTeacherClassesView(APIView):
    permission_classes = [IsStudent]

    def get(self, request):
        teacher_id = request.query_params.get('teacher')
        if not teacher_id:
            return Response({'detail': 'teacher is required.'}, status=status.HTTP_400_BAD_REQUEST)
        teacher = User.objects.filter(pk=teacher_id, groups__name='teacher', is_active=True).first()
        if teacher is None:
            return Response({'detail': 'Teacher not found.'}, status=status.HTTP_404_NOT_FOUND)
        classes = classes_for_teacher_request(request.user, teacher)
        return Response(ClassOfferingSerializer(classes, many=True).data)


class ClassRequestAvailabilityView(APIView):
    permission_classes = [IsStudent]

    def get(self, request):
        teacher_id = request.query_params.get('teacher')
        if not teacher_id:
            return Response({'detail': 'teacher is required.'}, status=status.HTTP_400_BAD_REQUEST)
        teacher = User.objects.filter(pk=teacher_id, groups__name='teacher', is_active=True).first()
        if teacher is None:
            return Response({'detail': 'Teacher not found.'}, status=status.HTTP_404_NOT_FOUND)
        days = int(request.query_params.get('days', 28))
        return Response(availability_snapshot(teacher, days=days))


class StudentClassRequestListCreateView(APIView):
    permission_classes = [IsStudent]

    def get(self, request):
        rows = requests_for_student(request.user)
        return Response(ClassRequestSerializer(rows, many=True).data)

    def post(self, request):
        serializer = ClassRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        teacher = User.objects.filter(pk=data['teacher'], groups__name='teacher', is_active=True).first()
        if teacher is None:
            return Response({'detail': 'Teacher not found.'}, status=status.HTTP_404_NOT_FOUND)
        offering = ClassOffering.objects.filter(pk=data['class_offering'], teacher=teacher, is_active=True).first()
        if offering is None:
            return Response({'detail': 'Class not found.'}, status=status.HTTP_404_NOT_FOUND)
        topic = None
        topic_id = data.get('class_topic')
        if topic_id:
            topic = ClassTopic.objects.filter(pk=topic_id, class_offering=offering).first()
            if topic is None:
                return Response({'detail': 'Topic not found.'}, status=status.HTTP_404_NOT_FOUND)
        created, error = create_class_request(
            request.user,
            teacher=teacher,
            class_offering=offering,
            class_topic=topic,
            start_time=data['start_time'],
            end_time=data['end_time'],
            tickets_requested=data['tickets_requested'],
        )
        if error:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ClassRequestSerializer(created).data, status=status.HTTP_201_CREATED)


class StudentClassRequestDetailView(APIView):
    permission_classes = [IsStudent]

    def delete(self, request, pk):
        class_request = ClassRequest.objects.filter(pk=pk, student=request.user).first()
        if class_request is None:
            return Response({'detail': 'Request not found.'}, status=status.HTTP_404_NOT_FOUND)
        ok, error = cancel_pending_request(request.user, class_request)
        if not ok:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)


class TeacherClassRequestListView(APIView):
    permission_classes = [IsTeacherOrStaff]

    def get(self, request, teacher_id=None):
        teacher = _teacher_from_request(request, teacher_id)
        if teacher is None:
            return Response({'detail': 'Teacher not found.'}, status=status.HTTP_404_NOT_FOUND)
        is_staff = request.user.groups.filter(name='staff').exists()
        if teacher_id is None and not is_staff and teacher != request.user:
            return Response({'detail': 'Forbidden.'}, status=status.HTTP_403_FORBIDDEN)
        rows = pending_requests_for_teacher(teacher)
        return Response(ClassRequestSerializer(rows, many=True).data)


class TeacherClassRequestDetailView(APIView):
    permission_classes = [IsTeacherOrStaff]

    def _get_request(self, request, pk, teacher_id=None):
        teacher = _teacher_from_request(request, teacher_id)
        if teacher is None:
            return None, Response({'detail': 'Teacher not found.'}, status=status.HTTP_404_NOT_FOUND)
        is_staff = request.user.groups.filter(name='staff').exists()
        if teacher_id is None and not is_staff and teacher != request.user:
            return None, Response({'detail': 'Forbidden.'}, status=status.HTTP_403_FORBIDDEN)
        class_request = ClassRequest.objects.filter(pk=pk, teacher=teacher).first()
        if class_request is None:
            return None, Response({'detail': 'Request not found.'}, status=status.HTTP_404_NOT_FOUND)
        return class_request, None

    def patch(self, request, pk, teacher_id=None):
        class_request, error_response = self._get_request(request, pk, teacher_id)
        if error_response is not None:
            return error_response
        serializer = ClassRequestUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        teacher = class_request.teacher
        fields = {}
        if 'class_offering' in data:
            offering = ClassOffering.objects.filter(
                pk=data['class_offering'],
                teacher=teacher,
                is_active=True,
            ).first()
            if offering is None:
                return Response({'detail': 'Class not found.'}, status=status.HTTP_404_NOT_FOUND)
            fields['class_offering'] = offering
        if 'class_topic' in data:
            offering = fields.get('class_offering', class_request.class_offering)
            topic = None
            if data['class_topic'] is not None:
                topic = ClassTopic.objects.filter(pk=data['class_topic'], class_offering=offering).first()
                if topic is None:
                    return Response({'detail': 'Topic not found.'}, status=status.HTTP_404_NOT_FOUND)
            fields['class_topic'] = topic
        if 'start_time' in data:
            fields['start_time'] = data['start_time']
        if 'end_time' in data:
            fields['end_time'] = data['end_time']
        updated, error = update_pending_request(class_request, teacher, **fields)
        if error:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ClassRequestSerializer(updated).data)


class TeacherClassRequestApproveView(APIView):
    permission_classes = [IsTeacherOrStaff]

    def post(self, request, pk, teacher_id=None):
        teacher = _teacher_from_request(request, teacher_id)
        if teacher is None:
            return Response({'detail': 'Teacher not found.'}, status=status.HTTP_404_NOT_FOUND)
        class_request = ClassRequest.objects.filter(pk=pk, teacher=teacher).first()
        if class_request is None:
            return Response({'detail': 'Request not found.'}, status=status.HTTP_404_NOT_FOUND)
        capacity = request.data.get('capacity')
        if capacity is not None:
            capacity = int(capacity)
        approved, error = approve_class_request(teacher, class_request, capacity=capacity)
        if error:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ClassRequestSerializer(approved).data)


class TeacherClassRequestDenyView(APIView):
    permission_classes = [IsTeacherOrStaff]

    def post(self, request, pk, teacher_id=None):
        teacher = _teacher_from_request(request, teacher_id)
        if teacher is None:
            return Response({'detail': 'Teacher not found.'}, status=status.HTTP_404_NOT_FOUND)
        class_request = ClassRequest.objects.filter(pk=pk, teacher=teacher).first()
        if class_request is None:
            return Response({'detail': 'Request not found.'}, status=status.HTTP_404_NOT_FOUND)
        ok, error = deny_class_request(teacher, class_request)
        if not ok:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'detail': 'Request denied.'})


class TeacherClassRequestDeleteView(APIView):
    permission_classes = [IsTeacherOrStaff]

    def delete(self, request, pk, teacher_id=None):
        teacher = _teacher_from_request(request, teacher_id)
        if teacher is None:
            return Response({'detail': 'Teacher not found.'}, status=status.HTTP_404_NOT_FOUND)
        class_request = ClassRequest.objects.filter(pk=pk, teacher=teacher).first()
        if class_request is None:
            return Response({'detail': 'Request not found.'}, status=status.HTTP_404_NOT_FOUND)
        ok, error = delete_class_request(teacher, class_request)
        if not ok:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)
