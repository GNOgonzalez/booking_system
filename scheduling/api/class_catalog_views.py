"""DRF views for studio class roadmap catalog."""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from scheduling.api.permissions import IsStaff
from scheduling.services.class_catalog import (
    bulk_add_catalog_topics,
    catalog_tree,
    create_catalog_focus,
    create_catalog_level,
    create_catalog_subject,
)


class ClassCatalogListView(APIView):
    """Nested subject → level → focus → topics for class creation pickers."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({'subjects': catalog_tree()})


class StaffClassCatalogView(APIView):
    permission_classes = [IsStaff]

    def get(self, request):
        return Response({'subjects': catalog_tree(include_inactive=True)})

    def post(self, request):
        kind = request.data.get('kind')
        if kind == 'subject':
            subject, error = create_catalog_subject(request.data.get('name'))
            if error:
                return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
            return Response({'id': subject.id, 'name': subject.name}, status=status.HTTP_201_CREATED)
        if kind == 'level':
            level, error = create_catalog_level(request.data.get('subject_id'), request.data.get('name'))
            if error:
                return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
            return Response({'id': level.id, 'name': level.name}, status=status.HTTP_201_CREATED)
        if kind == 'focus':
            focus, error = create_catalog_focus(request.data.get('level_id'), request.data.get('name'))
            if error:
                return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
            return Response({'id': focus.id, 'name': focus.name}, status=status.HTTP_201_CREATED)
        return Response({'detail': 'Expected kind: subject, level, or focus.'}, status=status.HTTP_400_BAD_REQUEST)


class StaffClassCatalogBulkTopicsView(APIView):
    permission_classes = [IsStaff]

    def post(self, request, focus_id):
        raw = request.data.get('topics')
        if raw is None:
            raw = request.data.get('topics_text', '')
        topics, error = bulk_add_catalog_topics(focus_id, raw)
        if error:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'topics': topics}, status=status.HTTP_201_CREATED)
