"""Staff operations — act on behalf of teachers."""

from django.contrib.auth import get_user_model

User = get_user_model()


def user_is_staff(user):
    return user.is_authenticated and user.groups.filter(name='staff').exists()


def list_teachers():
    return User.objects.filter(groups__name='teacher').order_by('username')


def get_teacher(teacher_id):
    return User.objects.filter(pk=teacher_id, groups__name='teacher').first()
