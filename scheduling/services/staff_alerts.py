"""In-app staff alerts for signups, membership changes, and payments.

Email hooks can be added later; emission must never block the primary action.
"""

import logging

from django.db.models import Exists, OuterRef
from django.utils import timezone

from scheduling.models import MembershipPlan, StaffAlert, StaffAlertRead

logger = logging.getLogger(__name__)

CATEGORIES = (
    StaffAlert.CATEGORY_USERS,
    StaffAlert.CATEGORY_MEMBERSHIP,
    StaffAlert.CATEGORY_FINANCIAL,
)


def emit_staff_alert(category, event_type, title, *, body='', payload=None, actor=None):
    """Create a StaffAlert. Best-effort — logs and returns None on failure."""
    try:
        return StaffAlert.objects.create(
            category=category,
            event_type=event_type,
            title=title,
            body=body or '',
            payload=payload or {},
            actor=actor,
        )
    except Exception:
        logger.exception(
            'Failed to emit staff alert %s/%s: %s',
            category,
            event_type,
            title,
        )
        return None


def notify_student_registered(user):
    display = ''
    profile = getattr(user, 'profile', None)
    if profile is not None:
        display = (profile.display_name or '').strip()
    detail = display or user.email or user.username
    return emit_staff_alert(
        StaffAlert.CATEGORY_USERS,
        StaffAlert.EVENT_STUDENT_REGISTERED,
        f'New student: {user.username}',
        body=detail,
        payload={
            'user_id': user.id,
            'username': user.username,
            'email': user.email or '',
            'display_name': display,
        },
        actor=user,
    )


def notify_purchase(*, payment, membership, membership_event_type, tickets_granted=0):
    """Emit separate financial + membership alerts for a completed purchase."""
    user = payment.user
    plan = payment.plan
    amount_display = f'${payment.amount_cents / 100:,.2f}'

    emit_staff_alert(
        StaffAlert.CATEGORY_FINANCIAL,
        StaffAlert.EVENT_PAYMENT_COMPLETED,
        f'Payment: {user.username} — {amount_display}',
        body=f'{plan.name} · {payment.provider}',
        payload={
            'payment_id': payment.id,
            'user_id': user.id,
            'username': user.username,
            'plan_id': plan.id,
            'plan_name': plan.name,
            'amount_cents': payment.amount_cents,
            'provider': payment.provider,
            'quantity': payment.quantity,
        },
        actor=user,
    )

    if membership_event_type == StaffAlert.EVENT_TICKETS_GRANTED:
        title = f'Tickets added: {user.username}'
        body = f'{tickets_granted} ticket(s) · {plan.name}'
    elif membership_event_type == StaffAlert.EVENT_MEMBERSHIP_RENEWED:
        title = f'Membership renewed: {user.username}'
        valid = membership.valid_until.isoformat() if membership and membership.valid_until else ''
        body = f'{plan.name}' + (f' · until {valid}' if valid else '')
    else:
        title = f'Membership activated: {user.username}'
        valid = membership.valid_until.isoformat() if membership and membership.valid_until else ''
        body = f'{plan.name}' + (f' · until {valid}' if valid else '')

    emit_staff_alert(
        StaffAlert.CATEGORY_MEMBERSHIP,
        membership_event_type,
        title,
        body=body,
        payload={
            'membership_id': membership.id if membership else None,
            'user_id': user.id,
            'username': user.username,
            'plan_id': plan.id,
            'plan_name': plan.name,
            'plan_type': plan.plan_type,
            'valid_until': (
                membership.valid_until.isoformat()
                if membership and membership.valid_until
                else None
            ),
            'tickets_remaining': membership.tickets_remaining if membership else None,
            'tickets_granted': tickets_granted,
            'payment_id': payment.id,
        },
        actor=user,
    )


def membership_event_for_subscription(*, was_new):
    if was_new:
        return StaffAlert.EVENT_MEMBERSHIP_ACTIVATED
    return StaffAlert.EVENT_MEMBERSHIP_RENEWED


def membership_event_for_plan(plan, *, was_new_subscription=False):
    if plan.plan_type == MembershipPlan.PLAN_TICKET_PACK:
        return StaffAlert.EVENT_TICKETS_GRANTED
    return membership_event_for_subscription(was_new=was_new_subscription)


def serialize_alert(alert, *, is_unread):
    return {
        'id': alert.id,
        'category': alert.category,
        'event_type': alert.event_type,
        'title': alert.title,
        'body': alert.body,
        'payload': alert.payload or {},
        'actor_id': alert.actor_id,
        'created_at': alert.created_at,
        'is_unread': is_unread,
    }


def list_staff_alerts(user, *, limit=10):
    """Grouped recent alerts plus per-category unread counts for one staff user."""
    limit = max(1, min(int(limit or 10), 50))
    read_exists = StaffAlertRead.objects.filter(alert_id=OuterRef('pk'), user=user)
    qs = StaffAlert.objects.annotate(is_read=Exists(read_exists)).order_by('-created_at')

    grouped = {category: [] for category in CATEGORIES}
    for category in CATEGORIES:
        for alert in qs.filter(category=category)[:limit]:
            grouped[category].append(
                serialize_alert(alert, is_unread=not alert.is_read),
            )

    unread = {}
    total = 0
    for category in CATEGORIES:
        count = qs.filter(category=category, is_read=False).count()
        unread[category] = count
        total += count
    unread['total'] = total

    return {
        'users': grouped[StaffAlert.CATEGORY_USERS],
        'membership': grouped[StaffAlert.CATEGORY_MEMBERSHIP],
        'financial': grouped[StaffAlert.CATEGORY_FINANCIAL],
        'unread': unread,
    }


def mark_alerts_read(user, *, alert_ids=None, mark_all=False):
    """Mark alerts as read for this staff user. Returns number of new read receipts."""
    if mark_all:
        targets = StaffAlert.objects.all()
    elif alert_ids:
        targets = StaffAlert.objects.filter(pk__in=alert_ids)
    else:
        return 0

    already = set(
        StaffAlertRead.objects.filter(user=user, alert__in=targets).values_list(
            'alert_id',
            flat=True,
        )
    )
    to_create = [
        StaffAlertRead(alert_id=alert_id, user=user, read_at=timezone.now())
        for alert_id in targets.values_list('pk', flat=True)
        if alert_id not in already
    ]
    if not to_create:
        return 0
    StaffAlertRead.objects.bulk_create(to_create, ignore_conflicts=True)
    return len(to_create)
