"""Google OAuth 2.0 flow for Calendar access (stdlib only).

State is a signed token carrying the user id, so the browser callback (which has
no JWT) can attach the credential to the right account without trusting input.
"""

import base64
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import timedelta

from django.conf import settings
from django.core import signing
from django.utils import timezone

GOOGLE_AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
CALENDAR_SCOPE = 'https://www.googleapis.com/auth/calendar.events'

STATE_SALT = 'google-oauth-state'
STATE_MAX_AGE_SECONDS = 600


class GoogleOAuthError(Exception):
    pass


def google_enabled():
    return bool(settings.GOOGLE.get('CLIENT_ID')) and bool(settings.GOOGLE.get('CLIENT_SECRET'))


def redirect_uri():
    return settings.GOOGLE.get(
        'REDIRECT_URI',
        'http://127.0.0.1:8000/integrations/google/callback/',
    )


def _encode_origin(origin):
    if not origin:
        return ''
    return base64.urlsafe_b64encode(origin.encode('utf-8')).decode('ascii').rstrip('=')


def _decode_origin(encoded):
    if not encoded:
        return ''
    padding = '=' * (-len(encoded) % 4)
    return base64.urlsafe_b64decode((encoded + padding).encode('ascii')).decode('utf-8')


def make_state(user, frontend_origin=''):
    # Origin URLs contain ":" — base64 keeps the signed payload colon-free for TimestampSigner.
    payload = f'{user.id}|{_encode_origin(frontend_origin)}'
    return signing.TimestampSigner(salt=STATE_SALT).sign(payload)


def parse_oauth_state(state):
    """Return (user_id, frontend_origin) from signed state."""
    try:
        raw = signing.TimestampSigner(salt=STATE_SALT).unsign(
            state, max_age=STATE_MAX_AGE_SECONDS,
        )
    except signing.BadSignature as exc:
        raise GoogleOAuthError('Invalid or expired OAuth state.') from exc
    if '|' in raw:
        user_id_str, origin_encoded = raw.split('|', 1)
        frontend_origin = _decode_origin(origin_encoded)
    else:
        user_id_str, frontend_origin = raw, ''
    try:
        return int(user_id_str), frontend_origin
    except ValueError as exc:
        raise GoogleOAuthError('Invalid or expired OAuth state.') from exc


def user_id_from_state(state):
    user_id, _ = parse_oauth_state(state)
    return user_id


def build_authorization_url(user, frontend_origin=''):
    if not google_enabled():
        raise GoogleOAuthError('Google OAuth is not configured.')
    params = {
        'client_id': settings.GOOGLE['CLIENT_ID'],
        'redirect_uri': redirect_uri(),
        'response_type': 'code',
        'scope': CALENDAR_SCOPE,
        'access_type': 'offline',
        'prompt': 'consent',
        'state': make_state(user, frontend_origin),
    }
    return f'{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}'


def _token_request(payload):
    data = urllib.parse.urlencode(payload).encode()
    request = urllib.request.Request(
        GOOGLE_TOKEN_URL,
        data=data,
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors='replace')
        raise GoogleOAuthError(f'Google token endpoint error {exc.code}: {body[:300]}') from exc
    except urllib.error.URLError as exc:
        raise GoogleOAuthError(f'Cannot reach Google: {exc.reason}') from exc


def exchange_code(code):
    """Exchange an authorization code for tokens. Returns the token dict."""
    if not google_enabled():
        raise GoogleOAuthError('Google OAuth is not configured.')
    return _token_request({
        'code': code,
        'client_id': settings.GOOGLE['CLIENT_ID'],
        'client_secret': settings.GOOGLE['CLIENT_SECRET'],
        'redirect_uri': redirect_uri(),
        'grant_type': 'authorization_code',
    })


def store_credential(user, token_data):
    from scheduling.models import GoogleCredential

    expires_in = int(token_data.get('expires_in', 3600))
    credential, _ = GoogleCredential.objects.update_or_create(
        user=user,
        defaults={
            'access_token': token_data.get('access_token', ''),
            'token_expires_at': timezone.now() + timedelta(seconds=expires_in),
            'scopes': token_data.get('scope', ''),
        },
    )
    # Google only returns refresh_token on first consent — keep the old one otherwise.
    refresh = token_data.get('refresh_token')
    if refresh:
        credential.refresh_token = refresh
        credential.save(update_fields=['refresh_token'])
    return credential


def valid_access_token(user):
    """Return a usable access token for the user, refreshing if needed, or None."""
    from scheduling.models import GoogleCredential

    credential = GoogleCredential.objects.filter(user=user).first()
    if credential is None or not credential.access_token:
        return None

    if credential.token_expires_at and credential.token_expires_at > timezone.now() + timedelta(minutes=2):
        return credential.access_token

    if not credential.refresh_token or not google_enabled():
        return None

    try:
        token_data = _token_request({
            'refresh_token': credential.refresh_token,
            'client_id': settings.GOOGLE['CLIENT_ID'],
            'client_secret': settings.GOOGLE['CLIENT_SECRET'],
            'grant_type': 'refresh_token',
        })
    except GoogleOAuthError:
        return None

    credential.access_token = token_data.get('access_token', '')
    credential.token_expires_at = timezone.now() + timedelta(
        seconds=int(token_data.get('expires_in', 3600)),
    )
    credential.save(update_fields=['access_token', 'token_expires_at', 'updated_at'])
    return credential.access_token or None


def disconnect(user):
    from scheduling.models import GoogleCredential

    GoogleCredential.objects.filter(user=user).delete()


def connection_status(user):
    from scheduling.models import GoogleCredential

    credential = GoogleCredential.objects.filter(user=user).first()
    return {
        'configured': google_enabled(),
        'connected': bool(credential and credential.refresh_token),
        'connected_at': credential.connected_at if credential else None,
    }
