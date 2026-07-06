"""Stripe HTTP helpers (stdlib only — no stripe SDK required)."""

import hashlib
import hmac
import json
import time
import urllib.error
import urllib.request
from urllib.parse import urlencode

from django.conf import settings


def stripe_enabled():
    return settings.STRIPE.get('ENABLED', False)


def stripe_api_request(method, path, payload=None):
    """Call the Stripe REST API."""
    if not stripe_enabled():
        return None
    secret = settings.STRIPE['SECRET_KEY']
    url = f'https://api.stripe.com/v1{path}'
    data = None
    headers = {
        'Authorization': f'Bearer {secret}',
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    if payload is not None:
        data = urlencode(payload).encode()
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()
        raise RuntimeError(f'Stripe API error {exc.code}: {body}') from exc


def verify_webhook_signature(payload, signature_header, *, tolerance=300):
    """Verify Stripe-Signature header against the raw request body."""
    secret = settings.STRIPE.get('WEBHOOK_SECRET', '')
    if not secret or not signature_header:
        return False

    timestamp = None
    signatures = []
    for item in signature_header.split(','):
        key, _, value = item.partition('=')
        if key == 't':
            timestamp = value
        elif key == 'v1':
            signatures.append(value)

    if not timestamp or not signatures:
        return False

    try:
        if abs(time.time() - int(timestamp)) > tolerance:
            return False
    except ValueError:
        return False

    signed_payload = f'{timestamp}.{payload.decode("utf-8") if isinstance(payload, bytes) else payload}'
    # Stripe uses the whole whsec_* secret string as the HMAC key — no decoding.
    expected = hmac.new(
        secret.encode('utf-8'),
        signed_payload.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()
    return any(hmac.compare_digest(expected, signature) for signature in signatures)
