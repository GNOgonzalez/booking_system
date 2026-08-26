"""Staff API — manage teachers, schedules, classes, and studio settings."""

from django.contrib.auth import get_user_model
from rest_framework import generics, status
from rest_framework.fields import DateTimeField
from rest_framework.response import Response
from rest_framework.views import APIView

from scheduling.api.permissions import IsStaff
from scheduling.api.serializers import (
    AvailabilityBlockSerializer,
    ClassOfferingOptionSerializer,
    ClassOfferingSerializer,
    MembershipPlanSerializer,
    SessionSerializer,
    SpecialAvailabilitySerializer,
    StaffBookingCancelSerializer,
    StaffMembershipGrantSerializer,
    StaffMembershipUpdateSerializer,
    StaffPasswordResetSerializer,
    StaffUserCreateSerializer,
    StaffUserUpdateSerializer,
    StudentOptionSerializer,
    TeacherOptionSerializer,
)
from scheduling.models import (
    AvailabilityBlock,
    Booking,
    ClassOffering,
    MembershipPlan,
    Profile,
    Session,
    SpecialAvailability,
)
from scheduling.services.availability import (
    request_wants_special_availability,
    resolve_session_availability,
    session_within_availability,
)
from scheduling.services.meetings import create_meeting_link
from scheduling.services.membership_admin import (
    adjust_tickets,
    grant_membership,
    student_membership_overview,
    update_membership,
)
from scheduling.services.payments import payment_settings_status
from scheduling.services.reports import staff_reports
from scheduling.services.sessions import cancel_session, sessions_for_list, update_session
from scheduling.services.staff import (
    get_teacher,
    list_teachers,
    staff_cancel_booking,
    staff_reset_password,
)
from scheduling.services.staff_alerts import list_staff_alerts, mark_alerts_read
from scheduling.services.staff_audit import list_staff_actions
from scheduling.services.users import (
    create_studio_user,
    get_student,
    list_students,
    update_user_account,
)

User = get_user_model()


class StaffTeacherListView(generics.ListAPIView):
    permission_classes = [IsStaff]
    serializer_class = TeacherOptionSerializer

    def get_queryset(self):
        return list_teachers()

    def post(self, request):
        """Staff creates a new teacher account."""
        serializer = StaffUserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        teacher, error = create_studio_user(
            role='teacher',
            actor=request.user,
            **serializer.validated_data,
        )
        if error:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
        return Response(TeacherOptionSerializer(teacher).data, status=status.HTTP_201_CREATED)


class StaffOverallScheduleView(generics.ListAPIView):
    """All sessions across teachers — studio-wide schedule for staff."""

    permission_classes = [IsStaff]
    serializer_class = SessionSerializer

    def get_queryset(self):
        return sessions_for_list(
            Session.objects.filter(teacher__groups__name='teacher').order_by('start_time'),
        )


class StaffTeacherMixin:
    permission_classes = [IsStaff]

    def get_teacher(self):
        teacher = get_teacher(self.kwargs['teacher_id'])
        if teacher is None:
            return None
        return teacher

    def get_serializer_context(self):
        context = super().get_serializer_context()
        teacher = self.get_teacher()
        if teacher is not None:
            context['acting_teacher'] = teacher
        return context

    def teacher_or_404_response(self):
        if self.get_teacher() is None:
            return Response({'detail': 'Teacher not found.'}, status=status.HTTP_404_NOT_FOUND)
        return None


class StaffTeacherSessionListCreateView(StaffTeacherMixin, generics.ListCreateAPIView):
    serializer_class = SessionSerializer

    def get_queryset(self):
        teacher = self.get_teacher()
        if teacher is None:
            return Session.objects.none()
        qs = Session.objects.filter(teacher=teacher)
        student_id = self.request.query_params.get('student')
        if student_id:
            qs = qs.filter(
                bookings__student_id=student_id,
                bookings__status='confirmed',
            ).distinct()
        return sessions_for_list(qs)

    def list(self, request, *args, **kwargs):
        if self.get_teacher() is None:
            return Response({'detail': 'Teacher not found.'}, status=status.HTTP_404_NOT_FOUND)
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        teacher = self.get_teacher()
        if teacher is None:
            return Response({'detail': 'Teacher not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        start = serializer.validated_data['start_time']
        end = serializer.validated_data['end_time']
        ok, detail = resolve_session_availability(
            teacher,
            start,
            end,
            acting_user=request.user,
            add_special=request_wants_special_availability(request),
            special_note=(request.data.get('special_availability_note') or '').strip(),
            staff_message=True,
        )
        if not ok:
            return Response(
                {'detail': detail, 'code': 'outside_availability'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        session = serializer.save(teacher=teacher, status='open')
        session.meeting_url = create_meeting_link(session)
        session.save(update_fields=['meeting_url'])
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class StaffTeacherSessionAvailabilityCheckView(StaffTeacherMixin, APIView):
    def get(self, request, teacher_id):
        teacher = self.get_teacher()
        if teacher is None:
            return Response({'detail': 'Teacher not found.'}, status=status.HTTP_404_NOT_FOUND)
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
        available = session_within_availability(teacher, start, end)
        return Response({'available': available})


class StaffTeacherSessionDetailView(StaffTeacherMixin, APIView):
    def get_session(self, teacher, session_id):
        return Session.objects.filter(pk=session_id, teacher=teacher).first()

    def patch(self, request, teacher_id, session_id):
        teacher = self.get_teacher()
        if teacher is None:
            return Response({'detail': 'Teacher not found.'}, status=status.HTTP_404_NOT_FOUND)
        session = self.get_session(teacher, session_id)
        if session is None:
            return Response({'detail': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = SessionSerializer(
            session,
            data=request.data,
            partial=True,
            context={'request': request, 'acting_teacher': teacher},
        )
        serializer.is_valid(raise_exception=True)
        start = serializer.validated_data.get('start_time', session.start_time)
        end = serializer.validated_data.get('end_time', session.end_time)
        if 'start_time' in serializer.validated_data or 'end_time' in serializer.validated_data:
            if not session_within_availability(teacher, start, end):
                return Response(
                    {'detail': 'Session time is outside teacher availability.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        ok, error = update_session(
            session,
            teacher,
            class_offering=serializer.validated_data.get('class_offering'),
            start_time=serializer.validated_data.get('start_time'),
            end_time=serializer.validated_data.get('end_time'),
            capacity=serializer.validated_data.get('capacity'),
        )
        if not ok:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
        session.refresh_from_db()
        return Response(SessionSerializer(session).data)

    def delete(self, request, teacher_id, session_id):
        teacher = self.get_teacher()
        if teacher is None:
            return Response({'detail': 'Teacher not found.'}, status=status.HTTP_404_NOT_FOUND)
        session = self.get_session(teacher, session_id)
        if session is None:
            return Response({'detail': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)
        ok, error = cancel_session(session, teacher)
        if not ok:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
        return Response(SessionSerializer(session).data)


class StaffTeacherSessionStudentsView(StaffTeacherMixin, APIView):
    def get(self, request, teacher_id, session_id):
        teacher = self.get_teacher()
        if teacher is None:
            return Response({'detail': 'Teacher not found.'}, status=status.HTTP_404_NOT_FOUND)

        session = Session.objects.filter(pk=session_id, teacher=teacher).first()
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


class StaffTeacherClassListCreateView(StaffTeacherMixin, generics.ListCreateAPIView):
    serializer_class = ClassOfferingSerializer

    def get_queryset(self):
        teacher = self.get_teacher()
        if teacher is None:
            return ClassOffering.objects.none()
        return ClassOffering.objects.filter(teacher=teacher).prefetch_related('topics').order_by('-is_active', 'subject')

    def list(self, request, *args, **kwargs):
        if self.get_teacher() is None:
            return Response({'detail': 'Teacher not found.'}, status=status.HTTP_404_NOT_FOUND)
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        if self.get_teacher() is None:
            return Response({'detail': 'Teacher not found.'}, status=status.HTTP_404_NOT_FOUND)
        return super().create(request, *args, **kwargs)


class StaffTeacherClassDetailView(StaffTeacherMixin, APIView):
    def get_offering(self, teacher, pk):
        return ClassOffering.objects.filter(pk=pk, teacher=teacher).first()

    def patch(self, request, teacher_id, pk):
        teacher = self.get_teacher()
        if teacher is None:
            return Response({'detail': 'Teacher not found.'}, status=status.HTTP_404_NOT_FOUND)
        offering = self.get_offering(teacher, pk)
        if offering is None:
            return Response({'detail': 'Class not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = ClassOfferingSerializer(
            offering,
            data=request.data,
            partial=True,
            context={'request': request, 'acting_teacher': teacher},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, teacher_id, pk):
        teacher = self.get_teacher()
        if teacher is None:
            return Response({'detail': 'Teacher not found.'}, status=status.HTTP_404_NOT_FOUND)
        offering = self.get_offering(teacher, pk)
        if offering is None:
            return Response({'detail': 'Class not found.'}, status=status.HTTP_404_NOT_FOUND)
        offering.is_active = False
        offering.save(update_fields=['is_active'])
        return Response(ClassOfferingSerializer(offering).data)


class StaffTeacherAvailabilityListCreateView(StaffTeacherMixin, generics.ListCreateAPIView):
    serializer_class = AvailabilityBlockSerializer

    def get_queryset(self):
        teacher = self.get_teacher()
        if teacher is None:
            return AvailabilityBlock.objects.none()
        return AvailabilityBlock.objects.filter(teacher=teacher)

    def list(self, request, *args, **kwargs):
        if self.get_teacher() is None:
            return Response({'detail': 'Teacher not found.'}, status=status.HTTP_404_NOT_FOUND)
        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(teacher=self.get_teacher())


class StaffTeacherAvailabilityUpdateDeleteView(StaffTeacherMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AvailabilityBlockSerializer
    http_method_names = ['patch', 'put', 'delete', 'options', 'head']

    def get_queryset(self):
        teacher = self.get_teacher()
        if teacher is None:
            return AvailabilityBlock.objects.none()
        return AvailabilityBlock.objects.filter(teacher=teacher)


class StaffTeacherSpecialAvailabilityListCreateView(StaffTeacherMixin, generics.ListCreateAPIView):
    serializer_class = SpecialAvailabilitySerializer

    def get_queryset(self):
        teacher = self.get_teacher()
        if teacher is None:
            return SpecialAvailability.objects.none()
        return SpecialAvailability.objects.filter(teacher=teacher)

    def list(self, request, *args, **kwargs):
        if self.get_teacher() is None:
            return Response({'detail': 'Teacher not found.'}, status=status.HTTP_404_NOT_FOUND)
        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(teacher=self.get_teacher())


class StaffTeacherSchedulingSlotsView(StaffTeacherMixin, APIView):
    def get(self, request, teacher_id):
        from scheduling.services.scheduling_slots import scheduling_slot_options

        teacher = self.get_teacher()
        if teacher is None:
            return Response({'detail': 'Teacher not found.'}, status=status.HTTP_404_NOT_FOUND)
        days = min(int(request.query_params.get('days', 28)), 90)
        duration = min(max(int(request.query_params.get('duration_minutes', 60)), 15), 240)
        step = min(max(int(request.query_params.get('step_minutes', 30)), 15), 120)
        slots = scheduling_slot_options(
            teacher,
            days=days,
            duration_minutes=duration,
            step_minutes=step,
        )
        return Response({'slots': slots})


class StaffTeacherSpecialAvailabilityUpdateDeleteView(StaffTeacherMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SpecialAvailabilitySerializer
    http_method_names = ['patch', 'put', 'delete', 'options', 'head']

    def get_queryset(self):
        teacher = self.get_teacher()
        if teacher is None:
            return SpecialAvailability.objects.none()
        return SpecialAvailability.objects.filter(teacher=teacher)


class StaffTeacherStudentListView(StaffTeacherMixin, generics.ListAPIView):
    serializer_class = StudentOptionSerializer

    def get_queryset(self):
        if self.get_teacher() is None:
            return User.objects.none()
        return User.objects.filter(groups__name='student', is_active=True).order_by('username')

    def list(self, request, *args, **kwargs):
        if self.get_teacher() is None:
            return Response({'detail': 'Teacher not found.'}, status=status.HTTP_404_NOT_FOUND)
        return super().list(request, *args, **kwargs)


class StaffTeacherPermissionsView(StaffTeacherMixin, APIView):
    """Grant or revoke teacher capabilities (schedule, classes, availability, reports)."""

    def get(self, request, teacher_id):
        teacher = self.get_teacher()
        if teacher is None:
            return Response({'detail': 'Teacher not found.'}, status=status.HTTP_404_NOT_FOUND)
        from scheduling.services.teacher_permissions import TEACHER_PERMISSION_DEFS, permissions_for_teacher

        perms = permissions_for_teacher(teacher)
        return Response([
            {
                'key': key,
                'label': label,
                'description': desc,
                'is_enabled': perms[key],
            }
            for key, label, desc in TEACHER_PERMISSION_DEFS
        ])

    def patch(self, request, teacher_id):
        teacher = self.get_teacher()
        if teacher is None:
            return Response({'detail': 'Teacher not found.'}, status=status.HTTP_404_NOT_FOUND)
        from scheduling.services.teacher_permissions import TEACHER_PERMISSION_DEFS, set_teacher_permissions

        updates = request.data.get('permissions', request.data)
        if not isinstance(updates, dict):
            return Response({'detail': 'Expected a permissions object.'}, status=status.HTTP_400_BAD_REQUEST)
        perms = set_teacher_permissions(teacher, updates)
        return Response([
            {
                'key': key,
                'label': label,
                'description': desc,
                'is_enabled': perms[key],
            }
            for key, label, desc in TEACHER_PERMISSION_DEFS
        ])


class StaffCreateClassView(APIView):
    """Staff creates a teachable class for any teacher."""

    permission_classes = [IsStaff]

    def post(self, request):
        teacher = get_teacher(request.data.get('teacher'))
        if teacher is None:
            return Response({'detail': 'Teacher not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = ClassOfferingSerializer(
            data=request.data,
            context={'request': request, 'acting_teacher': teacher},
        )
        serializer.is_valid(raise_exception=True)
        offering = serializer.save(teacher=teacher)
        return Response(ClassOfferingSerializer(offering).data, status=status.HTTP_201_CREATED)


class StaffTeacherDetailView(StaffTeacherMixin, APIView):
    def patch(self, request, teacher_id):
        teacher = self.get_teacher()
        if teacher is None:
            return Response({'detail': 'Teacher not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = StaffUserUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ok, error = update_user_account(
            teacher,
            is_active=serializer.validated_data.get('is_active'),
            display_name=serializer.validated_data.get('display_name'),
        )
        if not ok:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
        return Response(TeacherOptionSerializer(teacher).data)


class StaffStudentListView(generics.ListAPIView):
    permission_classes = [IsStaff]
    serializer_class = StudentOptionSerializer

    def get_queryset(self):
        return list_students()

    def post(self, request):
        """Staff creates a student who signed up in person."""
        serializer = StaffUserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        student, error = create_studio_user(
            role='student',
            actor=request.user,
            **serializer.validated_data,
        )
        if error:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
        return Response(StudentOptionSerializer(student).data, status=status.HTTP_201_CREATED)


class StaffPasswordResetMixin:
    """Staff sets a temporary password for a teacher or student."""

    permission_classes = [IsStaff]
    url_kwarg = None

    def get_target(self, user_id):
        raise NotImplementedError

    def post(self, request, **kwargs):
        target = self.get_target(kwargs[self.url_kwarg])
        if target is None:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = StaffPasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ok, error = staff_reset_password(
            request.user,
            target,
            serializer.validated_data['password'],
            note=serializer.validated_data.get('note', ''),
        )
        if not ok:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'detail': f'Password updated for {target.username}. Share it and ask them to change it.',
        })


class StaffTeacherPasswordResetView(StaffPasswordResetMixin, APIView):
    url_kwarg = 'teacher_id'

    def get_target(self, user_id):
        return get_teacher(user_id)


class StaffStudentPasswordResetView(StaffPasswordResetMixin, APIView):
    url_kwarg = 'student_id'

    def get_target(self, user_id):
        return get_student(user_id)


class StaffStudentMembershipView(APIView):
    """Read a student's membership state and comp / record a plan for them."""

    permission_classes = [IsStaff]

    def get(self, request, student_id):
        student = get_student(student_id)
        if student is None:
            return Response({'detail': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)
        payload = student_membership_overview(student)
        payload['plans'] = MembershipPlanSerializer(
            MembershipPlan.objects.filter(is_active=True).prefetch_related('allowed_classes'),
            many=True,
        ).data
        payload['recent_actions'] = list_staff_actions(limit=10, target_user=student)
        return Response(payload)

    def post(self, request, student_id):
        student = get_student(student_id)
        if student is None:
            return Response({'detail': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = StaffMembershipGrantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload, error = grant_membership(
            request.user,
            student,
            plan_id=serializer.validated_data['plan_id'],
            months=serializer.validated_data.get('months', 1),
            amount_cents=serializer.validated_data.get('amount_cents', 0),
            note=serializer.validated_data.get('note', ''),
        )
        if error:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
        return Response(payload, status=status.HTTP_201_CREATED)


class StaffStudentMembershipDetailView(APIView):
    """Adjust tickets, cancel, reactivate, or extend one membership."""

    permission_classes = [IsStaff]

    def patch(self, request, student_id, membership_id):
        student = get_student(student_id)
        if student is None:
            return Response({'detail': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = StaffMembershipUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        note = data.get('note', '')

        if 'tickets_delta' in data:
            payload, error = adjust_tickets(
                request.user,
                student,
                membership_id=membership_id,
                delta=data['tickets_delta'],
                note=note,
            )
        else:
            payload, error = update_membership(
                request.user,
                student,
                membership_id=membership_id,
                is_active=data.get('is_active'),
                valid_until=data.get('valid_until'),
                extend_days=data.get('extend_days'),
                note=note,
            )
        if error:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
        return Response(payload)


class StaffBookingCancelView(APIView):
    """Staff cancels a student's booking, with or without refunding the ticket."""

    permission_classes = [IsStaff]

    def post(self, request, booking_id):
        serializer = StaffBookingCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload, error = staff_cancel_booking(
            request.user,
            booking_id,
            refund=serializer.validated_data.get('refund', True),
            note=serializer.validated_data.get('note', ''),
        )
        if error:
            code = (
                status.HTTP_404_NOT_FOUND
                if error == 'Booking not found.'
                else status.HTTP_400_BAD_REQUEST
            )
            return Response({'detail': error}, status=code)
        return Response(payload)


class StaffPaymentSettingsView(APIView):
    """Read-only view of how payments are configured (never returns secret keys)."""

    permission_classes = [IsStaff]

    def get(self, request):
        base_url = f'{request.scheme}://{request.get_host()}'
        return Response(payment_settings_status(base_url=base_url))


class StaffActivityLogView(APIView):
    """Audit trail of staff overrides."""

    permission_classes = [IsStaff]

    def get(self, request):
        try:
            limit = int(request.query_params.get('limit', 50))
        except (TypeError, ValueError):
            limit = 50
        return Response({'actions': list_staff_actions(limit=limit)})


class StaffStudentDetailView(APIView):
    permission_classes = [IsStaff]

    def patch(self, request, student_id):
        student = get_student(student_id)
        if student is None:
            return Response({'detail': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = StaffUserUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ok, error = update_user_account(
            student,
            is_active=serializer.validated_data.get('is_active'),
            display_name=serializer.validated_data.get('display_name'),
        )
        if not ok:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
        return Response(StudentOptionSerializer(student).data)


class StaffClassOfferingListView(generics.ListAPIView):
    """All active catalog classes — for membership plan configuration."""

    permission_classes = [IsStaff]
    serializer_class = ClassOfferingOptionSerializer

    def get_queryset(self):
        return (
            ClassOffering.objects.filter(is_active=True)
            .select_related('teacher')
            .prefetch_related('topics')
            .order_by('teacher__username', 'subject', 'level', 'focus')
        )


class StaffMembershipPlanListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsStaff]
    serializer_class = MembershipPlanSerializer

    def get_queryset(self):
        return MembershipPlan.objects.prefetch_related('allowed_classes', 'allowed_classes__teacher')


class StaffMembershipPlanDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsStaff]
    serializer_class = MembershipPlanSerializer

    def get_queryset(self):
        return MembershipPlan.objects.prefetch_related('allowed_classes', 'allowed_classes__teacher')

    def destroy(self, request, *args, **kwargs):
        plan = self.get_object()
        if plan.memberships.exists():
            return Response(
                {'detail': 'Cannot delete a plan with memberships. Deactivate it instead.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)


class StaffReportsView(APIView):
    """Studio-wide reports for staff — financials, bookings, teachers, students."""

    permission_classes = [IsStaff]

    def get(self, request):
        try:
            days = int(request.query_params.get('days', 30))
        except (TypeError, ValueError):
            days = 30
        days = max(1, min(days, 365))
        return Response(staff_reports(days=days))


class StaffAlertsView(APIView):
    """In-app staff alerts — users, membership, and financial streams."""

    permission_classes = [IsStaff]

    def get(self, request):
        try:
            limit = int(request.query_params.get('limit', 10))
        except (TypeError, ValueError):
            limit = 10
        return Response(list_staff_alerts(request.user, limit=limit))


class StaffAlertsMarkReadView(APIView):
    permission_classes = [IsStaff]

    def post(self, request):
        mark_all = bool(request.data.get('all'))
        alert_ids = request.data.get('alert_ids')
        if not mark_all and not alert_ids:
            return Response(
                {'detail': 'Provide alert_ids or all: true.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if alert_ids is not None and not isinstance(alert_ids, list):
            return Response(
                {'detail': 'alert_ids must be a list.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        marked = mark_alerts_read(
            request.user,
            alert_ids=alert_ids,
            mark_all=mark_all,
        )
        return Response({'marked': marked, **list_staff_alerts(request.user)})
