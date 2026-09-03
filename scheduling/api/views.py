import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import generics, status
from rest_framework.fields import DateTimeField
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from scheduling.api.permissions import IsStudent, IsTeacher
from scheduling.api.serializers import (
    AvailabilityBlockSerializer,
    BookingCreateSerializer,
    BookingSerializer,
    ClassOfferingSerializer,
    CurriculumItemSerializer,
    MembershipPlanPublicSerializer,
    MembershipPurchaseSerializer,
    MembershipSerializer,
    MessageSerializer,
    MeUpdateSerializer,
    PasswordChangeSerializer,
    SessionSerializer,
    SpecialAvailabilitySerializer,
    StudentOptionSerializer,
    serialize_me,
)
from scheduling.models import (
    AvailabilityBlock,
    Booking,
    ClassOffering,
    CurriculumItem,
    MembershipPlan,
    Message,
    Profile,
    Session,
    SpecialAvailability,
)
from scheduling.services.availability import (
    request_wants_special_availability,
    resolve_session_availability,
    session_within_availability,
)
from scheduling.services.booking import booking_block_reason, cancel_booking, create_booking
from scheduling.services.meetings import attach_meeting_link
from scheduling.services.membership import (
    active_memberships_for,
    allowed_class_ids_for_user,
    total_tickets_remaining,
)
from scheduling.services.payments import (
    get_available_plans,
    get_payment_status,
    payment_mode,
    purchase_membership,
)
from scheduling.services.roster import roster_students_for_teacher
from scheduling.services.sessions import cancel_session, sessions_for_list, update_session
from scheduling.services.student_home import student_home
from scheduling.services.teacher_permissions import (
    TEACHER_PERMISSION_DEFS,
    permission_denied_response,
    permissions_for_teacher,
    teacher_can,
)

logger = logging.getLogger(__name__)

User = get_user_model()


class TeacherStudentListView(generics.ListAPIView):
    """Students this teacher may manage (assigned or already taught)."""

    permission_classes = [IsTeacher]
    serializer_class = StudentOptionSerializer

    def get_queryset(self):
        return roster_students_for_teacher(self.request.user)


class OpenSessionListView(generics.ListAPIView):
    permission_classes = [IsStudent]
    serializer_class = SessionSerializer

    def get_queryset(self):
        qs = Session.objects.filter(
            status='open',
            start_time__gte=timezone.now(),
            teacher__is_active=True,
        )
        allowed_ids = allowed_class_ids_for_user(self.request.user)
        if allowed_ids is not None:
            if not allowed_ids:
                return qs.none()
            qs = qs.filter(
                Q(class_offering__isnull=True) | Q(class_offering_id__in=allowed_ids),
            )
        booked = Booking.objects.filter(
            student=self.request.user,
            session_id=OuterRef('pk'),
            status='confirmed',
        )
        return sessions_for_list(qs).annotate(student_booked=Exists(booked))


class MyBookingListView(generics.ListAPIView):
    permission_classes = [IsStudent]
    serializer_class = BookingSerializer

    def get_queryset(self):
        return (
            Booking.objects.filter(student=self.request.user, status='confirmed')
            .select_related('session', 'session__teacher', 'session__class_offering', 'session__class_topic')
        )


class BookingCreateView(APIView):
    permission_classes = [IsStudent]

    def post(self, request):
        serializer = BookingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = Session.objects.filter(pk=serializer.validated_data['session_id']).first()
        if session is None:
            return Response({'detail': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)
        result = create_booking(request.user, session)
        if result:
            booking, notifications = result
            data = BookingSerializer(booking).data
            data['confirmation_email_sent'] = notifications['student_email_sent']
            data['confirmation_email'] = request.user.email or ''
            return Response(data, status=status.HTTP_201_CREATED)
        reason = booking_block_reason(request.user, session) or 'Booking not allowed.'
        return Response({'detail': reason}, status=status.HTTP_400_BAD_REQUEST)


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
        qs = Session.objects.filter(teacher=self.request.user)
        student_id = self.request.query_params.get('student')
        if student_id:
            qs = qs.filter(
                bookings__student_id=student_id,
                bookings__status='confirmed',
            ).distinct()
        return sessions_for_list(qs)

    def create(self, request, *args, **kwargs):
        if not teacher_can(request.user, 'manage_schedule'):
            return permission_denied_response('manage_schedule')
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        start = serializer.validated_data['start_time']
        end = serializer.validated_data['end_time']
        ok, detail = resolve_session_availability(
            request.user,
            start,
            end,
            acting_user=request.user,
            add_special=request_wants_special_availability(request),
            special_note=(request.data.get('special_availability_note') or '').strip(),
        )
        if not ok:
            return Response(
                {'detail': detail, 'code': 'outside_availability'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        session = serializer.save(teacher=self.request.user, status='open')
        attach_meeting_link(session)


class TeacherSessionDetailView(APIView):
    permission_classes = [IsTeacher]

    def get_session(self, request, session_id):
        return Session.objects.filter(pk=session_id, teacher=request.user).first()

    def patch(self, request, session_id):
        if not teacher_can(request.user, 'manage_schedule'):
            return permission_denied_response('manage_schedule')
        session = self.get_session(request, session_id)
        if session is None:
            return Response({'detail': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = SessionSerializer(
            session,
            data=request.data,
            partial=True,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        start = serializer.validated_data.get('start_time', session.start_time)
        end = serializer.validated_data.get('end_time', session.end_time)
        if 'start_time' in serializer.validated_data or 'end_time' in serializer.validated_data:
            if not session_within_availability(request.user, start, end):
                return Response(
                    {'detail': 'Session time is outside your availability.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        ok, error = update_session(
            session,
            request.user,
            class_offering=serializer.validated_data.get('class_offering'),
            start_time=serializer.validated_data.get('start_time'),
            end_time=serializer.validated_data.get('end_time'),
            capacity=serializer.validated_data.get('capacity'),
        )
        if not ok:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
        session.refresh_from_db()
        return Response(SessionSerializer(session).data)

    def delete(self, request, session_id):
        if not teacher_can(request.user, 'manage_schedule'):
            return permission_denied_response('manage_schedule')
        session = self.get_session(request, session_id)
        if session is None:
            return Response({'detail': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)
        ok, error = cancel_session(session, request.user)
        if not ok:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
        return Response(SessionSerializer(session).data)


class TeacherSessionStudentsView(APIView):
    """Confirmed students for one of the teacher's sessions (for report dropdowns)."""

    permission_classes = [IsTeacher]

    def get(self, request, session_id):
        session = Session.objects.filter(pk=session_id, teacher=request.user).first()
        if session is None:
            return Response({'detail': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)

        bookings = Booking.objects.filter(
            session=session,
            status='confirmed',
        ).select_related('student').order_by('student__username')

        students = []
        seen = set()
        for booking in bookings:
            user = booking.student
            if user.id in seen:
                continue
            seen.add(user.id)
            profile = Profile.objects.filter(user=user).first()
            if profile and profile.display_name:
                label = f"{profile.display_name} ({user.username})"
            else:
                label = user.username
            students.append({'id': user.id, 'username': user.username, 'label': label})
        return Response(students)


class TeacherAvailabilityListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsTeacher]
    serializer_class = AvailabilityBlockSerializer

    def get_queryset(self):
        return AvailabilityBlock.objects.filter(teacher=self.request.user)

    def perform_create(self, serializer):
        if not teacher_can(self.request.user, 'manage_availability'):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('You do not have permission to set availability.')
        serializer.save(teacher=self.request.user)


class TeacherAvailabilityUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsTeacher]
    serializer_class = AvailabilityBlockSerializer
    http_method_names = ['patch', 'put', 'delete', 'options', 'head']

    def get_queryset(self):
        return AvailabilityBlock.objects.filter(teacher=self.request.user)

    def update(self, request, *args, **kwargs):
        if not teacher_can(request.user, 'manage_availability'):
            return permission_denied_response('manage_availability')
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not teacher_can(request.user, 'manage_availability'):
            return permission_denied_response('manage_availability')
        return super().destroy(request, *args, **kwargs)


class TeacherSpecialAvailabilityUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsTeacher]
    serializer_class = SpecialAvailabilitySerializer
    http_method_names = ['patch', 'put', 'delete', 'options', 'head']

    def get_queryset(self):
        return SpecialAvailability.objects.filter(teacher=self.request.user)

    def update(self, request, *args, **kwargs):
        if not teacher_can(request.user, 'manage_availability'):
            return permission_denied_response('manage_availability')
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not teacher_can(request.user, 'manage_availability'):
            return permission_denied_response('manage_availability')
        return super().destroy(request, *args, **kwargs)


class TeacherSpecialAvailabilityListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsTeacher]
    serializer_class = SpecialAvailabilitySerializer

    def get_queryset(self):
        return SpecialAvailability.objects.filter(teacher=self.request.user)

    def perform_create(self, serializer):
        if not teacher_can(self.request.user, 'manage_availability'):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('You do not have permission to set availability.')
        serializer.save(teacher=self.request.user)


class TeacherSessionAvailabilityCheckView(APIView):
    """Preflight check — whether a session window fits weekly or special availability."""

    permission_classes = [IsTeacher]

    def get(self, request):
        start_raw = request.query_params.get('start_time')
        end_raw = request.query_params.get('end_time')
        if not start_raw or not end_raw:
            return Response(
                {'detail': 'start_time and end_time are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        field = DateTimeField()
        try:
            start = field.to_internal_value(start_raw)
            end = field.to_internal_value(end_raw)
        except Exception:
            return Response(
                {'detail': 'Invalid start_time or end_time.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if end <= start:
            return Response(
                {'detail': 'end_time must be after start_time.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        available = session_within_availability(request.user, start, end)
        return Response({'available': available})


class TeacherSchedulingSlotsView(APIView):
    """Upcoming bookable slots inside the teacher's availability windows."""

    permission_classes = [IsTeacher]

    def get(self, request):
        from scheduling.services.scheduling_slots import scheduling_slot_options

        days = min(int(request.query_params.get('days', 28)), 90)
        duration = min(max(int(request.query_params.get('duration_minutes', 60)), 15), 240)
        step = min(max(int(request.query_params.get('step_minutes', 30)), 15), 120)
        slots = scheduling_slot_options(
            request.user,
            days=days,
            duration_minutes=duration,
            step_minutes=step,
        )
        return Response({'slots': slots})


class TeacherClassOfferingListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsTeacher]
    serializer_class = ClassOfferingSerializer

    def get_queryset(self):
        return ClassOffering.objects.filter(teacher=self.request.user).prefetch_related('topics').order_by('-is_active', 'subject')

    def perform_create(self, serializer):
        if not teacher_can(self.request.user, 'manage_classes'):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('You do not have permission to manage classes.')
        serializer.save(teacher=self.request.user)


class TeacherClassOfferingDetailView(APIView):
    permission_classes = [IsTeacher]

    def get_offering(self, request, pk):
        return ClassOffering.objects.filter(pk=pk, teacher=request.user).first()

    def patch(self, request, pk):
        if not teacher_can(request.user, 'manage_classes'):
            return permission_denied_response('manage_classes')
        offering = self.get_offering(request, pk)
        if offering is None:
            return Response({'detail': 'Class not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = ClassOfferingSerializer(
            offering,
            data=request.data,
            partial=True,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        if not teacher_can(request.user, 'manage_classes'):
            return permission_denied_response('manage_classes')
        offering = self.get_offering(request, pk)
        if offering is None:
            return Response({'detail': 'Class not found.'}, status=status.HTTP_404_NOT_FOUND)
        offering.is_active = False
        offering.save(update_fields=['is_active'])
        return Response(ClassOfferingSerializer(offering).data)


class TeacherPermissionsView(APIView):
    """Current teacher's capability flags (read-only for teachers)."""

    permission_classes = [IsTeacher]

    def get(self, request):
        perms = permissions_for_teacher(request.user)
        defs = [
            {'key': key, 'label': label, 'description': desc, 'is_enabled': perms[key]}
            for key, label, desc in TEACHER_PERMISSION_DEFS
        ]
        return Response(defs)


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


class MarkdownPreviewView(APIView):
    """Server-rendered preview so client display always matches publish rules."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from scheduling.services.markdown import render_safe_markdown

        body = request.data.get('body', '')
        if not isinstance(body, str):
            return Response({'detail': 'body must be a string.'}, status=status.HTTP_400_BAD_REQUEST)
        if len(body) > 50000:
            return Response({'detail': 'Preview is limited to 50,000 characters.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'html': render_safe_markdown(body)})


class MeOnboardingView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from scheduling.services.onboarding import onboarding_for_user

        return Response(onboarding_for_user(request.user))

    def patch(self, request):
        from scheduling.services.onboarding import dismiss_onboarding, onboarding_for_user

        if request.data.get('dismissed'):
            return Response(dismiss_onboarding(request.user))
        return Response(onboarding_for_user(request.user))


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
        memberships = active_memberships_for(request.user)
        if not memberships:
            return Response({'active': False, 'memberships': [], 'tickets_remaining': 0})
        serialized = MembershipSerializer(memberships, many=True).data
        primary = serialized[0]
        return Response({
            'active': True,
            'memberships': serialized,
            'tickets_remaining': total_tickets_remaining(request.user),
            **primary,
        })

    def post(self, request):
        serializer = MembershipPurchaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership, error = purchase_membership(
            request.user,
            plan_id=serializer.validated_data['plan_id'],
            months=serializer.validated_data['months'],
            membership_id=serializer.validated_data.get('membership_id'),
        )
        if error:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
        return Response(MembershipSerializer(membership).data, status=status.HTTP_201_CREATED)


class StudentHomeView(APIView):
    """Aggregated snapshot for the student home dashboard."""

    permission_classes = [IsStudent]

    def get(self, request):
        return Response(student_home(request.user))


class MembershipPlanCatalogView(generics.ListAPIView):
    """Active membership plans students can purchase."""

    permission_classes = [IsStudent]
    serializer_class = MembershipPlanPublicSerializer

    def get_queryset(self):
        return get_available_plans()


class MembershipPaymentConfigView(APIView):
    """How payments run in this environment (mock vs Stripe)."""

    permission_classes = [IsStudent]

    def get(self, request):
        from integrations.stripe.client import stripe_enabled
        return Response({
            'mode': payment_mode(),
            'publishable_key': settings.STRIPE.get('PUBLISHABLE_KEY', '') or None,
            'checkout_available': stripe_enabled(),
            'webhook_configured': bool(settings.STRIPE.get('WEBHOOK_SECRET', '')),
        })


class MembershipCheckoutView(APIView):
    """Start Stripe Checkout for a membership purchase."""

    permission_classes = [IsStudent]

    def post(self, request):
        from integrations.stripe.checkout import create_checkout_session

        serializer = MembershipPurchaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = MembershipPlan.objects.filter(
            pk=serializer.validated_data['plan_id'],
            is_active=True,
        ).first()
        if plan is None:
            return Response({'detail': 'Unknown or inactive plan.'}, status=status.HTTP_400_BAD_REQUEST)

        result, error = create_checkout_session(
            request.user,
            plan,
            months=serializer.validated_data['months'],
            membership_id=serializer.validated_data.get('membership_id'),
            success_url=request.data.get('success_url', ''),
            cancel_url=request.data.get('cancel_url', ''),
        )
        if error:
            code = status.HTTP_400_BAD_REQUEST
            if 'Stripe API error' in error or 'Stripe did not return' in error:
                code = status.HTTP_502_BAD_GATEWAY
            elif 'not configured' in error.lower():
                code = status.HTTP_503_SERVICE_UNAVAILABLE
            return Response({'detail': error}, status=code)
        return Response(result, status=status.HTTP_201_CREATED)


class MembershipPaymentStatusView(APIView):
    """Poll Stripe checkout fulfillment for the logged-in student."""

    permission_classes = [IsStudent]

    def get(self, request, payment_id):
        result, error = get_payment_status(request.user, payment_id)
        if error:
            return Response({'detail': error}, status=status.HTTP_404_NOT_FOUND)
        return Response(result)


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(APIView):
    """Stripe webhook endpoint — no JWT; verified by Stripe-Signature."""

    authentication_classes = []
    permission_classes = [AllowAny]
    parser_classes = []  # must read raw body for signature verification

    def post(self, request):
        from integrations.stripe.webhooks import handle_webhook_request

        payload = request._request.body
        signature = request.META.get('HTTP_STRIPE_SIGNATURE', '')
        ok, message = handle_webhook_request(payload, signature)
        if not ok:
            logger.warning('Stripe webhook rejected: %s', message)
            code = status.HTTP_400_BAD_REQUEST
            if 'not configured' in message.lower():
                code = status.HTTP_503_SERVICE_UNAVAILABLE
            return Response({'detail': message}, status=code)
        return Response({'detail': message})
