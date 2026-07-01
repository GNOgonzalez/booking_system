from django.db.models import Q
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from scheduling.api.permissions import IsStudent, IsTeacher
from scheduling.api.serializers import (
    AvailabilityBlockSerializer,
    BookingCreateSerializer,
    BookingSerializer,
    ClassTypeSerializer,
    CurriculumItemSerializer,
    MembershipPurchaseSerializer,
    MembershipSerializer,
    MeUpdateSerializer,
    MessageSerializer,
    PasswordChangeSerializer,
    SessionSerializer,
    serialize_me,
)
from scheduling.models import AvailabilityBlock, Booking, ClassType, CurriculumItem, Message, Session
from scheduling.services.booking import cancel_booking, create_booking
from scheduling.services.membership import active_membership_for
from scheduling.services.payments import purchase_membership
from integrations.google.meet import create_meet_link


class OpenSessionListView(generics.ListAPIView):
    permission_classes = [IsStudent]
    serializer_class = SessionSerializer

    def get_queryset(self):
        return Session.objects.filter(
            status='open',
            start_time__gte=timezone.now(),
        )


class MyBookingListView(generics.ListAPIView):
    permission_classes = [IsStudent]
    serializer_class = BookingSerializer

    def get_queryset(self):
        return Booking.objects.filter(student=self.request.user, status='confirmed')


class BookingCreateView(APIView):
    permission_classes = [IsStudent]

    def post(self, request):
        serializer = BookingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = Session.objects.filter(pk=serializer.validated_data['session_id']).first()
        if session is None:
            return Response({'detail': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)
        if create_booking(request.user, session):
            booking = Booking.objects.filter(
                student=request.user,
                session=session,
                status='confirmed',
            ).latest('created_at')
            return Response(BookingSerializer(booking).data, status=status.HTTP_201_CREATED)
        return Response({'detail': 'Booking not allowed.'}, status=status.HTTP_400_BAD_REQUEST)


class BookingCancelView(APIView):
    permission_classes = [IsStudent]

    def post(self, request, booking_id):
        booking = Booking.objects.filter(
            pk=booking_id,
            student=request.user,
            status='confirmed',
        ).first()
        if booking is None:
            return Response({'detail': 'Booking not found.'}, status=status.HTTP_404_NOT_FOUND)
        if cancel_booking(request.user, booking):
            return Response({'detail': 'Cancelled.'})
        return Response({'detail': 'Cancel not allowed.'}, status=status.HTTP_400_BAD_REQUEST)


class TeacherSessionListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsTeacher]
    serializer_class = SessionSerializer

    def get_queryset(self):
        return Session.objects.filter(teacher=self.request.user)

    def perform_create(self, serializer):
        session = serializer.save(teacher=self.request.user, status='open')
        session.meeting_url = create_meet_link(session)
        session.save(update_fields=['meeting_url'])


class TeacherAvailabilityListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsTeacher]
    serializer_class = AvailabilityBlockSerializer

    def get_queryset(self):
        return AvailabilityBlock.objects.filter(teacher=self.request.user)

    def perform_create(self, serializer):
        serializer.save(teacher=self.request.user)


class TeacherAvailabilityDeleteView(generics.DestroyAPIView):
    permission_classes = [IsTeacher]
    serializer_class = AvailabilityBlockSerializer

    def get_queryset(self):
        return AvailabilityBlock.objects.filter(teacher=self.request.user)


class TeacherClassTypeListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsTeacher]
    serializer_class = ClassTypeSerializer

    def get_queryset(self):
        return ClassType.objects.filter(teacher=self.request.user)

    def perform_create(self, serializer):
        serializer.save(teacher=self.request.user)


class InboxListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MessageSerializer

    def get_queryset(self):
        return Message.objects.filter(recipient=self.request.user)


class CurriculumListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CurriculumItemSerializer

    def get_queryset(self):
        user = self.request.user
        qs = CurriculumItem.objects.filter(is_published=True)
        if user.groups.filter(name='teacher').exists():
            return qs.filter(Q(teacher=user) | Q(teacher__isnull=True))
        return qs


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(serialize_me(request.user))

    def patch(self, request):
        serializer = MeUpdateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serialize_me(request.user))


class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': 'Password updated.'})


class MembershipView(APIView):
    permission_classes = [IsStudent]

    def get(self, request):
        membership = active_membership_for(request.user)
        if membership is None:
            return Response({'active': False})
        data = MembershipSerializer(membership).data
        data['active'] = True
        return Response(data)

    def post(self, request):
        serializer = MembershipPurchaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership, error = purchase_membership(
            request.user,
            plan_type=serializer.validated_data['plan_type'],
            months=serializer.validated_data['months'],
        )
        if error:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
        return Response(MembershipSerializer(membership).data, status=status.HTTP_201_CREATED)
