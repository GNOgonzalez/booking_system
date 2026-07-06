"""Stripe webhook handler."""

import json

from django.db import transaction

from integrations.stripe.client import stripe_enabled, verify_webhook_signature


def handle_webhook_request(payload, signature_header):
    """Verify and process a Stripe webhook. Returns (ok, message)."""
    if not stripe_enabled():
        return False, 'Stripe not configured.'

    if not verify_webhook_signature(payload, signature_header):
        return False, 'Invalid Stripe signature.'

    try:
        event = json.loads(payload)
    except json.JSONDecodeError:
        return False, 'Invalid JSON payload.'

    event_type = event.get('type')
    if event_type == 'checkout.session.completed':
        return _handle_checkout_completed(event.get('data', {}).get('object', {}))
    if event_type == 'checkout.session.expired':
        return _handle_checkout_expired(event.get('data', {}).get('object', {}))

    return True, f'Ignored event type: {event_type}'


def _payment_id_from_session(session):
    metadata = session.get('metadata') or {}
    payment_id = metadata.get('payment_id') or session.get('client_reference_id')
    if payment_id is None:
        return None
    try:
        return int(payment_id)
    except (TypeError, ValueError):
        return None


@transaction.atomic
def _handle_checkout_completed(session):
    from scheduling.services.payments import fulfill_payment

    payment_id = _payment_id_from_session(session)
    if payment_id is None:
        return False, 'Checkout session missing payment reference.'

    membership, error = fulfill_payment(
        payment_id,
        stripe_checkout_session_id=session.get('id', ''),
        stripe_payment_intent_id=session.get('payment_intent', '') or '',
    )
    if error:
        return False, error
    return True, f'Membership fulfilled for payment {payment_id}.'


@transaction.atomic
def _handle_checkout_expired(session):
    from scheduling.models import Payment

    payment_id = _payment_id_from_session(session)
    if payment_id is None:
        return True, 'Expired checkout without payment reference.'

    updated = Payment.objects.filter(
        pk=payment_id,
        status=Payment.STATUS_PENDING,
    ).update(status=Payment.STATUS_FAILED)
    if updated:
        return True, f'Marked payment {payment_id} failed (checkout expired).'
    return True, f'Payment {payment_id} already processed.'
