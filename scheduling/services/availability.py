from scheduling.models import AvailabilityBlock, SpecialAvailability


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

    session_date = start_time.date()
    for block in special.filter(date=session_date):
        if _session_fits_time_range(start_time, end_time, block.start_time, block.end_time):
            return True

    weekday = start_time.weekday()
    for block in weekly.filter(weekday=weekday):
        if _session_fits_time_range(start_time, end_time, block.start_time, block.end_time):
            return True
    return False


def times_overlap(start_a, end_a, start_b, end_b):
    return start_a < end_b and start_b < end_a
