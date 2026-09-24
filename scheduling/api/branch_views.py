"""Branch open hours: staff manage branches, teachers place classes, students see today's list."""

from datetime import date

from django.db.models import Exists, OuterRef, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.fields import DateTimeField
from rest_framework.response import Response
from rest_framework.views import APIView

from scheduling.api.permissions import IsStaff, IsStudent, IsTeacherOrStaff
from scheduling.api.serializers import SessionSerializer
from scheduling.models import Booking, ClassOffering, ClassTopic, Session
from scheduling.services.branches import (
    branch_sessions_on,
    get_branch,
    list_branches,
    open_windows,
    place_branch_class,
    save_branch,
    serialize_branch,
    serialize_window,
    set_walk_ins,
    studio_tz,
    teacher_offerings,
)
from scheduling.services.membership import allowed_class_ids_for_user
from scheduling.services.sessions import sessions_for_list
from scheduling.services.staff import get_teacher
from scheduling.services.teacher_permissions import permission_denied_response, teacher_can, user_is_staff


def _parse_day(raw):
    if not raw:
        return timezone.now().astimezone(studio_tz()).date()
    try:
        return date.fromisoformat(str(raw))
    except ValueError:
        return None


def _parse_dt(raw):
    if not raw:
        return None
    try:
        return DateTimeField().to_internal_value(raw)
    except Exception:
        return None


def _offering_payload(offering):
    return {
        'id': offering.id,
        'label': offering.display_name,
        'default_capacity': offering.default_capacity,
        'topics': [{'id': t.id, 'title': t.title} for t in offering.topics.all()],
    }


def _place_from_request(request, branch, teacher):
    """Shared class-placement body for staff and teacher endpoints."""
    data = request.data
    offering = ClassOffering.objects.filter(pk=data.get('class_offering')).first()
    topic = None
    if data.get('class_topic_id'):
        topic = ClassTopic.objects.filter(pk=data.get('class_topic_id')).first()
        if topic is None:
            return Response({'detail': 'Topic not found in this class.'}, status=status.HTTP_400_BAD_REQUEST)
    start = _parse_dt(data.get('start_time'))
    end = _parse_dt(data.get('end_time'))
    if start is None or end is None:
        return Response({'detail': 'start_time and end_time are required.'}, status=status.HTTP_400_BAD_REQUEST)
    session, err = place_branch_class(
        branch=branch,
        teacher=teacher,
        class_offering=offering,
        class_topic=topic,
        start_time=start,
        end_time=end,
        capacity=data.get('capacity'),
        accepts_walk_ins=data.get('accepts_walk_ins', False),
    )
    if err:
        return Response({'detail': err}, status=status.HTTP_400_BAD_REQUEST)
    row = sessions_for_list(Session.objects.filter(pk=session.pk)).get()
    return Response(SessionSerializer(row, context={'request': request}).data, status=status.HTTP_201_CREATED)


class StaffBranchListCreateView(APIView):
    permission_classes = [IsStaff]

    def get(self, request):
        return Response([serialize_branch(b) for b in list_branches(include_inactive=True)])

    def post(self, request):
        branch, err = save_branch(
            name=request.data.get('name'),
            is_active=request.data.get('is_active'),
            hours=request.data.get('hours'),
        )
        if err:
            return Response({'detail': err}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serialize_branch(branch), status=status.HTTP_201_CREATED)


class StaffBranchDetailView(APIView):
    permission_classes = [IsStaff]

    def get(self, request, branch_id):
        branch = get_branch(branch_id)
        if branch is None:
            return Response({'detail': 'Branch not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(serialize_branch(branch))

    def patch(self, request, branch_id):
        branch = get_branch(branch_id)
        if branch is None:
            return Response({'detail': 'Branch not found.'}, status=status.HTTP_404_NOT_FOUND)
        data = request.data
        branch, err = save_branch(
            branch=branch,
            name=data['name'] if 'name' in data else None,
            is_active=data['is_active'] if 'is_active' in data else None,
            hours=data['hours'] if 'hours' in data else None,
        )
        if err:
            return Response({'detail': err}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serialize_branch(branch))


class StaffBranchClassCreateView(APIView):
    """Staff places a class for a chosen teacher: { teacher, class_offering, class_topic_id?, start_time, end_time, capacity?, accepts_walk_ins? }."""

    permission_classes = [IsStaff]

    def post(self, request, branch_id):
        branch = get_branch(branch_id)
        if branch is None:
            return Response({'detail': 'Branch not found.'}, status=status.HTTP_404_NOT_FOUND)
        teacher = get_teacher(request.data.get('teacher'))
        if teacher is None:
            return Response({'detail': 'Teacher not found.'}, status=status.HTTP_404_NOT_FOUND)
        return _place_from_request(request, branch, teacher)


class StaffBranchTeacherOptionsView(APIView):
    """Teachers with their active offerings, for the staff add-class form."""

    permission_classes = [IsStaff]

    def get(self, request):
        from scheduling.services.staff import list_teachers

        rows = []
        for teacher in list_teachers():
            if not teacher.is_active:
                continue
            rows.append({
                'id': teacher.id,
                'username': teacher.username,
                'offerings': [_offering_payload(o) for o in teacher_offerings(teacher)],
            })
        return Response(rows)


class BranchDayView(APIView):
    """One branch on one day: hours, classes placed, and remaining open stretches.

    Teachers and staff use this to decide where a class can still go.
    """

    permission_classes = [IsTeacherOrStaff]

    def get(self, request, branch_id):
        branch = get_branch(branch_id, include_inactive=False)
        if branch is None:
            return Response({'detail': 'Branch not found.'}, status=status.HTTP_404_NOT_FOUND)
        day = _parse_day(request.query_params.get('date'))
        if day is None:
            return Response({'detail': 'date must be YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)
        classes = sessions_for_list(branch_sessions_on(branch, day))
        return Response({
            **serialize_branch(branch),
            'date': day.isoformat(),
            'classes': SessionSerializer(classes, many=True, context={'request': request}).data,
            'open_windows': [serialize_window(w) for w in open_windows(branch, day)],
        })


class TeacherBranchListView(APIView):
    """Active branches plus the teacher's own offerings for the add-class form."""

    permission_classes = [IsTeacherOrStaff]

    def get(self, request):
        payload = {'branches': [serialize_branch(b) for b in list_branches()]}
        if request.user.groups.filter(name='teacher').exists():
            payload['offerings'] = [_offering_payload(o) for o in teacher_offerings(request.user)]
        else:
            payload['offerings'] = []
        return Response(payload)


class TeacherBranchClassCreateView(APIView):
    permission_classes = [IsTeacherOrStaff]

    def post(self, request, branch_id):
        if not user_is_staff(request.user) and not teacher_can(request.user, 'manage_schedule'):
            return permission_denied_response('manage_schedule')
        if not request.user.groups.filter(name='teacher').exists():
            return Response({'detail': 'Use the staff endpoint to place a class for a teacher.'}, status=status.HTTP_400_BAD_REQUEST)
        branch = get_branch(branch_id, include_inactive=False)
        if branch is None:
            return Response({'detail': 'Branch not found.'}, status=status.HTTP_404_NOT_FOUND)
        return _place_from_request(request, branch, request.user)


class SessionWalkInToggleView(APIView):
    """Staff, or the teacher who owns the class, flips walk-ins: { accepts_walk_ins }."""

    permission_classes = [IsTeacherOrStaff]

    def post(self, request, session_id):
        session = Session.objects.filter(pk=session_id).first()
        if session is None:
            return Response({'detail': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not user_is_staff(request.user):
            if session.teacher_id != request.user.id:
                return Response({'detail': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)
            if not teacher_can(request.user, 'manage_schedule'):
                return permission_denied_response('manage_schedule')
        if not session.branch_id:
            return Response({'detail': 'Only in-branch classes take walk-ins.'}, status=status.HTTP_400_BAD_REQUEST)
        set_walk_ins(session, request.data.get('accepts_walk_ins', True))
        row = sessions_for_list(Session.objects.filter(pk=session.pk)).get()
        return Response(SessionSerializer(row, context={'request': request}).data)


class StudentTodayView(APIView):
    """Today's in-branch classes a student can still join.

    Classes that have not started are listed; walk-in classes stay listed until they end.
    Empty opening hours are never shown — only classes with a teacher and topic.
    """

    permission_classes = [IsStudent]

    def get(self, request):
        day = _parse_day(request.query_params.get('date'))
        if day is None:
            return Response({'detail': 'date must be YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)
        branch_id = request.query_params.get('branch')
        branches = list_branches()
        if branch_id:
            branches = branches.filter(pk=branch_id)

        now = timezone.now()
        allowed_ids = allowed_class_ids_for_user(request.user)
        booked = Booking.objects.filter(student=request.user, session_id=OuterRef('pk'), status='confirmed')

        rows = []
        for branch in branches:
            qs = branch_sessions_on(branch, day).filter(
                teacher__is_active=True,
                class_offering__isnull=False,
            ).filter(
                Q(start_time__gt=now) | Q(accepts_walk_ins=True, end_time__gt=now),
            )
            if allowed_ids is not None:
                qs = qs.filter(class_offering_id__in=allowed_ids) if allowed_ids else qs.none()
            classes = sessions_for_list(qs).annotate(student_booked=Exists(booked))
            rows.append({
                **serialize_branch(branch),
                'classes': SessionSerializer(classes, many=True, context={'request': request}).data,
            })
        return Response({'date': day.isoformat(), 'branches': rows})
