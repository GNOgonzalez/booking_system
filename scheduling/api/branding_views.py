"""Public and staff branding API — sign-in name and logo."""

from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from scheduling.api.permissions import IsStaff
from scheduling.services.branding import branding_payload, update_branding


class PublicBrandingView(APIView):
    """Sign-in screen branding — no authentication required."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response(branding_payload(request=request))


class StaffBrandingView(APIView):
    permission_classes = [IsStaff]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        return Response(branding_payload(request=request))

    def patch(self, request):
        display_name = request.data.get('display_name')
        logo = request.FILES.get('logo')
        clear_logo = str(request.data.get('clear_logo', '')).lower() in ('true', '1', 'yes')
        fields = {}
        if display_name is not None:
            fields['display_name'] = display_name
        if logo is not None:
            fields['logo'] = logo
        if clear_logo:
            fields['clear_logo'] = True
        if not fields:
            return Response({'detail': 'Nothing to update.'}, status=status.HTTP_400_BAD_REQUEST)
        updated, error = update_branding(**fields)
        if error:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
        return Response(branding_payload(request=request))
