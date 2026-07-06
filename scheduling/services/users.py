"""Staff user management — teachers and students (not staff accounts)."""

from django.contrib.auth import get_user_model

from scheduling.models import Profile

User = get_user_model()


def user_is_staff_member(user):
    return user.groups.filter(name='staff').exists()


def list_students():
    return User.objects.filter(groups__name='student').order_by('username')


def get_student(student_id):
    return User.objects.filter(pk=student_id, groups__name='student').first()


def update_user_account(user, *, is_active=None, display_name=None):
    """Update a teacher or student account. Staff accounts cannot be changed."""
    if user_is_staff_member(user):
        return False, 'Staff accounts cannot be modified here.'

    update_fields = []
    if is_active is not None:
        user.is_active = bool(is_active)
        update_fields.append('is_active')
    if update_fields:
        user.save(update_fields=update_fields)

    if display_name is not None:
        profile, _ = Profile.objects.get_or_create(user=user)
        profile.display_name = display_name
        profile.save(update_fields=['display_name'])

    return True, None
