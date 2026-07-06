"""First-run onboarding checklist — computed from existing data, no duplicated business rules."""

from django.contrib.auth import get_user_model
from django.utils import timezone

from scheduling.models import Profile

User = get_user_model()


def _student_steps(user, profile):
    from progress.models import SessionFeedback
    from scheduling.models import Booking
    from scheduling.services.membership import active_memberships_for

    has_membership = bool(active_memberships_for(user))
    has_booking = Booking.objects.filter(student=user, status='confirmed').exists()
    has_progress = has_booking or SessionFeedback.objects.filter(student=user).exists()

    return [
        {
            'key': 'display_name',
            'label': 'Set your display name',
            'path': '/profile',
            'completed': bool(profile.display_name.strip()),
        },
        {
            'key': 'membership',
            'label': 'Get a membership or tickets',
            'path': '/membership',
            'completed': has_membership,
        },
        {
            'key': 'book',
            'label': 'Book or request a class',
            'path': '/sessions',
            'completed': has_booking,
        },
        {
            'key': 'progress',
            'label': 'Review your progress',
            'path': '/progress',
            'completed': has_progress,
        },
    ]


def _teacher_steps(user):
    from scheduling.models import AvailabilityBlock, ClassOffering, Session

    return [
        {
            'key': 'availability',
            'label': 'Set your availability',
            'path': '/teacher/availability',
            'completed': AvailabilityBlock.objects.filter(teacher=user).exists(),
        },
        {
            'key': 'class',
            'label': 'Add a class to your catalog',
            'path': '/teacher/classes',
            'completed': ClassOffering.objects.filter(teacher=user, is_active=True).exists(),
        },
        {
            'key': 'session',
            'label': 'Schedule your first session',
            'path': '/teacher/sessions/new',
            'completed': Session.objects.filter(teacher=user).exists(),
        },
    ]


def _staff_steps():
    from scheduling.models import MembershipPlan, StudioBranding

    branding = StudioBranding.load()
    has_branding = bool(branding.logo) or branding.display_name.strip() != 'Booking Studio'
    has_plan = MembershipPlan.objects.filter(is_active=True).exists()
    teacher_count = User.objects.filter(groups__name='teacher', is_active=True).count()

    return [
        {
            'key': 'branding',
            'label': 'Customize sign-in branding',
            'path': '/staff/branding',
            'completed': has_branding,
        },
        {
            'key': 'memberships',
            'label': 'Configure membership plans',
            'path': '/staff/memberships',
            'completed': has_plan,
        },
        {
            'key': 'teachers',
            'label': 'Review teachers on the dashboard',
            'path': '/staff',
            'completed': teacher_count >= 1,
        },
    ]


def onboarding_for_user(user):
    profile, _ = Profile.objects.get_or_create(user=user)
    if profile.onboarding_dismissed_at:
        return {'dismissed': True, 'complete': True, 'steps': []}

    roles = set(user.groups.values_list('name', flat=True))
    if 'staff' in roles:
        steps = _staff_steps()
    elif 'teacher' in roles and 'student' not in roles:
        steps = _teacher_steps(user)
    elif 'student' in roles:
        steps = _student_steps(user, profile)
    else:
        steps = []

    complete = bool(steps) and all(step['completed'] for step in steps)
    return {
        'dismissed': False,
        'complete': complete,
        'steps': steps,
    }


def dismiss_onboarding(user):
    profile, _ = Profile.objects.get_or_create(user=user)
    profile.onboarding_dismissed_at = timezone.now()
    profile.save(update_fields=['onboarding_dismissed_at'])
    return onboarding_for_user(user)
