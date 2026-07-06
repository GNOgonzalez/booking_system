"""Google OAuth endpoints — connect/status/disconnect via API, callback via browser."""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponseRedirect
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from integrations.google.oauth import (
    GoogleOAuthError,
    build_authorization_url,
    connection_status,
    disconnect,
    exchange_code,
    store_credential,
    user_id_from_state,
)
from scheduling.api.permissions import IsTeacherOrStaff

User = get_user_model()


def _frontend_profile_url(result):
    origins = getattr(settings, 'CORS_ALLOWED_ORIGINS', []) or []
    base = (origins[0] if origins else 'http://127.0.0.1:5173').rstrip('/')
    return f'{base}/profile?google={result}'


class GoogleConnectView(APIView):
    """Return the Google consent URL for the current teacher/staff user."""

    permission_classes = [IsTeacherOrStaff]

    def get(self, request):
        try:
            url = build_authorization_url(request.user)
        except GoogleOAuthError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response({'authorization_url': url})


class GoogleStatusView(APIView):
    permission_classes = [IsTeacherOrStaff]

    def get(self, request):
        return Response(connection_status(request.user))


class GoogleDisconnectView(APIView):
    permission_classes = [IsTeacherOrStaff]

    def post(self, request):
        disconnect(request.user)
        return Response(connection_status(request.user))


def google_oauth_callback(request):
    """Browser redirect from Google — no JWT; user identified via signed state."""
    error = request.GET.get('error')
    if error:
        return HttpResponseRedirect(_frontend_profile_url('denied'))

    code = request.GET.get('code', '')
    state = request.GET.get('state', '')
    if not code or not state:
        return HttpResponseRedirect(_frontend_profile_url('error'))

    try:
        user_id = user_id_from_state(state)
        user = User.objects.filter(pk=user_id, is_active=True).first()
        if user is None:
            raise GoogleOAuthError('Unknown user.')
        token_data = exchange_code(code)
        store_credential(user, token_data)
    except GoogleOAuthError:
        return HttpResponseRedirect(_frontend_profile_url('error'))

    return HttpResponseRedirect(_frontend_profile_url('connected'))
