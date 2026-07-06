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
    ).select_related('plan').prefetch_related('plan__allowed_classes')


def has_active_membership(user):
    return _active_qs(user).exists()


def active_memberships_for(user):
    return list(_active_qs(user).order_by('-valid_until', '-id'))


def active_membership_for(user):
    return _active_qs(user).order_by('-valid_until', '-id').first()


def total_tickets_remaining(user):
    return sum(m.tickets_remaining for m in active_memberships_for(user))


def _membership_allows_class(membership, class_offering):
    if class_offering is None:
        return True
    plan = membership.plan
    if not plan.allowed_classes.all():
        return True
    return plan.allowed_classes.filter(pk=class_offering.pk, is_active=True).exists()


def membership_allows_class(user, class_offering):
    """True when any active plan includes this catalog class (or all classes)."""
    if class_offering is None:
        return has_active_membership(user)
    return any(
        _membership_allows_class(membership, class_offering)
        for membership in active_memberships_for(user)
    )


def membership_allows_session(user, session):
    return membership_allows_class(user, session.class_offering)


def membership_for_booking(user, session):
    """Active membership that covers this session and has enough tickets."""
    from scheduling.services.tickets import session_ticket_cost

    cost = session_ticket_cost(session)
    for membership in active_memberships_for(user):
        if not _membership_allows_class(membership, session.class_offering):
            continue
        if membership.tickets_remaining >= cost:
            return membership
    return None


def allowed_class_ids_for_user(user):
    """Class offering IDs bookable with current memberships, or None if unrestricted."""
    memberships = active_memberships_for(user)
    if not memberships:
        return set()
    allowed_ids = set()
    unrestricted = False
    for membership in memberships:
        classes = list(membership.plan.allowed_classes.all())
        if not classes:
            unrestricted = True
        else:
            allowed_ids.update(c.pk for c in classes)
    if unrestricted:
        return None
    return allowed_ids
