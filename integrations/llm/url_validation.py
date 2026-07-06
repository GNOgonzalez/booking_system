"""Validate LLM API base URLs before outbound requests."""

import ipaddress
import socket
from urllib.parse import urlparse

from integrations.llm.errors import LLMError

CLOUD_LLM_HOSTS = frozenset({
    'api.openai.com',
    'api.anthropic.com',
})


def _hostname_resolves_to_private(hostname):
    try:
        for info in socket.getaddrinfo(hostname, None):
            addr = info[4][0]
            ip = ipaddress.ip_address(addr)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return True
    except (OSError, ValueError):
        return True
    return False


def validate_llm_url(url, *, provider):
    """Reject unsafe schemes and private-network targets for cloud providers."""
    if not url:
        if provider == 'ollama':
            return
        return

    parsed = urlparse(url.strip())
    scheme = (parsed.scheme or '').lower()
    if scheme in ('file', 'gopher', 'javascript', 'data'):
        raise LLMError(f'URL scheme "{scheme}" is not allowed for LLM requests.')
    if scheme not in ('http', 'https'):
        raise LLMError('LLM URL must use http or https.')

    hostname = (parsed.hostname or '').lower()
    if not hostname:
        raise LLMError('LLM URL must include a hostname.')

    if provider == 'ollama':
        if scheme != 'http' and not (scheme == 'https' and hostname in ('localhost', '127.0.0.1')):
            raise LLMError('Ollama base URL must use http (or https on localhost).')
        return

    if provider == 'anthropic':
        if hostname != 'api.anthropic.com' or scheme != 'https':
            raise LLMError('Anthropic requests must use https://api.anthropic.com.')
        return

    if provider == 'openai':
        if hostname not in CLOUD_LLM_HOSTS and (scheme != 'https' or _hostname_resolves_to_private(hostname)):
            raise LLMError('OpenAI base URL must be https://api.openai.com or another public HTTPS endpoint.')
        return

    # openai_compatible — https required; block obvious private targets
    if scheme != 'https':
        raise LLMError('OpenAI-compatible base URL must use https.')
    if hostname in ('localhost', '127.0.0.1') or _hostname_resolves_to_private(hostname):
        raise LLMError('OpenAI-compatible base URL must point to a public host.')
