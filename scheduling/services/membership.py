from django.db.models import Q
from django.utils import timezone

from scheduling.models import Membership


def _active_qs(user):
    today = timezone.now().date()
    return Membership.objects.filter(
        user=user,
        is_active=True,
    ).filter(
        Q(valid_until__isnull=True) | Q(valid_until__gte=today),
    )


def has_active_membership(user):
    return _active_qs(user).exists()


def active_membership_for(user):
    return _active_qs(user).order_by('-valid_until').first()
