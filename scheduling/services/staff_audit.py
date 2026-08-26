"""Audit trail for staff overrides.

Every staff action that changes money, access, or someone else's booking writes a row
here so the studio can answer "who did this, and when?" without database access.
"""

from scheduling.models import StaffActionLog


def log_staff_action(*, actor, action, summary, target_user=None, note='', **detail):
    return StaffActionLog.objects.create(
        actor=actor,
        action=action,
        target_user=target_user,
        summary=summary,
        note=(note or '').strip()[:300],
        detail=detail,
    )


def _serialize(entry):
    return {
        'id': entry.id,
        'action': entry.action,
        'action_label': entry.get_action_display(),
        'actor': entry.actor.username if entry.actor else 'deleted user',
        'target_user': entry.target_user.username if entry.target_user else None,
        'summary': entry.summary,
        'note': entry.note,
        'detail': entry.detail,
        'created_at': entry.created_at,
    }


def list_staff_actions(*, limit=50, target_user=None):
    entries = StaffActionLog.objects.select_related('actor', 'target_user')
    if target_user is not None:
        entries = entries.filter(target_user=target_user)
    limit = max(1, min(limit, 200))
    return [_serialize(entry) for entry in entries[:limit]]
