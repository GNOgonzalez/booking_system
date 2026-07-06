"""Bookable session start times derived from teacher availability windows."""

from datetime import timedelta

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from scheduling.services.availability import times_overlap
from scheduling.services.class_requests import availability_snapshot


def _aware(dt):
    if dt is None:
        return None
    if timezone.is_naive(dt):
        return timezone.make_aware(dt)
    return dt


def scheduling_slot_options(
    teacher,
    *,
    days=28,
    duration_minutes=60,
    step_minutes=30,
):
    """Return open session slots inside availability windows (excl. busy intervals)."""
    snapshot = availability_snapshot(teacher, days=days)
    duration = timedelta(minutes=duration_minutes)
    step = timedelta(minutes=step_minutes)
    now = timezone.now()

    busy = []
    for item in snapshot['busy']:
        start = _aware(parse_datetime(item['start']))
        end = _aware(parse_datetime(item['end']))
        if start and end:
            busy.append((start, end))

    slots = []
    seen = set()
    for window in snapshot['windows']:
        win_start = _aware(parse_datetime(window['start']))
        win_end = _aware(parse_datetime(window['end']))
        if not win_start or not win_end:
            continue
        cursor = win_start
        while cursor + duration <= win_end:
            slot_end = cursor + duration
            if cursor > now and not any(
                times_overlap(cursor, slot_end, busy_start, busy_end)
                for busy_start, busy_end in busy
            ):
                key = cursor.isoformat()
                if key not in seen:
                    seen.add(key)
                    slots.append({
                        'start': cursor.isoformat(),
                        'end': slot_end.isoformat(),
                        'kind': window.get('kind', 'weekly'),
                        'note': window.get('note', ''),
                    })
            cursor += step

    slots.sort(key=lambda item: item['start'])
    return slots
