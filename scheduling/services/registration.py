"""Student self-registration."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from scheduling.models import Profile
from scheduling.services.staff_alerts import notify_student_registered

User = get_user_model()


def register_student(*, username, email, password, display_name=''):
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

    student_group, _ = Group.objects.get_or_create(name='student')
    user = User.objects.create_user(username=username, email=email, password=password)
    user.groups.add(student_group)
    profile, _ = Profile.objects.get_or_create(user=user)
    if display_name:
        profile.display_name = display_name
        profile.save(update_fields=['display_name'])
    notify_student_registered(user)
    return user, None
