"""Studio AI / LLM configuration API."""

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from scheduling.api.permissions import IsStaff, IsTeacherOrStaff
from scheduling.models import Session
from scheduling.services.llm import (
    ai_available_for_user,
    llm_config_for_api,
    suggest_feedback_notes,
    test_llm_connection,
    update_llm_config,
)
from scheduling.services.teacher_permissions import permission_denied_response, teacher_can, user_is_staff

User = get_user_model()


class StaffLLMConfigView(APIView):
    permission_classes = [IsStaff]

    def get(self, request):
        return Response(llm_config_for_api())

    def patch(self, request):
        data = request.data
        _, error = update_llm_config(
            provider=data.get('provider'),
            api_key=data.get('api_key'),
            base_url=data.get('base_url'),
            model_name=data.get('model_name'),
            is_enabled=data.get('is_enabled'),
            max_tokens=data.get('max_tokens'),
        )
        if error:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
        return Response(llm_config_for_api())


class StaffLLMTestView(APIView):
    permission_classes = [IsStaff]

    def post(self, request):
        ok, message = test_llm_connection()
        if not ok:
            return Response({'detail': message}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'detail': 'Connection successful.', 'sample': message})


class TeacherAIStatusView(APIView):
    permission_classes = [IsTeacherOrStaff]

    def get(self, request):
        return Response({
            'available': ai_available_for_user(request.user),
            'studio_enabled': llm_config_for_api()['is_enabled'],
            'can_use_ai': user_is_staff(request.user) or teacher_can(request.user, 'use_ai'),
        })


class TeacherAISuggestFeedbackView(APIView):
    permission_classes = [IsTeacherOrStaff]

    def post(self, request):
        if not ai_available_for_user(request.user):
            if not user_is_staff(request.user) and not teacher_can(request.user, 'use_ai'):
                return permission_denied_response('use_ai')
            return Response(
                {'detail': 'Studio AI is not configured or disabled.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        student_id = request.data.get('student')
        if not student_id:
            return Response({'detail': 'Student is required.'}, status=status.HTTP_400_BAD_REQUEST)

        student = User.objects.filter(pk=student_id, groups__name='student', is_active=True).first()
        if student is None:
            return Response({'detail': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)

        session = None
        session_id = request.data.get('session')
        if session_id:
            qs = Session.objects.filter(pk=session_id)
            if not user_is_staff(request.user):
                qs = qs.filter(teacher=request.user)
            session = qs.first()
            if session is None:
                return Response({'detail': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)

        scores = request.data.get('scores') or {}
        metric_labels = request.data.get('metric_labels') or {}

        text, error = suggest_feedback_notes(
            student=student,
            session=session,
            scores=scores,
            metric_labels=metric_labels,
        )
        if error:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'suggestion': text})
