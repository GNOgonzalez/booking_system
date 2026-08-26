"""DRF views for studio class roadmap catalog."""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from scheduling.api.permissions import IsStaff
from scheduling.services.class_catalog import (
    CATALOG_KINDS,
    bulk_add_catalog_topics,
    catalog_node_children,
    catalog_node_usage,
    catalog_tree,
    create_catalog_focus,
    create_catalog_level,
    create_catalog_subject,
    delete_catalog_node,
    get_catalog_node,
    rename_catalog_node,
    set_catalog_node_active,
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


class StaffClassCatalogNodeView(APIView):
    """Rename, deactivate, or remove one roadmap entry."""

    permission_classes = [IsStaff]

    def get(self, request, kind, node_id):
        node = self._node_or_none(kind, node_id)
        if node is None:
            return Response({'detail': 'Roadmap entry not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({
            'kind': kind,
            'id': node.id,
            'usage': catalog_node_usage(kind, node),
            'children': catalog_node_children(kind, node),
        })

    def patch(self, request, kind, node_id):
        if kind not in CATALOG_KINDS:
            return Response({'detail': 'Unknown roadmap entry type.'}, status=status.HTTP_400_BAD_REQUEST)

        name = request.data.get('name')
        is_active = request.data.get('is_active')
        if name is None and is_active is None:
            return Response(
                {'detail': 'Provide name and/or is_active.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        summary = None
        if name is not None:
            summary, error = rename_catalog_node(kind, node_id, name)
            if error:
                return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
        if is_active is not None:
            summary, error = set_catalog_node_active(kind, node_id, is_active)
            if error:
                return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
        return Response(summary)

    def delete(self, request, kind, node_id):
        if kind not in CATALOG_KINDS:
            return Response({'detail': 'Unknown roadmap entry type.'}, status=status.HTTP_400_BAD_REQUEST)
        summary, error = delete_catalog_node(kind, node_id)
        if error:
            code = (
                status.HTTP_404_NOT_FOUND
                if error == 'Roadmap entry not found.'
                else status.HTTP_400_BAD_REQUEST
            )
            return Response({'detail': error}, status=code)
        return Response(summary)

    @staticmethod
    def _node_or_none(kind, node_id):
        if kind not in CATALOG_KINDS:
            return None
        return get_catalog_node(kind, node_id)


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
