"""DRF rate limits — scoped throttles for auth endpoints (audit Phase 6)."""

from rest_framework.throttling import SimpleRateThrottle


class LoginRateThrottle(SimpleRateThrottle):
    """Limit POST /api/auth/token/ attempts by client IP."""

    scope = 'login'

    def get_cache_key(self, request, view):
        return self.cache_format % {
            'scope': self.scope,
            'ident': self.get_ident(request),
        }


class TokenRefreshRateThrottle(SimpleRateThrottle):
    """Limit POST /api/auth/token/refresh/ by client IP."""

    scope = 'token_refresh'

    def get_cache_key(self, request, view):
        return self.cache_format % {
            'scope': self.scope,
            'ident': self.get_ident(request),
        }
