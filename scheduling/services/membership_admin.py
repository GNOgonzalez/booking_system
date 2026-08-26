"""Staff overrides on a student's membership — comp a plan, fix a ticket balance, cancel.

Every write records a `StaffActionLog` row, and money that changed hands outside Stripe
is recorded as a `Payment` with provider `staff` so reports stay accurate.
"""

from datetime import date, timedelta

from django.utils import timezone

from scheduling.models import Booking, Membership, MembershipPlan, Payment, StaffActionLog
from scheduling.services.membership import active_memberships_for, total_tickets_remaining
from scheduling.services.payments import grant_plan_to_user
from scheduling.services.staff_audit import log_staff_action

MAX_TICKET_BALANCE = 999


def _serialize_membership(membership):
    return {
        'id': membership.id,
        'plan_id': membership.plan_id,
        'plan_name': membership.plan.name,
        'plan_type': membership.plan.plan_type,
        'is_active': membership.is_active,
        'valid_until': membership.valid_until,
        'tickets_remaining': membership.tickets_remaining,
        'is_expired': bool(
            membership.valid_until and membership.valid_until < timezone.now().date(),
        ),
    }


def _serialize_payment(payment):
    return {
        'id': payment.id,
        'plan_name': payment.plan.name,
        'amount_cents': payment.amount_cents,
        'quantity': payment.quantity,
        'provider': payment.provider,
        'status': payment.status,
        'description': payment.description,
        'created_at': payment.created_at,
    }


def _serialize_booking(booking):
    session = booking.session
    return {
        'id': booking.id,
        'session_id': session.id,
        'session_title': session.title,
        'teacher': session.teacher.username,
        'start_time': session.start_time,
        'tickets_spent': booking.tickets_spent,
        'status': booking.status,
    }


def student_membership_overview(student):
    """Everything staff needs on one panel: memberships, tickets, payments, next bookings."""
    memberships = (
        Membership.objects.filter(user=student)
        .select_related('plan')
        .order_by('-is_active', '-id')
    )
    payments = (
        Payment.objects.filter(user=student)
        .select_related('plan')
        .order_by('-created_at')[:10]
    )
    upcoming = (
        Booking.objects.filter(
            student=student,
            status='confirmed',
            session__start_time__gte=timezone.now(),
        )
        .select_related('session', 'session__teacher')
        .order_by('session__start_time')
    )
    return {
        'student': {
            'id': student.id,
            'username': student.username,
            'email': student.email,
            'is_active': student.is_active,
        },
        'tickets_remaining': total_tickets_remaining(student),
        'has_active_membership': bool(active_memberships_for(student)),
        'memberships': [_serialize_membership(m) for m in memberships],
        'payments': [_serialize_payment(p) for p in payments],
        'upcoming_bookings': [_serialize_booking(b) for b in upcoming],
    }


def _bounded_int(value, *, maximum):
    """Clamped positive integer, or None when the value is unusable."""
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    if number < 1:
        return None
    return min(number, maximum)


def grant_membership(actor, student, *, plan_id, months=1, amount_cents=0, note=''):
    """Comp or record a paid membership for a student. Returns (overview, error)."""
    plan = MembershipPlan.objects.filter(pk=plan_id).first()
    if plan is None:
        return None, 'Plan not found.'
    if not plan.is_active:
        return None, 'That plan is inactive. Reactivate it first.'

    months = _bounded_int(months, maximum=24) or 1
    try:
        amount_cents = max(0, int(amount_cents or 0))
    except (TypeError, ValueError):
        return None, 'Amount must be a whole number of cents.'

    membership, error = grant_plan_to_user(student, plan, months=months)
    if error:
        return None, error

    Payment.objects.create(
        user=student,
        plan=plan,
        membership=membership,
        amount_cents=amount_cents,
        quantity=months,
        provider=Payment.PROVIDER_STAFF,
        status=Payment.STATUS_COMPLETED,
        description=f'{plan.name} × {months} (recorded by {actor.username})',
    )
    log_staff_action(
        actor=actor,
        action=StaffActionLog.ACTION_MEMBERSHIP_GRANTED,
        target_user=student,
        summary=f'Granted {plan.name} × {months} to {student.username}',
        note=note,
        plan_id=plan.id,
        plan_name=plan.name,
        months=months,
        amount_cents=amount_cents,
        membership_id=membership.id,
    )
    return student_membership_overview(student), None


def _get_membership(student, membership_id):
    return (
        Membership.objects.filter(pk=membership_id, user=student)
        .select_related('plan')
        .first()
    )


def adjust_tickets(actor, student, *, membership_id, delta, note=''):
    """Add or remove tickets on one membership. Returns (overview, error)."""
    membership = _get_membership(student, membership_id)
    if membership is None:
        return None, 'Membership not found.'
    try:
        delta = int(delta)
    except (TypeError, ValueError):
        return None, 'Enter a whole number of tickets.'
    if delta == 0:
        return None, 'Enter a non-zero number of tickets.'

    before = membership.tickets_remaining
    after = before + delta
    if after < 0:
        return None, f'{student.username} only has {before} ticket(s) on this membership.'
    if after > MAX_TICKET_BALANCE:
        return None, f'Ticket balance cannot exceed {MAX_TICKET_BALANCE}.'

    membership.tickets_remaining = after
    membership.save(update_fields=['tickets_remaining'])

    verb = 'Added' if delta > 0 else 'Removed'
    log_staff_action(
        actor=actor,
        action=StaffActionLog.ACTION_TICKETS_ADJUSTED,
        target_user=student,
        summary=(
            f'{verb} {abs(delta)} ticket(s) on {membership.plan.name} '
            f'for {student.username} ({before} → {after})'
        ),
        note=note,
        membership_id=membership.id,
        delta=delta,
        tickets_before=before,
        tickets_after=after,
    )
    return student_membership_overview(student), None


def _parse_date(value):
    if isinstance(value, date):
        return value, None
    try:
        return date.fromisoformat(str(value)), None
    except (TypeError, ValueError):
        return None, 'Use a YYYY-MM-DD date.'


def update_membership(actor, student, *, membership_id, is_active=None, valid_until=None, extend_days=None, note=''):
    """Cancel, reactivate, or change the expiry date of one membership."""
    membership = _get_membership(student, membership_id)
    if membership is None:
        return None, 'Membership not found.'
    if is_active is None and valid_until is None and extend_days is None:
        return None, 'Provide is_active, valid_until, or extend_days.'

    changes = []
    update_fields = []

    if is_active is not None:
        membership.is_active = bool(is_active)
        update_fields.append('is_active')
        changes.append('activated' if membership.is_active else 'cancelled')

    if valid_until is not None:
        if valid_until == '':
            membership.valid_until = None
            changes.append('expiry cleared')
        else:
            parsed, error = _parse_date(valid_until)
            if error:
                return None, error
            membership.valid_until = parsed
            changes.append(f'expires {parsed.isoformat()}')
        update_fields.append('valid_until')

    if extend_days is not None:
        days = _bounded_int(extend_days, maximum=365)
        if days is None:
            return None, 'Extend by a whole number of days (1–365).'
        base = membership.valid_until
        today = timezone.now().date()
        if base is None or base < today:
            base = today
        membership.valid_until = base + timedelta(days=days)
        if 'valid_until' not in update_fields:
            update_fields.append('valid_until')
        changes.append(f'extended {days} day(s) to {membership.valid_until.isoformat()}')

    membership.save(update_fields=update_fields)
    log_staff_action(
        actor=actor,
        action=StaffActionLog.ACTION_MEMBERSHIP_UPDATED,
        target_user=student,
        summary=(
            f'{membership.plan.name} for {student.username}: ' + ', '.join(changes)
        ),
        note=note,
        membership_id=membership.id,
        is_active=membership.is_active,
        valid_until=membership.valid_until.isoformat() if membership.valid_until else None,
    )
    return student_membership_overview(student), None
