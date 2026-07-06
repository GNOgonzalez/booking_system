"""HTTP clients for studio-configured LLM providers (stdlib only)."""

import json
import urllib.error
import urllib.request

from integrations.llm.errors import LLMError
from integrations.llm.url_validation import validate_llm_url


def _post_json(url, headers, payload, timeout=60, *, provider='openai'):
    validate_llm_url(url, provider=provider)
    body = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=body, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode('utf-8', errors='replace')
        raise LLMError(detail or f'HTTP {exc.code}') from exc
    except urllib.error.URLError as exc:
        raise LLMError(f'Cannot reach LLM API: {exc.reason}') from exc


def chat_completion(*, provider, api_key, base_url, model, messages, max_tokens=500):
    """Return assistant text from a chat-style LLM."""
    if provider == 'anthropic':
        return _anthropic_chat(api_key=api_key, model=model, messages=messages, max_tokens=max_tokens)
    if provider == 'ollama':
        return _ollama_chat(base_url=base_url, model=model, messages=messages)
    if provider == 'openai_compatible':
        return _openai_chat(
            api_key=api_key,
            base_url=base_url,
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            provider='openai_compatible',
        )
    return _openai_chat(
        api_key=api_key,
        base_url=base_url,
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        provider='openai',
    )


def _openai_chat(*, api_key, base_url, model, messages, max_tokens, provider='openai'):
    root = (base_url or 'https://api.openai.com/v1').rstrip('/')
    url = f'{root}/chat/completions'
    headers = {'Content-Type': 'application/json'}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'
    data = _post_json(url, headers, {
        'model': model,
        'messages': messages,
        'max_tokens': max_tokens,
    }, provider=provider)
    try:
        return data['choices'][0]['message']['content'].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMError('Unexpected response from OpenAI-compatible API.') from exc


def _anthropic_chat(*, api_key, model, messages, max_tokens):
    if not api_key:
        raise LLMError('Anthropic requires an API key.')
    url = 'https://api.anthropic.com/v1/messages'
    headers = {
        'Content-Type': 'application/json',
        'x-api-key': api_key,
        'anthropic-version': '2023-06-01',
    }
    system_parts = [m['content'] for m in messages if m.get('role') == 'system']
    user_messages = [m for m in messages if m.get('role') != 'system']
    payload = {
        'model': model,
        'max_tokens': max_tokens,
        'messages': user_messages,
    }
    if system_parts:
        payload['system'] = '\n\n'.join(system_parts)
    data = _post_json(url, headers, payload, provider='anthropic')
    try:
        blocks = data.get('content') or []
        texts = [b['text'] for b in blocks if b.get('type') == 'text']
        return '\n'.join(texts).strip()
    except (KeyError, TypeError) as exc:
        raise LLMError('Unexpected response from Anthropic API.') from exc


def _ollama_chat(*, base_url, model, messages):
    root = (base_url or 'http://127.0.0.1:11434').rstrip('/')
    url = f'{root}/api/chat'
    headers = {'Content-Type': 'application/json'}
    data = _post_json(url, headers, {
        'model': model,
        'messages': messages,
        'stream': False,
    }, provider='ollama')
    try:
        return data['message']['content'].strip()
    except (KeyError, TypeError) as exc:
        raise LLMError('Unexpected response from Ollama API.') from exc
