"""Teacher capability flags — staff grants or revokes what each teacher can do."""

from scheduling.models import TeacherPermission

# (key, label, description) — extend here as the studio adds more capabilities.
TEACHER_PERMISSION_DEFS = [
    ('manage_schedule', 'Manage schedule', 'Create and schedule sessions'),
    ('manage_classes', 'Manage classes', 'Create and edit teachable classes'),
    ('manage_availability', 'Set availability', 'Edit weekly and special-day availability'),
    ('write_reports', 'Write reports', 'Submit session feedback for students'),
    ('assign_homework', 'Assign homework', 'Send files and journal prompts to students'),
    ('manage_curriculum', 'Manage curriculum', 'Edit student learning paths and skip modules'),
    ('manage_blog', 'Manage blog', 'Publish announcements and photos on the home page'),
    ('use_ai', 'Use AI', 'Draft session notes and other AI-assisted writing'),
]

PERMISSION_KEYS = [key for key, _, _ in TEACHER_PERMISSION_DEFS]


def ensure_default_permissions(teacher):
    """Idempotent — new teachers get all capabilities enabled until staff changes them."""
    for key in PERMISSION_KEYS:
        TeacherPermission.objects.get_or_create(
            teacher=teacher,
            key=key,
            defaults={'is_enabled': True},
        )


def permissions_for_teacher(teacher):
    ensure_default_permissions(teacher)
    rows = TeacherPermission.objects.filter(teacher=teacher, key__in=PERMISSION_KEYS)
    by_key = {row.key: row.is_enabled for row in rows}
    return {key: by_key.get(key, True) for key in PERMISSION_KEYS}


def set_teacher_permissions(teacher, updates):
    """Apply {key: bool} updates from staff."""
    ensure_default_permissions(teacher)
    for key, enabled in updates.items():
        if key not in PERMISSION_KEYS:
            continue
        TeacherPermission.objects.filter(teacher=teacher, key=key).update(is_enabled=bool(enabled))
    return permissions_for_teacher(teacher)


def user_is_staff(user):
    return user.is_authenticated and user.groups.filter(name='staff').exists()


def teacher_can(user, key):
    """Staff always can; teachers need the matching permission flag."""
    if user_is_staff(user):
        return True
    if not user.groups.filter(name='teacher').exists():
        return False
    if key not in PERMISSION_KEYS:
        return False
    perms = permissions_for_teacher(user)
    return perms.get(key, True)


def permission_denied_response(key):
    from rest_framework import status
    from rest_framework.response import Response

    labels = {k: label for k, label, _ in TEACHER_PERMISSION_DEFS}
    label = labels.get(key, key)
    return Response(
        {'detail': f'You do not have permission: {label}.'},
        status=status.HTTP_403_FORBIDDEN,
    )
