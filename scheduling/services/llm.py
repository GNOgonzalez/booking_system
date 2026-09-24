"""Studio LLM configuration and teacher-facing AI helpers."""

import json

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
        'adaptive_curriculum_enabled': config.adaptive_curriculum_enabled,
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


def update_llm_config(
    *,
    provider=None,
    api_key=None,
    base_url=None,
    model_name=None,
    is_enabled=None,
    max_tokens=None,
    adaptive_curriculum_enabled=None,
):
    config = get_llm_config()
    if adaptive_curriculum_enabled is not None:
        config.adaptive_curriculum_enabled = bool(adaptive_curriculum_enabled)
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


CURRICULUM_KINDS = {'next_module', 'supplementary', 'review'}
MAX_LLM_CURRICULUM_SUGGESTIONS = 3


def _extract_json_object(text):
    """First {...} block in a model reply (models often wrap JSON in prose or fences)."""
    start = text.find('{')
    end = text.rfind('}')
    if start == -1 or end <= start:
        return None
    try:
        return json.loads(text[start:end + 1])
    except ValueError:
        return None


def _curriculum_prompt(student, signals, track_modules):
    dim_lines = [
        f"- {row['label']} ({row['key']}): {row['average']}/{row['max']} over {row['count']} report(s)"
        for row in signals.get('dimensions', [])
    ] or ['- (no scored reports in this window)']
    note_lines = [
        f"- {row['date']}: {row['excerpt']}" for row in signals.get('recent_notes', [])
    ] or ['- (no notes)']

    current = signals.get('current_module')
    listed = ([current] if current else []) + list(signals.get('upcoming_modules', []))
    listed_ids = {row['id'] for row in listed}
    completed = [
        row for row in track_modules
        if row['status'] == 'completed' and row['id'] not in listed_ids
    ][-3:]
    listed += completed

    def module_line(row):
        tag = ' [CURRENT]' if current and row['id'] == current['id'] else ''
        return (
            f"- id={row['id']} | {row['cefr_level'] or '—'} | {row['title']} | "
            f"skills: {', '.join(row['skill_keys']) or 'none'} | {row['status']}{tag}"
        )

    module_lines = [module_line(row) for row in listed] or ['- (student has no active track)']
    prompt = (
        f"Student: {student.username}\n"
        f"Track: {(signals.get('track') or {}).get('title', 'none')}\n\n"
        f"Score averages (last {signals.get('days')} days):\n" + '\n'.join(dim_lines) + '\n\n'
        'Recent teacher notes:\n' + '\n'.join(note_lines) + '\n\n'
        'Modules you may reference (use these ids only):\n' + '\n'.join(module_lines) + '\n\n'
        f'Propose at most {MAX_LLM_CURRICULUM_SUGGESTIONS} next steps. Kinds:\n'
        '- next_module: mark the CURRENT module done so the student moves on (target_module_id = current id)\n'
        '- supplementary: extra practice on a listed module (target_module_id required)\n'
        '- review: revisit a completed module (target_module_id required)\n'
        'Respond with JSON only: {"suggestions": [{"kind": "...", "title": "...", '
        '"rationale": "...", "content": "...", "target_module_id": 123}]}'
    )
    return prompt, {row['id'] for row in listed}


def suggest_curriculum_steps(*, student, signals, track_modules):
    """Ask the studio LLM for curriculum next steps. Returns (proposals, error).

    Proposals use the same dict shape as the rule engine; any module id the model
    was not shown is dropped.
    """
    config = get_llm_config()
    if not config.is_enabled:
        return [], 'Studio AI is disabled.'
    prompt, allowed_ids = _curriculum_prompt(student, signals, track_modules)
    if not allowed_ids:
        return [], None

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
                        'You are a CEFR-aware language tutor helping a teacher plan 1:1 lessons. '
                        'Base every suggestion on the scores and notes provided. Do not claim a '
                        'CEFR level the data does not show. Output a single JSON object and nothing else.'
                    ),
                },
                {'role': 'user', 'content': prompt},
            ],
            max_tokens=config.max_tokens,
        )
    except LLMError as exc:
        return [], str(exc)[:500]

    data = _extract_json_object(text or '')
    if not isinstance(data, dict) or not isinstance(data.get('suggestions'), list):
        return [], 'The AI reply was not valid suggestion JSON.'

    current = signals.get('current_module')
    proposals = []
    for row in data['suggestions']:
        if not isinstance(row, dict):
            continue
        kind = row.get('kind')
        title = str(row.get('title') or '').strip()
        try:
            target_id = int(row.get('target_module_id'))
        except (TypeError, ValueError):
            target_id = None
        if kind not in CURRICULUM_KINDS or not title or target_id not in allowed_ids:
            continue
        if kind == 'next_module' and (current is None or target_id != current['id']):
            continue
        proposals.append({
            'kind': kind,
            'title': title[:200],
            'rationale': str(row.get('rationale') or '').strip(),
            'content': str(row.get('content') or '').strip(),
            'target_module_id': target_id,
            'source': 'llm',
        })
        if len(proposals) >= MAX_LLM_CURRICULUM_SUGGESTIONS:
            break
    return proposals, None
