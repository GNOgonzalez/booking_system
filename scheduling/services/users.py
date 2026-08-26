"""Staff user management — teachers and students (not staff accounts)."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from scheduling.models import Profile, StaffActionLog
from scheduling.services.staff_audit import log_staff_action
from scheduling.services.teacher_permissions import ensure_default_permissions

User = get_user_model()

CREATABLE_ROLES = ('teacher', 'student')


def user_is_staff_member(user):
    return user.groups.filter(name='staff').exists()


def list_students():
    return User.objects.filter(groups__name='student').order_by('username')


def get_student(student_id):
    return User.objects.filter(pk=student_id, groups__name='student').first()


def create_studio_user(*, role, username, password, email='', display_name='', actor=None):
    """Staff adds a teacher or student account. New teachers get all capabilities enabled."""
    if role not in CREATABLE_ROLES:
        return None, 'Role must be teacher or student.'

    username = (username or '').strip()
    email = (email or '').strip()
    display_name = (display_name or '').strip()

    if not username:
        return None, 'Username is required.'
    if User.objects.filter(username__iexact=username).exists():
        return None, 'That username is already taken.'
    if email and User.objects.filter(email__iexact=email).exists():
        return None, 'That email is already registered.'

    try:
        validate_password(password)
    except ValidationError as exc:
        return None, ' '.join(exc.messages)

    group, _ = Group.objects.get_or_create(name=role)
    user = User.objects.create_user(username=username, email=email, password=password)
    user.groups.add(group)

    profile, _ = Profile.objects.get_or_create(user=user)
    if display_name:
        profile.display_name = display_name
        profile.save(update_fields=['display_name'])

    if role == 'teacher':
        ensure_default_permissions(user)
    if actor is not None:
        log_staff_action(
            actor=actor,
            action=StaffActionLog.ACTION_USER_CREATED,
            target_user=user,
            summary=f'Created {role} account {user.username}',
            role=role,
        )
    return user, None


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
