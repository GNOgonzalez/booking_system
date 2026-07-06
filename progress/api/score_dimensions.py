from django.contrib.auth import get_user_model
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from progress.api.serializers import (
    ScoreDimensionSerializer,
    StaffScoreDimensionCreateSerializer,
    StaffScoreDimensionSerializer,
)
from progress.models import ScoreDimension
from progress.services import (
    MAX_SCORE_DIMENSIONS,
    create_score_dimension,
    delete_score_dimension,
    get_score_dimensions,
    list_metric_subjects,
    list_score_dimensions_for_staff,
    reorder_score_dimensions,
)
from scheduling.api.permissions import IsStaff

User = get_user_model()

class StaffScoreDimensionListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsStaff]
    serializer_class = StaffScoreDimensionSerializer

    def get_queryset(self):
        subject = self.request.query_params.get('subject', '')
        include_inactive = self.request.query_params.get('include_inactive') == '1'
        return list_score_dimensions_for_staff(subject=subject, include_inactive=include_inactive)

    def create(self, request, *args, **kwargs):
        serializer = StaffScoreDimensionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dim, error = create_score_dimension(
            serializer.validated_data['label'],
            subject=serializer.validated_data.get('subject', ''),
            min_score=serializer.validated_data.get('min_score', 0),
            max_score=serializer.validated_data.get('max_score', 5),
        )
        if error:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            StaffScoreDimensionSerializer(dim).data,
            status=status.HTTP_201_CREATED,
        )



class StaffScoreDimensionDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsStaff]
    serializer_class = StaffScoreDimensionSerializer
    queryset = ScoreDimension.objects.filter(teacher__isnull=True)
    http_method_names = ['patch', 'put', 'delete', 'options', 'head']

    def destroy(self, request, *args, **kwargs):
        dim = self.get_object()
        ok, error = delete_score_dimension(dim)
        if not ok:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)



class StaffScoreSubjectsView(APIView):
    permission_classes = [IsStaff]

    def get(self, request):
        subjects = list_metric_subjects()
        return Response([
            {'value': '', 'label': 'All subjects (default)'},
            *[{'value': s, 'label': s} for s in subjects],
        ])



class StaffScoreDimensionReorderView(APIView):
    permission_classes = [IsStaff]

    def post(self, request):
        subject = request.data.get('subject', '')
        ordered_ids = request.data.get('order', [])
        if not isinstance(ordered_ids, list) or not ordered_ids:
            return Response({'detail': 'Expected a non-empty order list.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            ordered_ids = [int(pk) for pk in ordered_ids]
        except (TypeError, ValueError):
            return Response({'detail': 'Order must be a list of metric IDs.'}, status=status.HTTP_400_BAD_REQUEST)
        ok, error = reorder_score_dimensions(ordered_ids, subject=subject)
        if not ok:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
        dims = list_score_dimensions_for_staff(subject=subject, include_inactive=False)
        return Response(StaffScoreDimensionSerializer(dims, many=True).data)



class StaffScoreDimensionMetaView(APIView):
    permission_classes = [IsStaff]

    def get(self, request):
        subject = request.query_params.get('subject', '')
        from progress.services import active_count_for_scope

        active = active_count_for_scope(subject=subject)
        return Response({
            'max': MAX_SCORE_DIMENSIONS,
            'active': active,
            'remaining': max(0, MAX_SCORE_DIMENSIONS - active),
        })



class ScoreDimensionListView(generics.ListAPIView):
    """Active score column labels for forms and charts."""

    permission_classes = [IsAuthenticated]
    serializer_class = ScoreDimensionSerializer

    def get_queryset(self):
        subject = self.request.query_params.get('subject', '')
        teacher = self.request.user if self.request.user.groups.filter(name='teacher').exists() else None
        return get_score_dimensions(teacher, subject)


