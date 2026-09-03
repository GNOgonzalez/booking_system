"""
Django settings for config project.

Environment-driven so the same file runs in local dev and production.
Set values in `.env` (see `.env.example`).
"""

import logging
import os
import sys
from datetime import timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).lower() in ('1', 'true', 'yes', 'on')


def env_list(name, default=''):
    raw = os.environ.get(name, default)
    return [item.strip() for item in raw.split(',') if item.strip()]


def _database_from_url(url):
    """Parse postgres:// or postgresql:// URL (Render, Supabase, etc.)."""
    parsed = urlparse(url)
    config = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': parsed.path.lstrip('/') or '',
        'USER': parsed.username or '',
        'PASSWORD': parsed.password or '',
        'HOST': parsed.hostname or '',
        'PORT': str(parsed.port or 5432),
    }
    query = parse_qs(parsed.query)
    sslmode = (query.get('sslmode') or [None])[0]
    if not sslmode and parsed.hostname and 'supabase.co' in parsed.hostname:
        sslmode = 'require'
    if sslmode:
        config['OPTIONS'] = {'sslmode': sslmode}
    return config


# Core
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-8d^&!_0yz299!j+p=wj4y@@xywf_82i9&09t-e*s62-$rv78-a',
)
DEBUG = env_bool('DEBUG', True)
ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', 'localhost,127.0.0.1')
_render_host = os.environ.get('RENDER_EXTERNAL_HOSTNAME', '').strip()
if _render_host and _render_host not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_render_host)

RUNNING_TESTS = 'test' in sys.argv


# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'scheduling',
    'progress',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'config.middleware.ContentSecurityPolicyMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
if RUNNING_TESTS:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'test_db.sqlite3',
        }
    }
elif os.environ.get('DATABASE_URL'):
    DATABASES = {'default': _database_from_url(os.environ['DATABASE_URL'])}
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'booking_dev'),
            'USER': os.environ.get('DB_USER', 'booking_user'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
            'PORT': os.environ.get('DB_PORT', '5432'),
        }
    }


AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# Static files (WhiteNoise for production)
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'
        if not DEBUG
        else 'django.contrib.staticfiles.storage.StaticFilesStorage',
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# User-uploaded files (homework purged after 7 days; blog images kept)
#
# MEDIA PRIVACY (audit Phase 4):
# - Django serves /media/ ONLY when DEBUG=True (config/urls.py). WhiteNoise is static-only.
# - Homework files (media/homework/) are PRIVATE — served exclusively via the authenticated
#   HomeworkAttachmentDownloadView. They must NEVER be exposed by a public /media/ mapping.
# - Blog images (media/blog/) and branding logos (media/branding/) are public-facing.
# - Production: if you map /media/ in nginx/CDN, map ONLY /media/blog/ and /media/branding/.
#   See README "Deploy" section. Longer term: object storage (S3) with private homework bucket.
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
HOMEWORK_FILE_TTL_DAYS = 7
MAX_HOMEWORK_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_BLOG_IMAGE_BYTES = 5 * 1024 * 1024
MAX_LOGO_BYTES = 2 * 1024 * 1024
ALLOWED_HOMEWORK_EXTENSIONS = {
    '.pdf', '.doc', '.docx', '.txt', '.rtf',
    '.png', '.jpg', '.jpeg', '.gif', '.webp',
    '.zip', '.mp3', '.mp4', '.wav', '.m4a',
}
ALLOWED_BLOG_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
ALLOWED_LOGO_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
DATA_UPLOAD_MAX_MEMORY_SIZE = 12 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 12 * 1024 * 1024

LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'


# Email (console in dev; SMTP in prod when EMAIL_HOST is set)
if os.environ.get('EMAIL_HOST'):
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.environ['EMAIL_HOST']
    EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
    EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
    EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '').replace(' ', '')
    EMAIL_USE_TLS = env_bool('EMAIL_USE_TLS', True)
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'no-reply@booking.local')


# DRF + JWT
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
        'scheduling.api.permissions.IsActiveUser',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'login': '10/minute',
        'token_refresh': '30/minute',
    },
}

if RUNNING_TESTS:
    # Full suite issues many token requests from one client IP — keep tests unblocked.
    # AuthRateLimitTests overrides login rate to verify throttling explicitly.
    REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['login'] = '10000/minute'
    REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['token_refresh'] = '10000/minute'

# Tokens live in browser localStorage (see docs/security.md) — keep lifetimes short.
# Refresh defaults to 7 days in dev, 1 day in production; override via env.
JWT_ACCESS_MINUTES = int(os.environ.get('JWT_ACCESS_MINUTES', '60'))
JWT_REFRESH_DAYS = int(os.environ.get('JWT_REFRESH_DAYS', '7' if DEBUG else '1'))

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=JWT_ACCESS_MINUTES),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=JWT_REFRESH_DAYS),
    # Reject valid JWTs from deactivated users at the authentication layer
    # (explicit — this is the library default, but the audit requires it pinned).
    'CHECK_USER_IS_ACTIVE': True,
}


# CORS / CSRF for the React dev server + deployed frontend
CORS_ALLOWED_ORIGINS = env_list(
    'CORS_ALLOWED_ORIGINS',
    'http://127.0.0.1:5173,http://localhost:5173',
)
CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS', '')


# Production hardening (only when DEBUG off)
if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', True)
    # Health probes (Docker HEALTHCHECK, Render) arrive over plain HTTP inside
    # the container; a 301 to https would read as a failure and restart us.
    SECURE_REDIRECT_EXEMPT = [r'^healthz/?$', r'^readyz/?$']
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', '3600'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# Content-Security-Policy for Django-served pages (applied when DEBUG=False via
# config.middleware.ContentSecurityPolicyMiddleware). 'unsafe-inline' styles are
# needed by Django admin and the DRF browsable API; scripts stay 'self'-only.
CONTENT_SECURITY_POLICY = os.environ.get(
    'CSP_POLICY',
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob:; "
    "font-src 'self'; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'",
)


# Integrations (optional; stubs stay inert until configured)
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')

STRIPE = {
    'SECRET_KEY': os.environ.get('STRIPE_SECRET_KEY', ''),
    'PUBLISHABLE_KEY': os.environ.get('STRIPE_PUBLISHABLE_KEY', ''),
    'WEBHOOK_SECRET': STRIPE_WEBHOOK_SECRET,
    'ENABLED': bool(os.environ.get('STRIPE_SECRET_KEY', '')),
}

# Mock membership purchases (POST /api/membership/) are allowed in DEBUG by default.
# In production (DEBUG=False), require Stripe or explicit ALLOW_MOCK_PAYMENTS=true.
ALLOW_MOCK_PAYMENTS = env_bool('ALLOW_MOCK_PAYMENTS', default=False)
if RUNNING_TESTS:
    # Tests may run with DEBUG=False from .env; override_settings can still disable mock.
    ALLOW_MOCK_PAYMENTS = True

GOOGLE = {
    'CLIENT_ID': os.environ.get('GOOGLE_CLIENT_ID', ''),
    'CLIENT_SECRET': os.environ.get('GOOGLE_CLIENT_SECRET', ''),
    'ENABLED': bool(os.environ.get('GOOGLE_CLIENT_ID', '')),
    'REDIRECT_URI': os.environ.get(
        'GOOGLE_REDIRECT_URI',
        'http://127.0.0.1:8000/integrations/google/callback/',
    ),
}

ZOOM = {
    'ACCOUNT_ID': os.environ.get('ZOOM_ACCOUNT_ID', ''),
    'CLIENT_ID': os.environ.get('ZOOM_CLIENT_ID', ''),
    'CLIENT_SECRET': os.environ.get('ZOOM_CLIENT_SECRET', ''),
    'ENABLED': bool(os.environ.get('ZOOM_CLIENT_ID', '')),
}


# Logging — everything to stdout, which is what Render/Docker collect.
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{asctime} {levelname} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': LOG_LEVEL,
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        # 500s: log the traceback instead of only mailing ADMINS.
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'scheduling': {'handlers': ['console'], 'level': LOG_LEVEL, 'propagate': False},
        'progress': {'handlers': ['console'], 'level': LOG_LEVEL, 'propagate': False},
        'integrations': {'handlers': ['console'], 'level': LOG_LEVEL, 'propagate': False},
    },
}


# Error tracking — inert unless SENTRY_DSN is set, and never during tests.
SENTRY_DSN = os.environ.get('SENTRY_DSN', '').strip()
if SENTRY_DSN and not RUNNING_TESTS:
    try:
        import sentry_sdk

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            environment=os.environ.get('SENTRY_ENVIRONMENT', 'production' if not DEBUG else 'development'),
            release=os.environ.get('RENDER_GIT_COMMIT', '') or None,
            traces_sample_rate=float(os.environ.get('SENTRY_TRACES_SAMPLE_RATE', '0')),
            # Student names, emails, and homework are PII; keep them out of Sentry.
            send_default_pii=False,
        )
    except ImportError:
        logging.getLogger(__name__).warning(
            'SENTRY_DSN is set but sentry-sdk is not installed; error tracking is off.'
        )
