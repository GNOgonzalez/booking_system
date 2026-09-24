"""Branch open hours and in-branch classes.

A branch is a physical location with weekly opening windows. Classes placed in a
branch must fit inside those windows and must name a teacher and a class offering,
so students only ever see classes that are ready to attend.
"""

from datetime import datetime, time

from django.db import transaction
from django.utils import timezone

from scheduling.models import AvailabilityBlock, Branch, BranchHours, ClassOffering, Session
from scheduling.services.sessions import class_topic_belongs_to_offering, session_display_title

WEEKDAY_LABELS = dict(AvailabilityBlock.WEEKDAY_CHOICES)
OUTSIDE_BRANCH_HOURS_DETAIL = 'That time is outside the branch’s open hours.'
TEACHER_BUSY_DETAIL = 'This teacher already has a session at that time.'


def studio_tz():
    return timezone.get_default_timezone()


def _parse_time(value):
    if isinstance(value, time):
        return value
    text = str(value or '').strip()
    for fmt in ('%H:%M', '%H:%M:%S'):
        try:
            return datetime.strptime(text, fmt).time()
        except ValueError:
            continue
    return None


def list_branches(*, include_inactive=False):
    qs = Branch.objects.prefetch_related('hours')
    if not include_inactive:
        qs = qs.filter(is_active=True)
    return qs


def get_branch(branch_id, *, include_inactive=True):
    qs = Branch.objects.prefetch_related('hours')
    if not include_inactive:
        qs = qs.filter(is_active=True)
    return qs.filter(pk=branch_id).first()


def _clean_hours(rows):
    """Validate [{weekday, start_time, end_time}] rows. Returns (cleaned, error)."""
    cleaned = []
    for row in rows or []:
        try:
            weekday = int(row.get('weekday'))
        except (TypeError, ValueError):
            return None, 'Weekday must be 0 (Monday) to 6 (Sunday).'
        if weekday not in WEEKDAY_LABELS:
            return None, 'Weekday must be 0 (Monday) to 6 (Sunday).'
        start = _parse_time(row.get('start_time'))
        end = _parse_time(row.get('end_time'))
        if start is None or end is None:
            return None, 'Hours must be HH:MM.'
        if end <= start:
            return None, f'{WEEKDAY_LABELS[weekday]}: closing time must be after opening time.'
        cleaned.append((weekday, start, end))
    cleaned.sort()
    for (day_a, start_a, end_a), (day_b, start_b, _) in zip(cleaned, cleaned[1:]):
        if day_a == day_b and start_b < end_a:
            return None, f'{WEEKDAY_LABELS[day_a]}: opening windows overlap.'
    return cleaned, None


@transaction.atomic
def save_branch(*, branch=None, name=None, is_active=None, hours=None):
    """Create or update a branch. `hours` replaces the full weekly list when given."""
    if branch is None:
        name = (name or '').strip()
        if not name:
            return None, 'Give the branch a name.'
        if Branch.objects.filter(name__iexact=name).exists():
            return None, 'A branch with that name already exists.'
        branch = Branch.objects.create(name=name[:120], is_active=True if is_active is None else bool(is_active))
    else:
        if name is not None:
            name = name.strip()
            if not name:
                return None, 'Give the branch a name.'
            if Branch.objects.filter(name__iexact=name).exclude(pk=branch.pk).exists():
                return None, 'A branch with that name already exists.'
            branch.name = name[:120]
        if is_active is not None:
            branch.is_active = bool(is_active)
        branch.save()

    if hours is not None:
        cleaned, err = _clean_hours(hours)
        if err:
            transaction.set_rollback(True)
            return None, err
        branch.hours.all().delete()
        BranchHours.objects.bulk_create([
            BranchHours(branch=branch, weekday=weekday, start_time=start, end_time=end)
            for weekday, start, end in cleaned
        ])
    return get_branch(branch.id), None


def _local(start_time, end_time):
    tz = studio_tz()
    return start_time.astimezone(tz), end_time.astimezone(tz)


def session_within_branch_hours(branch, start_time, end_time):
    """The whole class must sit inside one opening window on that weekday (studio time)."""
    if end_time <= start_time:
        return False
    local_start, local_end = _local(start_time, end_time)
    if local_start.date() != local_end.date():
        return False
    for window in branch.hours.all():
        if window.weekday != local_start.weekday():
            continue
        if window.start_time <= local_start.time() and window.end_time >= local_end.time():
            return True
    return False


def teacher_is_busy(teacher, start_time, end_time, *, exclude_session=None):
    qs = Session.objects.filter(
        teacher=teacher,
        status='open',
        start_time__lt=end_time,
        end_time__gt=start_time,
    )
    if exclude_session is not None:
        qs = qs.exclude(pk=exclude_session.pk)
    return qs.exists()


def branch_sessions_on(branch, day):
    """Open classes at a branch on a studio-local date, ordered by start."""
    tz = studio_tz()
    day_start = datetime.combine(day, time.min).replace(tzinfo=tz)
    day_end = datetime.combine(day, time.max).replace(tzinfo=tz)
    return (
        Session.objects.filter(
            branch=branch,
            status='open',
            start_time__gte=day_start,
            start_time__lte=day_end,
        )
        .select_related('teacher', 'class_offering', 'class_topic')
        .order_by('start_time')
    )


def open_windows(branch, day):
    """Opening windows on `day` minus time already taken by classes at this branch.

    Returns a list of {start, end} aware datetimes in studio time. Teachers use this to
    see where a class could still go; students never see these.
    """
    tz = studio_tz()
    windows = []
    for row in branch.hours.all():
        if row.weekday != day.weekday():
            continue
        windows.append([
            datetime.combine(day, row.start_time).replace(tzinfo=tz),
            datetime.combine(day, row.end_time).replace(tzinfo=tz),
        ])
    for session in branch_sessions_on(branch, day):
        s_start, s_end = _local(session.start_time, session.end_time)
        next_windows = []
        for w_start, w_end in windows:
            if s_end <= w_start or s_start >= w_end:
                next_windows.append([w_start, w_end])
                continue
            if s_start > w_start:
                next_windows.append([w_start, s_start])
            if s_end < w_end:
                next_windows.append([s_end, w_end])
        windows = next_windows
    return [{'start': start, 'end': end} for start, end in windows if end > start]


def place_branch_class(
    *,
    branch,
    teacher,
    class_offering,
    start_time,
    end_time,
    class_topic=None,
    capacity=None,
    accepts_walk_ins=False,
):
    """Create a class inside branch hours. Returns (session, error)."""
    if branch is None or not branch.is_active:
        return None, 'That branch is not open.'
    if teacher is None or not teacher.is_active:
        return None, 'Teacher not found.'
    if class_offering is None or class_offering.teacher_id != teacher.id or not class_offering.is_active:
        return None, 'Class not found in that teacher’s catalog.'
    if class_topic is not None and not class_topic_belongs_to_offering(class_topic.id, class_offering):
        return None, 'Topic not found in this class.'
    if start_time is None or end_time is None or end_time <= start_time:
        return None, 'End time must be after start time.'
    if not session_within_branch_hours(branch, start_time, end_time):
        return None, OUTSIDE_BRANCH_HOURS_DETAIL
    if teacher_is_busy(teacher, start_time, end_time):
        return None, TEACHER_BUSY_DETAIL

    try:
        capacity = int(capacity) if capacity not in (None, '') else 0
    except (TypeError, ValueError):
        return None, 'Capacity must be a whole number.'
    if capacity <= 0:
        capacity = class_offering.default_capacity or 1

    session = Session.objects.create(
        teacher=teacher,
        class_offering=class_offering,
        class_topic=class_topic,
        title=session_display_title(class_offering, class_topic),
        start_time=start_time,
        end_time=end_time,
        capacity=capacity,
        status='open',
        branch=branch,
        accepts_walk_ins=bool(accepts_walk_ins),
    )
    from scheduling.services.meetings import attach_meeting_link

    attach_meeting_link(session)
    return session, None


def set_walk_ins(session, allowed):
    session.accepts_walk_ins = bool(allowed)
    session.save(update_fields=['accepts_walk_ins'])
    return session


def teacher_offerings(teacher):
    return ClassOffering.objects.filter(teacher=teacher, is_active=True).prefetch_related('topics')


def serialize_hours(branch):
    return [
        {
            'id': row.id,
            'weekday': row.weekday,
            'weekday_label': WEEKDAY_LABELS[row.weekday],
            'start_time': row.start_time.strftime('%H:%M'),
            'end_time': row.end_time.strftime('%H:%M'),
        }
        for row in branch.hours.all()
    ]


def serialize_branch(branch):
    return {
        'id': branch.id,
        'name': branch.name,
        'is_active': branch.is_active,
        'hours': serialize_hours(branch),
    }


def serialize_window(window):
    return {'start': window['start'].isoformat(), 'end': window['end'].isoformat()}
