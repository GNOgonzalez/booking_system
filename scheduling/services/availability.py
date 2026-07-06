from scheduling.models import AvailabilityBlock, SpecialAvailability
from scheduling.services.timezones import session_in_teacher_local


def teacher_has_availability_blocks(teacher):
    return (
        AvailabilityBlock.objects.filter(teacher=teacher).exists()
        or SpecialAvailability.objects.filter(teacher=teacher).exists()
    )


def _session_fits_time_range(start_time, end_time, block_start, block_end):
    return block_start <= start_time.time() and block_end >= end_time.time()


def session_within_availability(teacher, start_time, end_time):
    """Return True if the session fits a weekly or special block, or teacher has none yet."""
    weekly = AvailabilityBlock.objects.filter(teacher=teacher)
    special = SpecialAvailability.objects.filter(teacher=teacher)
    if not weekly.exists() and not special.exists():
        return True

    local_start, local_end = session_in_teacher_local(teacher, start_time, end_time)
    session_date = local_start.date()
    for block in special.filter(date=session_date):
        if _session_fits_time_range(local_start, local_end, block.start_time, block.end_time):
            return True

    weekday = local_start.weekday()
    for block in weekly.filter(weekday=weekday):
        if _session_fits_time_range(local_start, local_end, block.start_time, block.end_time):
            return True
    return False


OUTSIDE_AVAILABILITY_DETAIL = 'Session time is outside your availability.'
OUTSIDE_AVAILABILITY_STAFF_DETAIL = 'Session time is outside teacher availability.'


def ensure_special_block_for_session(teacher, start_time, end_time, *, note=''):
    """Create a one-off special block that covers the session window, if none exists yet."""
    local_start, local_end = session_in_teacher_local(teacher, start_time, end_time)
    session_date = local_start.date()
    start = local_start.time()
    end = local_end.time()
    covers = SpecialAvailability.objects.filter(
        teacher=teacher,
        date=session_date,
        start_time__lte=start,
        end_time__gte=end,
    ).exists()
    if covers:
        return
    SpecialAvailability.objects.create(
        teacher=teacher,
        date=session_date,
        start_time=start,
        end_time=end,
        note=note or '',
    )


def resolve_session_availability(
    teacher,
    start_time,
    end_time,
    *,
    acting_user,
    add_special=False,
    special_note='',
    staff_message=False,
):
    """
    Return (True, None) when the session may be created, else (False, user-facing detail).
    When add_special is True and the actor may manage availability, create a special block first.
    """
    if session_within_availability(teacher, start_time, end_time):
        return True, None

    from scheduling.services.teacher_permissions import teacher_can

    if add_special and teacher_can(acting_user, 'manage_availability'):
        ensure_special_block_for_session(
            teacher,
            start_time,
            end_time,
            note=special_note,
        )
        if session_within_availability(teacher, start_time, end_time):
            return True, None

    detail = OUTSIDE_AVAILABILITY_STAFF_DETAIL if staff_message else OUTSIDE_AVAILABILITY_DETAIL
    return False, detail


def request_wants_special_availability(request):
    val = request.data.get('add_special_availability')
    return val in (True, 'true', 'True', '1', 1)


def times_overlap(start_a, end_a, start_b, end_b):
    return start_a < end_b and start_b < end_a
