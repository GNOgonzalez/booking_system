"""Teacher-local timezone helpers for availability and scheduling."""

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from scheduling.models import Profile

DEFAULT_TZ = 'UTC'


def teacher_tz_name(teacher):
    profile = Profile.objects.filter(user=teacher).first()
    if profile and profile.timezone:
        name = profile.timezone.strip()
        if name:
            return name
    return DEFAULT_TZ


def teacher_zoneinfo(teacher):
    try:
        return ZoneInfo(teacher_tz_name(teacher))
    except (ZoneInfoNotFoundError, KeyError):
        return ZoneInfo(DEFAULT_TZ)


def combine_in_teacher_tz(teacher, day, time_obj):
    tz = teacher_zoneinfo(teacher)
    return datetime.combine(day, time_obj).replace(tzinfo=tz)


def session_in_teacher_local(teacher, start_time, end_time):
    tz = teacher_zoneinfo(teacher)
    return start_time.astimezone(tz), end_time.astimezone(tz)
