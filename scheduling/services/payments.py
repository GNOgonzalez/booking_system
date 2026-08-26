"""Membership payments.

Mock by default so the app works with no Stripe account. When STRIPE_SECRET_KEY is
set, direct POST /api/membership/ purchases are blocked — use Stripe Checkout
(POST /api/membership/checkout/) once wired.
"""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from scheduling.models import Membership, MembershipPlan, Payment
from scheduling.services.membership import active_memberships_for
from scheduling.services.notifications import send_membership_receipt
from scheduling.services.staff_alerts import (
    membership_event_for_plan,
    notify_purchase,
)
from scheduling.services.tickets import grant_tickets


def payment_mode():
    return 'stripe' if settings.STRIPE.get('ENABLED') else 'mock'


def _masked_key(value):
    """Show enough of a key to identify it, never enough to use it."""
    if not value:
        return ''
    if len(value) <= 12:
        return '••••'
    return f'{value[:7]}…{value[-4:]}'


def payment_settings_status(*, base_url=''):
    """Read-only payment configuration for the staff settings panel. Never returns secrets."""
    from django.db.models import Count, Sum

    stripe = settings.STRIPE
    mode = payment_mode()
    totals = (
        Payment.objects.filter(status=Payment.STATUS_COMPLETED)
        .values('provider')
        .annotate(count=Count('id'), amount_cents=Sum('amount_cents'))
        .order_by('provider')
    )
    webhook_path = '/api/payments/stripe/webhook/'
    return {
        'mode': mode,
        'is_live': mode == 'stripe',
        'mock_payments_allowed': bool(settings.DEBUG or settings.ALLOW_MOCK_PAYMENTS),
        'debug': settings.DEBUG,
        'stripe': {
            'secret_key_configured': bool(stripe.get('SECRET_KEY')),
            'publishable_key': stripe.get('PUBLISHABLE_KEY') or '',
            'secret_key_hint': _masked_key(stripe.get('SECRET_KEY')),
            'webhook_secret_configured': bool(stripe.get('WEBHOOK_SECRET')),
            'webhook_path': webhook_path,
            'webhook_url': f'{base_url.rstrip("/")}{webhook_path}' if base_url else webhook_path,
        },
        'env_keys': [
            'STRIPE_SECRET_KEY',
            'STRIPE_PUBLISHABLE_KEY',
            'STRIPE_WEBHOOK_SECRET',
            'ALLOW_MOCK_PAYMENTS',
        ],
        'completed_by_provider': [
            {
                'provider': row['provider'],
                'count': row['count'],
                'amount_cents': row['amount_cents'] or 0,
            }
            for row in totals
        ],
        'pending_count': Payment.objects.filter(status=Payment.STATUS_PENDING).count(),
        'failed_count': Payment.objects.filter(status=Payment.STATUS_FAILED).count(),
    }


def get_available_plans():
    return (
        MembershipPlan.objects.filter(is_active=True)
        .prefetch_related('allowed_classes')
        .order_by('plan_type', 'price_cents', 'name')
    )


def record_payment(user, plan, membership, *, amount_cents, quantity=1, provider=None, status=None):
    provider = provider or (Payment.PROVIDER_STRIPE if settings.STRIPE.get('ENABLED') else Payment.PROVIDER_MOCK)
    status = status or Payment.STATUS_COMPLETED
    return Payment.objects.create(
        user=user,
        plan=plan,
        membership=membership,
        amount_cents=amount_cents,
        quantity=quantity,
        provider=provider,
        status=status,
        description=f'{plan.name} × {quantity}',
    )


def create_pending_payment(user, plan, *, months=1, membership_id=None):
    """Create a pending Payment row before Stripe Checkout completes."""
    amount_cents = plan.price_cents * months
    membership = None
    if membership_id is not None:
        membership = Membership.objects.filter(pk=membership_id, user=user).first()
    return Payment.objects.create(
        user=user,
        plan=plan,
        membership=membership,
        amount_cents=amount_cents,
        quantity=months,
        provider=Payment.PROVIDER_STRIPE,
        status=Payment.STATUS_PENDING,
        description=f'{plan.name} × {months}',
    )


def validate_checkout_plan(user, plan, *, months=1, membership_id=None):
    """Pre-flight checks before starting Stripe Checkout."""
    if plan.plan_type == MembershipPlan.PLAN_TICKET_PACK:
        _, error = _membership_for_ticket_pack(user, plan, membership_id)
        return error
    return None


def _grant_subscription(user, plan, months=1):
    today = timezone.now().date()
    membership = Membership.objects.filter(user=user, plan=plan).order_by('-id').first()
    base_date = today
    if membership and membership.valid_until and membership.valid_until > today:
        base_date = membership.valid_until

    days = plan.billing_period_days * months
    valid_until = base_date + timedelta(days=days)
    tickets_to_grant = plan.ticket_allowance * months

    if membership:
        membership.is_active = True
        membership.valid_until = valid_until
        membership.save(update_fields=['is_active', 'valid_until'])
        grant_tickets(membership, tickets_to_grant)
    else:
        membership = Membership.objects.create(
            user=user,
            plan=plan,
            is_active=True,
            valid_until=valid_until,
            tickets_remaining=tickets_to_grant,
        )
    return membership


def _grant_ticket_pack(user, plan, months=1, membership_id=None):
    membership, error = _membership_for_ticket_pack(user, plan, membership_id)
    if error:
        return None, error
    grant_tickets(membership, plan.ticket_allowance * months)
    return membership, None


def grant_plan_to_user(user, plan, *, months=1, membership_id=None):
    """Apply a plan's benefits without running checkout (staff comp or cash sale)."""
    if plan.plan_type == MembershipPlan.PLAN_TICKET_PACK:
        return _grant_ticket_pack(user, plan, months=months, membership_id=membership_id)
    return _grant_subscription(user, plan, months=months), None


def get_payment_status(user, payment_id):
    """Return payment status for the student who owns it, or (None, error)."""
    payment = (
        Payment.objects.filter(pk=payment_id, user=user)
        .select_related('plan')
        .first()
    )
    if payment is None:
        return None, 'Payment not found.'
    return {
        'id': payment.id,
        'status': payment.status,
        'plan_name': payment.plan.name,
    }, None


def fulfill_payment(payment_id, *, stripe_checkout_session_id='', stripe_payment_intent_id=''):
    """Complete a pending Stripe payment and activate the membership."""
    payment = (
        Payment.objects.select_for_update()
        .select_related('user', 'plan')
        .filter(pk=payment_id)
        .first()
    )
    if payment is None:
        return None, 'Payment not found.'
    if payment.status == Payment.STATUS_COMPLETED:
        return payment.membership, None

    plan = payment.plan
    if not plan.is_active:
        payment.status = Payment.STATUS_FAILED
        payment.save(update_fields=['status'])
        return None, 'Plan is no longer active.'

    user = payment.user
    months = payment.quantity
    membership_id = payment.membership_id
    was_new_subscription = (
        plan.plan_type != MembershipPlan.PLAN_TICKET_PACK
        and not Membership.objects.filter(user=user, plan=plan).exists()
    )
    tickets_granted = plan.ticket_allowance * months

    if plan.plan_type == MembershipPlan.PLAN_TICKET_PACK:
        membership, error = _grant_ticket_pack(user, plan, months=months, membership_id=membership_id)
    else:
        membership = _grant_subscription(user, plan, months=months)
        error = None

    if error:
        payment.status = Payment.STATUS_FAILED
        payment.save(update_fields=['status'])
        return None, error

    payment.membership = membership
    payment.status = Payment.STATUS_COMPLETED
    payment.provider = Payment.PROVIDER_STRIPE
    if stripe_checkout_session_id:
        payment.stripe_checkout_session_id = stripe_checkout_session_id
    if stripe_payment_intent_id:
        payment.stripe_payment_intent_id = stripe_payment_intent_id
    payment.save(
        update_fields=[
            'membership',
            'status',
            'provider',
            'stripe_checkout_session_id',
            'stripe_payment_intent_id',
        ],
    )
    send_membership_receipt(membership)
    notify_purchase(
        payment=payment,
        membership=membership,
        membership_event_type=membership_event_for_plan(
            plan,
            was_new_subscription=was_new_subscription,
        ),
        tickets_granted=tickets_granted,
    )
    return membership, None


def _plans_share_classes(subscription_plan, ticket_plan):
    sub_classes = list(subscription_plan.allowed_classes.all())
    ticket_classes = list(ticket_plan.allowed_classes.all())
    if not sub_classes or not ticket_classes:
        return True
    sub_ids = {c.pk for c in sub_classes}
    return any(c.pk in sub_ids for c in ticket_classes)


def _membership_for_ticket_pack(user, ticket_plan, membership_id=None):
    if membership_id is not None:
        membership = (
            Membership.objects.filter(
                pk=membership_id,
                user=user,
                is_active=True,
                plan__plan_type=MembershipPlan.PLAN_SUBSCRIPTION,
            )
            .select_related('plan')
            .first()
        )
        if membership is None:
            return None, 'Membership not found.'
        if not _plans_share_classes(membership.plan, ticket_plan):
            return None, 'Those tickets cannot be added to that membership.'
        return membership, None

    for membership in active_memberships_for(user):
        if membership.plan.plan_type != MembershipPlan.PLAN_SUBSCRIPTION:
            continue
        if _plans_share_classes(membership.plan, ticket_plan):
            return membership, None
    return None, 'You need an active subject membership before buying individual tickets.'


def purchase_ticket_pack(user, plan, months=1, membership_id=None):
    membership, error = _grant_ticket_pack(user, plan, months=months, membership_id=membership_id)
    if error:
        return None, error
    payment = record_payment(
        user,
        plan,
        membership,
        amount_cents=plan.price_cents * months,
        quantity=months,
    )
    send_membership_receipt(membership)
    notify_purchase(
        payment=payment,
        membership=membership,
        membership_event_type=membership_event_for_plan(plan),
        tickets_granted=plan.ticket_allowance * months,
    )
    return membership, None


def purchase_subscription(user, plan, months=1):
    was_new_subscription = not Membership.objects.filter(user=user, plan=plan).exists()
    membership = _grant_subscription(user, plan, months=months)
    payment = record_payment(
        user,
        plan,
        membership,
        amount_cents=plan.price_cents * months,
        quantity=months,
    )
    send_membership_receipt(membership)
    notify_purchase(
        payment=payment,
        membership=membership,
        membership_event_type=membership_event_for_plan(
            plan,
            was_new_subscription=was_new_subscription,
        ),
        tickets_granted=plan.ticket_allowance * months,
    )
    return membership, None


def purchase_membership(user, plan_id, months=1, membership_id=None):
    """Activate, extend, or top up a membership. Returns (membership, error)."""
    plan = MembershipPlan.objects.filter(pk=plan_id, is_active=True).first()
    if plan is None:
        return None, 'Unknown or inactive plan.'

    if settings.STRIPE.get('ENABLED'):
        return None, 'Stripe is configured. Use POST /api/membership/checkout/ to pay via Stripe Checkout.'

    if not settings.DEBUG and not settings.ALLOW_MOCK_PAYMENTS:
        return None, (
            'Mock payments are disabled in production. '
            'Configure Stripe or set ALLOW_MOCK_PAYMENTS=true for testing only.'
        )

    if plan.plan_type == MembershipPlan.PLAN_TICKET_PACK:
        return purchase_ticket_pack(user, plan, months=months, membership_id=membership_id)
    return purchase_subscription(user, plan, months=months)
