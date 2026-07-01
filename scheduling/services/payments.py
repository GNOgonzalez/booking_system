"""Membership payments.

Mock by default so the app works with no Stripe account. When STRIPE_SECRET_KEY is
set, a real implementation would create a Checkout Session / PaymentIntent here.
"""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from scheduling.models import Membership
from scheduling.services.notifications import send_membership_receipt

VALID_PLANS = {choice[0] for choice in Membership.PLAN_CHOICES}


def get_plan_prices():
    return settings.STRIPE.get('PRICES', {})


def purchase_membership(user, plan_type='basic', months=1):
    """Activate (or extend) a membership. Returns (membership, error)."""
    if plan_type not in VALID_PLANS:
        return None, 'Unknown plan.'

    if settings.STRIPE.get('ENABLED'):
        # TODO: create Stripe Checkout Session and confirm payment via webhook
        # before activating. For the sandbox we activate immediately.
        pass

    today = timezone.now().date()
    membership = (
        Membership.objects.filter(user=user, plan_type=plan_type).order_by('-id').first()
    )
    base_date = today
    if membership and membership.valid_until and membership.valid_until > today:
        base_date = membership.valid_until

    valid_until = base_date + timedelta(days=30 * months)

    if membership:
        membership.is_active = True
        membership.valid_until = valid_until
        membership.save()
    else:
        membership = Membership.objects.create(
            user=user,
            plan_type=plan_type,
            is_active=True,
            valid_until=valid_until,
        )

    send_membership_receipt(membership)
    return membership, None
