"""Stripe Checkout Session creation."""

from django.conf import settings

from integrations.stripe.client import stripe_api_request, stripe_enabled


def frontend_checkout_urls():
    origins = getattr(settings, 'CORS_ALLOWED_ORIGINS', []) or []
    base = (origins[0] if origins else 'http://127.0.0.1:5173').rstrip('/')
    return {
        'success_url': f'{base}/membership?checkout=success',
        'cancel_url': f'{base}/membership?checkout=cancelled',
    }


def create_checkout_session(
    user,
    plan,
    *,
    months=1,
    membership_id=None,
    success_url='',
    cancel_url='',
):
    """Start a Stripe Checkout Session for a membership purchase.

    Returns (result_dict, error_message).
    """
    if not stripe_enabled():
        return None, 'Stripe is not configured.'

    from scheduling.services.payments import create_pending_payment, validate_checkout_plan

    error = validate_checkout_plan(user, plan, months=months, membership_id=membership_id)
    if error:
        return None, error

    defaults = frontend_checkout_urls()
    success_url = success_url or defaults['success_url']
    cancel_url = cancel_url or defaults['cancel_url']

    payment = create_pending_payment(
        user,
        plan,
        months=months,
        membership_id=membership_id,
    )

    payload = {
        'mode': 'payment',
        'success_url': success_url,
        'cancel_url': cancel_url,
        'client_reference_id': str(payment.id),
        'metadata[payment_id]': str(payment.id),
        'metadata[user_id]': str(user.id),
        'metadata[plan_id]': str(plan.id),
        'metadata[months]': str(months),
        'line_items[0][price_data][currency]': 'usd',
        'line_items[0][price_data][unit_amount]': plan.price_cents,
        'line_items[0][price_data][product_data][name]': plan.name,
        'line_items[0][quantity]': months,
    }
    if membership_id is not None:
        payload['metadata[membership_id]'] = str(membership_id)

    try:
        session = stripe_api_request('POST', '/checkout/sessions', payload)
    except RuntimeError as exc:
        from scheduling.models import Payment
        payment.status = Payment.STATUS_FAILED
        payment.save(update_fields=['status'])
        return None, str(exc)

    payment.stripe_checkout_session_id = session.get('id', '')
    payment.save(update_fields=['stripe_checkout_session_id'])

    checkout_url = session.get('url')
    if not checkout_url:
        return None, 'Stripe did not return a checkout URL.'

    return {
        'checkout_url': checkout_url,
        'session_id': session.get('id'),
        'payment_id': payment.id,
    }, None
