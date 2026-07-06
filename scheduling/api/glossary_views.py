"""Studio glossary API — customizable UI terminology."""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from scheduling.api.permissions import IsStaff
from scheduling.services.glossary import glossary_entries, set_glossary_terms


class GlossaryListView(APIView):
    """Current studio labels — all authenticated users (read-only)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        entries = glossary_entries()
        return Response([
            {
                'key': e['key'],
                'singular': e['singular'],
                'plural': e['plural'],
            }
            for e in entries
        ])


class StaffGlossaryView(APIView):
    """Staff edits customizable terminology."""

    permission_classes = [IsStaff]

    def get(self, request):
        return Response(glossary_entries())

    def patch(self, request):
        updates = request.data.get('terms', request.data)
        if not isinstance(updates, dict):
            return Response({'detail': 'Expected a terms object.'}, status=status.HTTP_400_BAD_REQUEST)
        entries = set_glossary_terms(updates)
        return Response(entries)
