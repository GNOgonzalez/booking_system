"""Adaptive curriculum: read session reports, propose next steps, apply on teacher approval.

Suggestions are proposals only. Nothing on a student's track changes until a teacher
(or staff) accepts one through ``apply_suggestion``.
"""

from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from progress.models import SessionFeedback
from progress.services import feedback_scores, get_score_dimensions
from scheduling.models import (
    CurriculumSuggestion,
    StudentModuleProgress,
    StudentSupplementaryMaterial,
)
from scheduling.services.curriculum import (
    complete_module,
    get_active_enrollment,
    module_status_map,
)

WEAK_RATIO = 0.6
MAX_FEEDBACK_ROWS = 20
MAX_SUGGESTIONS_PER_RUN = 3
UPCOMING_MODULE_COUNT = 5
NOTE_EXCERPT_COUNT = 3
NOTE_EXCERPT_CHARS = 300


def _clean_days(days, default=90):
    try:
        days = int(days)
    except (TypeError, ValueError):
        return default
    return max(1, min(days, 365))


def _dimension_ranges(teacher, subject):
    return {
        dim.key: {'label': dim.label, 'min': dim.min_score, 'max': dim.max_score}
        for dim in get_score_dimensions(teacher, subject)
    }


def _module_row(module, status):
    return {
        'id': module.id,
        'title': module.title,
        'sort_order': module.sort_order,
        'cefr_level': module.cefr_level,
        'skill_keys': module.skill_keys or [],
        'status': status,
    }


def _track_state(student):
    """Active enrollment's modules with status, plus the current (first pending) module."""
    enrollment = get_active_enrollment(student)
    if enrollment is None:
        return None, [], None
    statuses = module_status_map(student, enrollment.track)
    rows = [
        _module_row(module, statuses.get(module.id, StudentModuleProgress.STATUS_PENDING))
        for module in enrollment.track.modules.all()
    ]
    current = next((row for row in rows if row['status'] == StudentModuleProgress.STATUS_PENDING), None)
    return enrollment, rows, current


def student_learning_signals(student, *, teacher=None, subject='', days=90):
    """What recent reports say about a student, alongside where they are on their track.

    With a teacher, reports on sessions hidden from peers are left out unless that
    teacher taught the session or wrote the report (same rule as session history).
    """
    days = _clean_days(days)
    since = timezone.now() - timedelta(days=days)
    feedback_qs = (
        SessionFeedback.objects.filter(student=student, created_at__gte=since)
        .select_related('session__class_offering')
        .order_by('-created_at')
    )
    if subject:
        feedback_qs = feedback_qs.filter(session__class_offering__subject__iexact=subject)
    if teacher is not None:
        hidden = Q(session__history_privacy__hidden_by_student=True) | Q(
            session__history_privacy__hidden_by_teacher=True
        )
        own = Q(teacher=teacher) | Q(session__teacher=teacher)
        feedback_qs = feedback_qs.exclude(hidden & ~own)
    feedback_rows = list(feedback_qs[:MAX_FEEDBACK_ROWS])

    ranges = _dimension_ranges(teacher, subject)
    totals = {}
    for feedback in feedback_rows:
        for key, value in feedback_scores(feedback).items():
            totals.setdefault(key, []).append(value)

    dimensions = []
    for key, values in totals.items():
        info = ranges.get(key, {'label': key.replace('_', ' ').title(), 'min': 0, 'max': 5})
        span = max(info['max'], 1)
        average = sum(values) / len(values)
        ratio = average / span
        dimensions.append({
            'key': key,
            'label': info['label'],
            'average': round(average, 2),
            'max': info['max'],
            'ratio': round(ratio, 2),
            'count': len(values),
            'is_weak': ratio < WEAK_RATIO,
        })
    dimensions.sort(key=lambda row: row['ratio'])

    notes = [
        {
            'feedback_id': feedback.id,
            'date': feedback.created_at.date().isoformat(),
            'excerpt': feedback.class_notes.strip()[:NOTE_EXCERPT_CHARS],
        }
        for feedback in feedback_rows
        if feedback.class_notes.strip()
    ][:NOTE_EXCERPT_COUNT]

    enrollment, modules, current = _track_state(student)
    upcoming = [
        row for row in modules
        if row['status'] == StudentModuleProgress.STATUS_PENDING
        and (current is None or row['id'] != current['id'])
    ][:UPCOMING_MODULE_COUNT]

    return {
        'student_id': student.id,
        'days': days,
        'subject': subject,
        'report_count': len(feedback_rows),
        'latest_feedback_id': feedback_rows[0].id if feedback_rows else None,
        'dimensions': dimensions,
        'weak_keys': [row['key'] for row in dimensions if row['is_weak']],
        'recent_notes': notes,
        'track': (
            {
                'id': enrollment.track.id,
                'title': enrollment.track.title,
                'framework': enrollment.track.framework,
            }
            if enrollment
            else None
        ),
        'modules': modules,
        'current_module': current,
        'upcoming_modules': upcoming,
    }


def _dimension_phrase(dim):
    return f"{dim['label']} averaged {dim['average']}/{dim['max']} over {dim['count']} report(s)"


def rule_based_suggestions(signals):
    """Proposals (plain dicts, not saved) from weak score areas and track position."""
    proposals = []
    modules = signals['modules']
    current = signals['current_module']
    dims_by_key = {row['key']: row for row in signals['dimensions']}
    used_module_ids = set()

    for key in signals['weak_keys'][:2]:
        dim = dims_by_key[key]
        pending_match = next(
            (
                row for row in modules
                if row['status'] == StudentModuleProgress.STATUS_PENDING
                and key in row['skill_keys']
                and row['id'] not in used_module_ids
            ),
            None,
        )
        if pending_match is not None:
            used_module_ids.add(pending_match['id'])
            proposals.append({
                'kind': CurriculumSuggestion.KIND_SUPPLEMENTARY,
                'title': f"Extra {dim['label'].lower()} practice: {pending_match['title']}",
                'rationale': f"{_dimension_phrase(dim)}. This module targets {dim['label'].lower()}.",
                'content': '',
                'target_module_id': pending_match['id'],
            })
            continue
        done_match = next(
            (
                row for row in reversed(modules)
                if row['status'] == StudentModuleProgress.STATUS_COMPLETED
                and key in row['skill_keys']
                and row['id'] not in used_module_ids
            ),
            None,
        )
        if done_match is not None:
            used_module_ids.add(done_match['id'])
            proposals.append({
                'kind': CurriculumSuggestion.KIND_REVIEW,
                'title': f"Review: {done_match['title']}",
                'rationale': f"{_dimension_phrase(dim)}. Revisit an earlier {dim['label'].lower()} module.",
                'content': '',
                'target_module_id': done_match['id'],
            })

    if current is not None:
        current_is_weak = bool(set(current['skill_keys']) & set(signals['weak_keys']))
        if not current_is_weak:
            upcoming = signals['upcoming_modules']
            next_title = upcoming[0]['title'] if upcoming else None
            if signals['report_count']:
                reason = 'No weak areas on this module’s skills in recent reports.'
            else:
                reason = 'No recent reports yet — accept when the student is ready to move on.'
            proposals.append({
                'kind': CurriculumSuggestion.KIND_NEXT_MODULE,
                'title': (
                    f"Mark “{current['title']}” done and start “{next_title}”"
                    if next_title
                    else f"Mark “{current['title']}” done (last module)"
                ),
                'rationale': reason,
                'content': '',
                'target_module_id': current['id'],
            })

    return proposals


def _llm_proposals(teacher, student, signals):
    """LLM proposals when staff opted in and this teacher may use AI. Returns (list, error)."""
    from scheduling.services.llm import (
        ai_available_for_user,
        get_llm_config,
        suggest_curriculum_steps,
    )

    if teacher is None or not get_llm_config().adaptive_curriculum_enabled:
        return [], None
    if not ai_available_for_user(teacher):
        return [], None
    return suggest_curriculum_steps(student=student, signals=signals, track_modules=signals['modules'])


def _merge_proposals(llm_rows, rule_rows):
    """LLM wording wins when both point at the same kind + module; rules fill the gaps."""
    merged = []
    seen = set()
    for row in llm_rows + rule_rows:
        key = (row['kind'], row.get('target_module_id'))
        if key in seen:
            continue
        seen.add(key)
        merged.append(row)
    return merged[:MAX_SUGGESTIONS_PER_RUN]


def _pending_keys(student):
    return set(
        CurriculumSuggestion.objects.filter(
            student=student,
            status=CurriculumSuggestion.STATUS_PENDING,
        ).values_list('kind', 'target_module_id')
    )


@transaction.atomic
def generate_suggestions(student, *, teacher=None, session=None, feedback=None, subject='', days=90):
    """Create pending suggestions for a student. Returns (created, info)."""
    signals = student_learning_signals(student, teacher=teacher, subject=subject, days=days)
    rule_rows = rule_based_suggestions(signals)
    llm_rows, llm_error = _llm_proposals(teacher, student, signals)
    proposals = _merge_proposals(llm_rows or [], rule_rows)

    if feedback is None and signals['latest_feedback_id']:
        feedback = SessionFeedback.objects.filter(pk=signals['latest_feedback_id']).first()
    if session is None and feedback is not None:
        session = feedback.session

    valid_module_ids = {row['id'] for row in signals['modules']}
    existing = _pending_keys(student)
    created = []
    for row in proposals:
        target_id = row.get('target_module_id')
        if target_id is not None and target_id not in valid_module_ids:
            continue
        if (row['kind'], target_id) in existing:
            continue
        existing.add((row['kind'], target_id))
        created.append(
            CurriculumSuggestion.objects.create(
                student=student,
                teacher=teacher,
                session=session,
                feedback=feedback,
                kind=row['kind'],
                source=row.get('source', CurriculumSuggestion.SOURCE_RULES),
                title=row['title'][:200],
                rationale=row.get('rationale', ''),
                content=row.get('content', ''),
                target_module_id=target_id,
            )
        )
    info = {
        'used_llm': any(s.source == CurriculumSuggestion.SOURCE_LLM for s in created),
        'llm_error': llm_error,
        'signals': signals,
    }
    return created, info


def list_suggestions(student, *, recent=10):
    pending = list(
        CurriculumSuggestion.objects.filter(student=student, status=CurriculumSuggestion.STATUS_PENDING)
        .select_related('target_module')
    )
    resolved = list(
        CurriculumSuggestion.objects.filter(student=student)
        .exclude(status=CurriculumSuggestion.STATUS_PENDING)
        .select_related('target_module', 'resolved_by')
        .order_by('-resolved_at', '-created_at')[:recent]
    )
    return pending, resolved


def get_suggestion(suggestion_id):
    return (
        CurriculumSuggestion.objects.select_related('student', 'target_module')
        .filter(pk=suggestion_id)
        .first()
    )


def _resolve(suggestion, status, actor):
    suggestion.status = status
    suggestion.resolved_by = actor
    suggestion.resolved_at = timezone.now()
    suggestion.save(update_fields=['status', 'resolved_by', 'resolved_at'])


@transaction.atomic
def apply_suggestion(suggestion, actor):
    """Accept a pending suggestion and run its action. Returns (suggestion, error)."""
    suggestion = CurriculumSuggestion.objects.select_for_update().get(pk=suggestion.pk)
    if suggestion.status != CurriculumSuggestion.STATUS_PENDING:
        return None, 'This suggestion was already handled.'
    module = suggestion.target_module

    if suggestion.kind == CurriculumSuggestion.KIND_NEXT_MODULE:
        if module is None:
            return None, 'The module for this suggestion no longer exists.'
        _, err = complete_module(suggestion.student, module, actor=actor)
        if err:
            return None, err
    else:
        content = suggestion.content.strip() or (module.content if module else '')
        StudentSupplementaryMaterial.objects.create(
            student=suggestion.student,
            title=suggestion.title,
            content=content,
            module=module,
            suggestion=suggestion,
            created_by=actor,
        )

    _resolve(suggestion, CurriculumSuggestion.STATUS_ACCEPTED, actor)
    return suggestion, None


def dismiss_suggestion(suggestion, actor):
    if suggestion.status != CurriculumSuggestion.STATUS_PENDING:
        return None, 'This suggestion was already handled.'
    _resolve(suggestion, CurriculumSuggestion.STATUS_DISMISSED, actor)
    return suggestion, None


def list_supplementary(student):
    return (
        StudentSupplementaryMaterial.objects.filter(student=student, is_active=True)
        .select_related('module')
    )


def serialize_suggestion(suggestion):
    module = suggestion.target_module
    return {
        'id': suggestion.id,
        'kind': suggestion.kind,
        'kind_label': suggestion.get_kind_display(),
        'status': suggestion.status,
        'source': suggestion.source,
        'title': suggestion.title,
        'rationale': suggestion.rationale,
        'content': suggestion.content,
        'target_module': (
            {'id': module.id, 'title': module.title, 'cefr_level': module.cefr_level}
            if module
            else None
        ),
        'session_id': suggestion.session_id,
        'feedback_id': suggestion.feedback_id,
        'created_at': suggestion.created_at.isoformat(),
        'resolved_at': suggestion.resolved_at.isoformat() if suggestion.resolved_at else None,
        'resolved_by': suggestion.resolved_by.username if suggestion.resolved_by_id else None,
    }


def serialize_supplementary(material):
    module = material.module
    return {
        'id': material.id,
        'title': material.title,
        'content': material.content,
        'module': (
            {'id': module.id, 'title': module.title, 'cefr_level': module.cefr_level}
            if module
            else None
        ),
        'created_at': material.created_at.isoformat(),
    }


def _estimated_band(modules, current):
    if current is not None and current['cefr_level']:
        return current['cefr_level']
    done = [
        row['cefr_level'] for row in modules
        if row['status'] == StudentModuleProgress.STATUS_COMPLETED and row['cefr_level']
    ]
    return done[-1] if done else ''


def periodic_summary(student, *, teacher=None, days=30):
    """Progress over a window: modules finished, score averages, suggestion activity, CEFR band."""
    days = _clean_days(days, default=30)
    since = timezone.now() - timedelta(days=days)
    signals = student_learning_signals(student, teacher=teacher, days=days)
    track_id = signals['track']['id'] if signals['track'] else None

    completed_qs = StudentModuleProgress.objects.none()
    if track_id is not None:
        completed_qs = (
            StudentModuleProgress.objects.filter(
                student=student,
                module__track_id=track_id,
                status=StudentModuleProgress.STATUS_COMPLETED,
                updated_at__gte=since,
            )
            .select_related('module')
            .order_by('updated_at')
        )
    completed = [
        {
            'id': row.module.id,
            'title': row.module.title,
            'cefr_level': row.module.cefr_level,
            'completed_at': row.updated_at.isoformat(),
        }
        for row in completed_qs
    ]

    suggestions = CurriculumSuggestion.objects.filter(student=student)
    modules = signals['modules']
    finished_total = sum(
        1 for row in modules
        if row['status'] in (StudentModuleProgress.STATUS_COMPLETED, StudentModuleProgress.STATUS_SKIPPED)
    )
    return {
        'student_id': student.id,
        'days': days,
        'track': signals['track'],
        'modules_completed': completed,
        'modules_total': len(modules),
        'modules_finished_total': finished_total,
        'report_count': signals['report_count'],
        'dimensions': signals['dimensions'],
        'weak_keys': signals['weak_keys'],
        'open_suggestions': suggestions.filter(status=CurriculumSuggestion.STATUS_PENDING).count(),
        'accepted_in_period': suggestions.filter(
            status=CurriculumSuggestion.STATUS_ACCEPTED,
            resolved_at__gte=since,
        ).count(),
        'dismissed_in_period': suggestions.filter(
            status=CurriculumSuggestion.STATUS_DISMISSED,
            resolved_at__gte=since,
        ).count(),
        'current_module': signals['current_module'],
        'estimated_cefr_band': _estimated_band(modules, signals['current_module']),
    }
