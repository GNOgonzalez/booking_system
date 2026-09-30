"""Check-in APIs: staff window settings and participant check-in."""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from scheduling.api.permissions import IsStaff
from scheduling.api.serializers import SessionSerializer
from scheduling.models import Session
from scheduling.services.checkin import (
    record_check_in,
    serialize_checkin_config,
    update_checkin_config,
)
from scheduling.services.sessions import sessions_for_list


class StaffCheckInConfigView(APIView):
    permission_classes = [IsStaff]

    def get(self, request):
        return Response(serialize_checkin_config())

    def patch(self, request):
        config, error = update_checkin_config(
            check_in_opens_hours_before=request.data.get('check_in_opens_hours_before'),
            reminder_hours_before=request.data.get('reminder_hours_before'),
        )
        if error:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serialize_checkin_config(config))


class SessionCheckInView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        session = Session.objects.filter(pk=session_id).first()
        if session is None:
            return Response({'detail': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)
        row, error = record_check_in(session, request.user)
        if error:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
        refreshed = sessions_for_list(Session.objects.filter(pk=session.pk)).get()
        return Response(SessionSerializer(refreshed, context={'request': request}).data)
