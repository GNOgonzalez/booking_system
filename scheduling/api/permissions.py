from rest_framework.permissions import BasePermission


def _active(user):
    """Authenticated AND active — deactivated users lose API access immediately."""
    return user.is_authenticated and user.is_active


class IsActiveUser(BasePermission):
    """Defense-in-depth: simplejwt already rejects inactive users at auth time
    (CHECK_USER_IS_ACTIVE), but permissions should not trust that alone."""

    def has_permission(self, request, view):
        return _active(request.user)


class IsStudent(BasePermission):
    def has_permission(self, request, view):
        return _active(request.user) and request.user.groups.filter(name='student').exists()


class IsTeacher(BasePermission):
    def has_permission(self, request, view):
        return _active(request.user) and request.user.groups.filter(name='teacher').exists()


class IsStaff(BasePermission):
    def has_permission(self, request, view):
        return _active(request.user) and request.user.groups.filter(name='staff').exists()


class IsStudentOrTeacher(BasePermission):
    def has_permission(self, request, view):
        if not _active(request.user):
            return False
        names = set(request.user.groups.values_list('name', flat=True))
        return bool(names & {'student', 'teacher', 'staff'})


class IsTeacherOrStaff(BasePermission):
    def has_permission(self, request, view):
        if not _active(request.user):
            return False
        names = set(request.user.groups.values_list('name', flat=True))
        return bool(names & {'teacher', 'staff'})
