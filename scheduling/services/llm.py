"""Studio LLM configuration and teacher-facing AI helpers."""

from django.contrib.auth import get_user_model

from integrations.llm.client import chat_completion
from integrations.llm.errors import LLMError
from integrations.llm.url_validation import validate_llm_url
from scheduling.models import StudioLLMConfig
from scheduling.services.teacher_permissions import teacher_can, user_is_staff

User = get_user_model()

PROVIDER_DEFAULTS = {
    StudioLLMConfig.PROVIDER_OPENAI: {
        'base_url': '',
        'model_name': 'gpt-4o-mini',
    },
    StudioLLMConfig.PROVIDER_ANTHROPIC: {
        'base_url': '',
        'model_name': 'claude-sonnet-4-20250514',
    },
    StudioLLMConfig.PROVIDER_OLLAMA: {
        'base_url': 'http://127.0.0.1:11434',
        'model_name': 'llama3.2',
    },
    StudioLLMConfig.PROVIDER_OPENAI_COMPATIBLE: {
        'base_url': '',
        'model_name': 'gpt-4o-mini',
    },
}

PROVIDER_LABELS = dict(StudioLLMConfig.PROVIDER_CHOICES)


def get_llm_config():
    return StudioLLMConfig.load()


def _mask_api_key(api_key):
    if not api_key:
        return ''
    if len(api_key) <= 4:
        return '••••'
    return f'••••{api_key[-4:]}'


def llm_config_for_api():
    config = get_llm_config()
    return {
        'provider': config.provider,
        'provider_label': PROVIDER_LABELS.get(config.provider, config.provider),
        'base_url': config.base_url,
        'model_name': config.model_name,
        'is_enabled': config.is_enabled,
        'max_tokens': config.max_tokens,
        'has_api_key': bool(config.api_key),
        'api_key_masked': _mask_api_key(config.api_key),
        'providers': [
            {'value': value, 'label': label}
            for value, label in StudioLLMConfig.PROVIDER_CHOICES
        ],
    }


def _credentials_ready(config):
    if config.provider == StudioLLMConfig.PROVIDER_OLLAMA:
        return True
    return bool(config.api_key.strip())


def studio_llm_ready():
    config = get_llm_config()
    return config.is_enabled and _credentials_ready(config)


def ai_available_for_user(user):
    """Studio AI on + configured + teacher has use_ai (staff always)."""
    if not user.is_authenticated:
        return False
    if user_is_staff(user):
        return studio_llm_ready()
    if not user.groups.filter(name='teacher').exists():
        return False
    return studio_llm_ready() and teacher_can(user, 'use_ai')


def update_llm_config(*, provider=None, api_key=None, base_url=None, model_name=None, is_enabled=None, max_tokens=None):
    config = get_llm_config()
    if provider is not None and provider in dict(StudioLLMConfig.PROVIDER_CHOICES):
        config.provider = provider
    if api_key is not None and api_key.strip() and api_key.strip() != '__unchanged__':
        config.api_key = api_key.strip()
    if base_url is not None:
        cleaned_url = base_url.strip()
        try:
            validate_llm_url(cleaned_url, provider=config.provider)
        except LLMError as exc:
            return None, str(exc)
        config.base_url = cleaned_url
    if model_name is not None:
        config.model_name = model_name.strip() or config.model_name
    if is_enabled is not None:
        config.is_enabled = bool(is_enabled)
    if max_tokens is not None:
        try:
            config.max_tokens = max(50, min(int(max_tokens), 4000))
        except (TypeError, ValueError):
            return None, 'max_tokens must be a number.'
    try:
        validate_llm_url(config.base_url, provider=config.provider)
    except LLMError as exc:
        return None, str(exc)
    config.save()
    return config, None


def test_llm_connection():
    config = get_llm_config()
    if not _credentials_ready(config):
        return False, 'Add an API key (or use Ollama on localhost).'
    try:
        text = chat_completion(
            provider=config.provider,
            api_key=config.api_key,
            base_url=config.base_url,
            model=config.model_name,
            messages=[
                {'role': 'user', 'content': 'Reply with exactly the word: connected'},
            ],
            max_tokens=20,
        )
        if not text:
            return False, 'Empty response from the model.'
        return True, text[:200]
    except LLMError as exc:
        return False, str(exc)[:500]


def suggest_feedback_notes(*, student, session=None, scores=None, metric_labels=None):
    """Draft class notes for a session feedback form."""
    config = get_llm_config()
    if not config.is_enabled:
        return None, 'Studio AI is disabled. Ask staff to enable it in AI settings.'

    score_lines = []
    for key, value in (scores or {}).items():
        label = (metric_labels or {}).get(key, key)
        score_lines.append(f'- {label}: {value}')

    session_line = ''
    if session is not None:
        subject = ''
        if session.class_offering_id and session.class_offering:
            subject = session.class_offering.subject
        session_line = (
            f'Session: {session.title}\n'
            f'Subject: {subject or "unknown"}\n'
            f'Date: {session.start_time:%Y-%m-%d}\n'
        )

    user_prompt = (
        f'Student: {student.username}\n'
        f'{session_line}'
        f'Skill scores:\n' + ('\n'.join(score_lines) if score_lines else '- (no scores yet)') + '\n\n'
        'Write 2–4 sentences of constructive class notes for the student. '
        'Be specific, encouraging, and professional. Do not invent scores or facts not listed.'
    )

    try:
        text = chat_completion(
            provider=config.provider,
            api_key=config.api_key,
            base_url=config.base_url,
            model=config.model_name,
            messages=[
                {
                    'role': 'system',
                    'content': (
                        'You help music and language teachers write brief progress notes '
                        'after lessons. Output plain text only — no markdown or bullet lists.'
                    ),
                },
                {'role': 'user', 'content': user_prompt},
            ],
            max_tokens=config.max_tokens,
        )
        return text, None
    except LLMError as exc:
        return None, str(exc)[:500]
