from django.http import HttpResponseForbidden


def user_in_group(user, group_name):
    return user.groups.filter(name=group_name).exists()


def require_group(user, group_name):
    if not user_in_group(user, group_name):
        return HttpResponseForbidden("You don't have access to this page.")
    return None
