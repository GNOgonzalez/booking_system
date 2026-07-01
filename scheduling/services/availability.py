from scheduling.models import AvailabilityBlock


def teacher_has_availability_blocks(teacher):
    return AvailabilityBlock.objects.filter(teacher=teacher).exists()


def session_within_availability(teacher, start_time, end_time):
    """Return True if the session fits a weekly block, or teacher has no blocks yet."""
    blocks = AvailabilityBlock.objects.filter(teacher=teacher)
    if not blocks.exists():
        return True

    weekday = start_time.weekday()
    session_start = start_time.time()
    session_end = end_time.time()

    for block in blocks.filter(weekday=weekday):
        if block.start_time <= session_start and block.end_time >= session_end:
            return True
    return False
