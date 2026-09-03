"""Read-only integration status for the staff settings panel.

Same contract as payment_settings_status(): report whether something is
configured and what to set, never the secret itself.
"""

from django.conf import settings


def email_settings_status():
    """How email is being delivered right now.

    Only a real SMTP backend with a host counts as live — console, locmem (used
    by the test runner), filebased, and dummy all deliver to nobody.
    """
    backend = settings.EMAIL_BACKEND
    host = getattr(settings, 'EMAIL_HOST', '') or ''
    is_live = backend.endswith('smtp.EmailBackend') and bool(host)
    # 'django.core.mail.backends.console.EmailBackend' -> 'console'
    backend_name = backend.rsplit('.', 2)[-2] if backend.count('.') >= 2 else backend
    return {
        'mode': 'smtp' if is_live else backend_name,
        'is_live': is_live,
        'host': host,
        'port': getattr(settings, 'EMAIL_PORT', None) if is_live else None,
        'use_tls': bool(getattr(settings, 'EMAIL_USE_TLS', False)) if is_live else False,
        # Username is an address, not a credential — the password is never reported.
        'username': getattr(settings, 'EMAIL_HOST_USER', '') or '',
        'password_configured': bool(getattr(settings, 'EMAIL_HOST_PASSWORD', '')),
        'from_address': settings.DEFAULT_FROM_EMAIL,
        'env_keys': [
            'EMAIL_HOST',
            'EMAIL_PORT',
            'EMAIL_HOST_USER',
            'EMAIL_HOST_PASSWORD',
            'EMAIL_USE_TLS',
            'DEFAULT_FROM_EMAIL',
        ],
    }


def google_settings_status():
    """Studio-wide Google status plus which teachers have actually connected."""
    from django.contrib.auth import get_user_model

    from integrations.google.oauth import google_enabled, redirect_uri
    from scheduling.models import GoogleCredential

    User = get_user_model()
    teachers = User.objects.filter(groups__name='teacher', is_active=True).order_by('username')
    connected_ids = set(
        GoogleCredential.objects.exclude(refresh_token='')
        .values_list('user_id', flat=True)
    )
    teacher_rows = [
        {
            'id': teacher.id,
            'username': teacher.username,
            'connected': teacher.id in connected_ids,
        }
        for teacher in teachers
    ]
    return {
        'configured': google_enabled(),
        'client_id_configured': bool(settings.GOOGLE.get('CLIENT_ID')),
        'client_secret_configured': bool(settings.GOOGLE.get('CLIENT_SECRET')),
        'redirect_uri': redirect_uri(),
        'connected_count': sum(1 for row in teacher_rows if row['connected']),
        'teacher_count': len(teacher_rows),
        'teachers': teacher_rows,
        'env_keys': [
            'GOOGLE_CLIENT_ID',
            'GOOGLE_CLIENT_SECRET',
            'GOOGLE_REDIRECT_URI',
        ],
    }


def integrations_status():
    """Everything the staff integrations page needs, in one call."""
    google = google_settings_status()
    email = email_settings_status()
    return {
        'email': email,
        'google': google,
        'summary': {
            'email_live': email['is_live'],
            'google_configured': google['configured'],
            'google_connected': google['connected_count'] > 0,
        },
    }
