"""Liveness and readiness endpoints for the host's health checker.

Deliberately split in two:

- /healthz answers without touching the database. Supabase Free pauses an idle
  project, and Render restarts a service whose health check fails — a
  DB-dependent liveness probe would turn a paused database into a crash loop.
- /readyz does check the database, for deploy verification and debugging.

Both are unauthenticated (no data is exposed) and exempt from CSRF.
"""

import logging

from django.db import connection
from django.http import JsonResponse
from django.views.decorators.cache import never_cache

logger = logging.getLogger(__name__)


@never_cache
def healthz(request):
    """Is the process up? No database, no external calls."""
    return JsonResponse({'status': 'ok'})


@never_cache
def readyz(request):
    """Is the process able to serve real traffic? Includes a database round-trip."""
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
    except Exception as exc:
        logger.warning('Readiness check failed: %s', exc)
        return JsonResponse({'status': 'unavailable', 'database': 'error'}, status=503)
    return JsonResponse({'status': 'ok', 'database': 'ok'})
