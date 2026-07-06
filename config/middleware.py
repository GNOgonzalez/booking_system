"""Security middleware for Django-served pages (templates, admin, browsable API).

The React SPA is served separately (Vite dev server / static host) and needs its
own CSP at that layer; this protects everything Django renders.
"""

from django.conf import settings


class ContentSecurityPolicyMiddleware:
    """Attach a Content-Security-Policy header when DEBUG is off.

    Skipped in DEBUG because the Vite dev setup and Django debug pages rely on
    inline scripts that a strict policy would break.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not settings.DEBUG and 'Content-Security-Policy' not in response:
            response['Content-Security-Policy'] = settings.CONTENT_SECURITY_POLICY
        return response
