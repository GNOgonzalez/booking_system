"""Progress reporting rules. Views/API call these, not the ORM directly."""

import re

from django.utils.text import slugify

from progress.models import ProgressReport, ScoreDimension, SessionFeedback

MAX_SCORE_DIMENSIONS = 10
ABSOLUTE_MIN_SCORE = 0
ABSOLUTE_MAX_SCORE = 100

DEFAULT_SCORE_DIMENSIONS = [
    ('grammar', 'Grammar', 1),
    ('reading', 'Reading', 2),
    ('writing', 'Writing', 3),
    ('speaking', 'Speaking', 4),
]

LEGACY_SCORE_KEYS = {
    'grammar': 'grammar_stars',
    'reading': 'reading_stars',
    'writing': 'writing_stars',
    'speaking': 'speaking_stars',
}


def can_report(teacher):
    return teacher.groups.filter(name='teacher').exists()


def create_report(teacher, student, rating, note='', session=None, skill=None):
    if not can_report(teacher):
        return None
    return ProgressReport.objects.create(
        teacher=teacher,
        student=student,
        rating=rating,
        note=note,
        session=session,
        skill=skill,
    )


def reports_for_student(student):
    return ProgressReport.objects.filter(student=student)


def reports_by_teacher(teacher):
    return ProgressReport.objects.filter(teacher=teacher)


def _normalize_subject(subject):
    return (subject or '').strip()


def _scope_queryset(*, teacher=None, subject=''):
    subject = _normalize_subject(subject)
    qs = ScoreDimension.objects.filter(teacher=teacher, subject=subject)
    return qs


def active_count_for_scope(*, teacher=None, subject=''):
    return _scope_queryset(teacher=teacher, subject=subject).filter(is_active=True).count()


def _clamp_score(value, dimension):
    try:
        val = int(value)
    except (TypeError, ValueError):
        val = dimension.min_score
    return max(dimension.min_score, min(dimension.max_score, val))


def _validate_score_range(min_score, max_score):
    try:
        min_score = int(min_score)
        max_score = int(max_score)
    except (TypeError, ValueError):
        return None, None, 'Min and max must be numbers.'
    if min_score < ABSOLUTE_MIN_SCORE or max_score > ABSOLUTE_MAX_SCORE:
        return None, None, f'Scores must stay between {ABSOLUTE_MIN_SCORE} and {ABSOLUTE_MAX_SCORE}.'
    if min_score >= max_score:
        return None, None, 'Max must be greater than min.'
    return min_score, max_score, None


def ensure_default_score_dimensions():
    """Idempotent seed of studio-wide default score columns (all subjects)."""
    for key, label, sort_order in DEFAULT_SCORE_DIMENSIONS:
        ScoreDimension.objects.get_or_create(
            teacher=None,
            subject='',
            key=key,
            defaults={
                'label': label,
                'sort_order': sort_order,
                'min_score': 0,
                'max_score': 5,
                'is_active': True,
            },
        )


def get_score_dimensions(teacher=None, subject=None):
    """Active dimensions for a subject — subject-specific set, else studio defaults."""
    subject = _normalize_subject(subject)
    if subject:
        specific = (
            ScoreDimension.objects.filter(teacher=None, subject=subject, is_active=True)
            .order_by('sort_order', 'key')
        )
        if specific.exists():
            return specific
        if teacher is not None:
            teacher_specific = (
                ScoreDimension.objects.filter(teacher=teacher, subject=subject, is_active=True)
                .order_by('sort_order', 'key')
            )
            if teacher_specific.exists():
                return teacher_specific

    if teacher is not None:
        custom = (
            ScoreDimension.objects.filter(teacher=teacher, subject='', is_active=True)
            .order_by('sort_order', 'key')
        )
        if custom.exists():
            return custom

    return (
        ScoreDimension.objects.filter(teacher__isnull=True, subject='', is_active=True)
        .order_by('sort_order', 'key')
    )


def list_score_dimensions_for_staff(subject=None, include_inactive=False):
    """All dimension rows staff can manage for a subject scope."""
    subject = _normalize_subject(subject)
    qs = ScoreDimension.objects.filter(teacher__isnull=True, subject=subject).order_by('sort_order', 'key')
    if not include_inactive:
        qs = qs.filter(is_active=True)
    return qs


def list_metric_subjects():
    """Distinct class subjects plus the default (all subjects) option."""
    from scheduling.models import ClassOffering

    subjects = sorted(
        {s for s in ClassOffering.objects.values_list('subject', flat=True) if s}
    )
    return subjects


def _next_sort_order(*, teacher=None, subject=''):
    last = (
        _scope_queryset(teacher=teacher, subject=subject)
        .order_by('-sort_order')
        .values_list('sort_order', flat=True)
        .first()
    )
    return (last or 0) + 1


def _unique_key(label, *, teacher=None, subject=''):
    base = slugify(label) or 'metric'
    base = re.sub(r'[^a-z0-9_-]', '', base.replace('-', '_'))[:40] or 'metric'
    key = base
    n = 2
    while _scope_queryset(teacher=teacher, subject=subject).filter(key=key).exists():
        key = f'{base}_{n}'
        n += 1
    return key


def create_score_dimension(label, *, subject='', sort_order=None, min_score=0, max_score=5, teacher=None):
    subject = _normalize_subject(subject)
    if active_count_for_scope(teacher=teacher, subject=subject) >= MAX_SCORE_DIMENSIONS:
        return None, f'Maximum of {MAX_SCORE_DIMENSIONS} active metrics per subject.'
    if not label or not label.strip():
        return None, 'Label is required.'
    min_score, max_score, range_error = _validate_score_range(min_score, max_score)
    if range_error:
        return None, range_error
    key = _unique_key(label.strip(), teacher=teacher, subject=subject)
    dim = ScoreDimension.objects.create(
        teacher=teacher,
        subject=subject,
        key=key,
        label=label.strip(),
        sort_order=sort_order if sort_order is not None else _next_sort_order(teacher=teacher, subject=subject),
        min_score=min_score,
        max_score=max_score,
        is_active=True,
    )
    return dim, None


def reorder_score_dimensions(ordered_ids, *, subject='', teacher=None):
    """Persist drag-and-drop order — list of dimension IDs in display sequence."""
    subject = _normalize_subject(subject)
    active = list(
        _scope_queryset(teacher=teacher, subject=subject).filter(is_active=True).order_by('sort_order', 'key')
    )
    by_id = {d.id: d for d in active}
    if set(ordered_ids) != set(by_id):
        return False, 'Order must include every active metric for this subject.'
    for index, pk in enumerate(ordered_ids):
        dim = by_id.get(pk)
        if dim is not None:
            dim.sort_order = index + 1
            dim.save(update_fields=['sort_order'])
    return True, None


def delete_score_dimension(dimension):
    """Soft-delete (deactivate) a metric definition."""
    if dimension.teacher_id is not None:
        return False, 'Only studio metrics can be deleted here.'
    dimension.is_active = False
    dimension.save(update_fields=['is_active'])
    return True, None


def feedback_scores(feedback):
    """Normalized score dict for a feedback row."""
    if feedback.scores:
        return {k: int(v) for k, v in feedback.scores.items()}
    legacy = {}
    for key, field in LEGACY_SCORE_KEYS.items():
        legacy[key] = getattr(feedback, field, 0) or 0
    return legacy


def subject_for_session(session):
    if session is None:
        return ''
    offering = getattr(session, 'class_offering', None)
    if offering is not None and offering.subject:
        return offering.subject
    return ''


def apply_feedback_scores(feedback, scores, *, session=None):
    """Validate and persist scores JSON on feedback."""
    subject = subject_for_session(session or feedback.session)
    dims = get_score_dimensions(feedback.teacher, subject)
    dim_by_key = {d.key: d for d in dims}
    allowed = set(dim_by_key)
    cleaned = {}
    for key, value in (scores or {}).items():
        if key not in allowed:
            continue
        cleaned[key] = _clamp_score(value, dim_by_key[key])
    for dim in dims:
        cleaned.setdefault(dim.key, dim.min_score)
    feedback.scores = cleaned
    for key, field in LEGACY_SCORE_KEYS.items():
        if key in cleaned:
            setattr(feedback, field, cleaned[key])
    feedback.save()
    return feedback


def update_session_feedback(feedback, teacher, **fields):
    if not isinstance(feedback, SessionFeedback) or feedback.teacher_id != teacher.id:
        return False, 'Feedback not found.'
    scores = fields.pop('scores', None)
    for key in ('class_notes', 'session', 'student'):
        if key in fields:
            setattr(feedback, key, fields[key])
    if scores is not None:
        apply_feedback_scores(feedback, scores)
    else:
        feedback.save()
    return True, None


def delete_session_feedback(feedback, teacher):
    if feedback.teacher_id != teacher.id:
        return False, 'Feedback not found.'
    feedback.delete()
    return True, None


def _serialize_dimension(dim):
    return {
        'key': dim.key,
        'label': dim.label,
        'sort_order': dim.sort_order,
        'min_score': dim.min_score,
        'max_score': dim.max_score,
    }


def _session_row(session, *, has_feedback=False, include_privacy=False):
    row = {
        'id': session.id,
        'title': session.title,
        'start_time': session.start_time,
        'end_time': session.end_time,
        'teacher_name': session.teacher.username if session.teacher_id else '',
        'status': session.status,
        'has_feedback': has_feedback,
        'class_topic': session.class_topic.title if session.class_topic_id else None,
        'class_topic_id': session.class_topic_id,
    }
    if include_privacy:
        from progress.session_history import privacy_flags

        row['privacy'] = privacy_flags(session)
    return row


def _topic_progress_for_class(offering, sessions):
    """Where a student is in an ordered topic sequence, plus their next class."""
    from django.utils import timezone

    from scheduling.models import Session

    topics = list(offering.topics.all())
    if not offering.topics_ordered or not topics:
        return None

    now = timezone.now()
    completed_ids = set()
    upcoming_by_topic = {}

    for session in sessions:
        if not session.class_topic_id:
            continue
        topic_id = session.class_topic_id
        if session.end_time <= now:
            completed_ids.add(topic_id)
        elif session.status != 'cancelled':
            existing = upcoming_by_topic.get(topic_id)
            if existing is None or session.start_time < existing.start_time:
                upcoming_by_topic[topic_id] = session

    steps = []
    next_topic = None
    for topic in topics:
        if topic.id not in completed_ids and next_topic is None:
            next_topic = topic

    for topic in topics:
        if next_topic is None:
            status = 'completed'
        elif topic.id == next_topic.id:
            status = 'current'
        elif topic.id in completed_ids:
            status = 'completed'
        else:
            status = 'pending'
        steps.append({
            'id': topic.id,
            'title': topic.title,
            'sort_order': topic.sort_order,
            'status': status,
        })

    next_class = None
    if next_topic is not None:
        booked = upcoming_by_topic.get(next_topic.id)
        if booked is not None:
            next_class = {
                'session_id': booked.id,
                'title': booked.title,
                'start_time': booked.start_time,
                'end_time': booked.end_time,
                'teacher_name': booked.teacher.username if booked.teacher_id else '',
                'is_booked': True,
            }
        else:
            open_session = (
                Session.objects.filter(
                    class_offering_id=offering.id,
                    class_topic_id=next_topic.id,
                    status='open',
                    start_time__gt=now,
                )
                .select_related('teacher')
                .order_by('start_time')
                .first()
            )
            if open_session is not None:
                next_class = {
                    'session_id': open_session.id,
                    'title': open_session.title,
                    'start_time': open_session.start_time,
                    'end_time': open_session.end_time,
                    'teacher_name': open_session.teacher.username if open_session.teacher_id else '',
                    'is_booked': False,
                }

    completed_count = 0
    if next_topic is not None:
        for topic in topics:
            if topic.id == next_topic.id:
                break
            if topic.id in completed_ids:
                completed_count += 1
    else:
        completed_count = len(topics)

    position = completed_count + 1 if next_topic is not None else len(topics)
    return {
        'position': min(position, len(topics)),
        'total': len(topics),
        'completed_count': completed_count,
        'all_complete': next_topic is None,
        'steps': steps,
        'next_topic': {
            'id': next_topic.id,
            'title': next_topic.title,
        } if next_topic is not None else None,
        'next_class': next_class,
    }


def student_dashboard(student):
    """Progress metrics and class history grouped by subject."""
    from scheduling.models import Booking

    bookings = (
        Booking.objects.filter(student=student, status='confirmed')
        .select_related('session__class_offering', 'session__class_topic', 'session__teacher', 'session__history_privacy')
        .prefetch_related('session__class_offering__topics')
        .order_by('-session__start_time')
    )
    feedback_rows = list(
        SessionFeedback.objects.filter(student=student)
        .select_related('session__class_offering', 'session__class_topic', 'teacher', 'session', 'session__history_privacy')
        .prefetch_related('session__class_offering__topics')
        .order_by('created_at')
    )
    feedback_by_session = {
        fb.session_id: fb for fb in feedback_rows if fb.session_id is not None
    }

    subjects = set()
    classes_by_subject = {}

    def _ensure_class(subject, offering):
        bucket = classes_by_subject.setdefault(subject, {})
        if offering.id not in bucket:
            bucket[offering.id] = {
                'class_offering_id': offering.id,
                'label': offering.display_name,
                'subject': offering.subject,
                'level': offering.level,
                'focus': offering.focus,
                'topics': [
                    {'id': topic.id, 'title': topic.title, 'sort_order': topic.sort_order}
                    for topic in offering.topics.all()
                ],
                'topics_ordered': offering.topics_ordered,
                'sessions': [],
                '_session_ids': set(),
                '_session_objects': [],
                '_offering': offering,
            }
        return bucket[offering.id]

    for booking in bookings:
        session = booking.session
        if session is None:
            continue
        offering = session.class_offering
        if offering is None or not offering.subject:
            continue
        subject = offering.subject
        subjects.add(subject)
        row = _ensure_class(subject, offering)
        if session.id in row['_session_ids']:
            continue
        row['_session_ids'].add(session.id)
        row['_session_objects'].append(session)
        row['sessions'].append(
            _session_row(session, has_feedback=session.id in feedback_by_session, include_privacy=True)
        )

    for feedback in feedback_rows:
        subject = subject_for_session(feedback.session)
        if not subject:
            continue
        subjects.add(subject)
        session = feedback.session
        offering = session.class_offering if session else None
        if offering is None:
            continue
        row = _ensure_class(subject, offering)
        if session.id not in row['_session_ids']:
            row['_session_ids'].add(session.id)
            row['_session_objects'].append(session)
            row['sessions'].append(
                _session_row(session, has_feedback=True, include_privacy=True)
            )

    dashboard = []
    for subject in sorted(subjects):
        feedback_for_subject = [
            fb for fb in feedback_rows if subject_for_session(fb.session) == subject
        ]
        classes = []
        for row in classes_by_subject.get(subject, {}).values():
            sessions = sorted(row['sessions'], key=lambda s: s['start_time'], reverse=True)
            topic_progress = _topic_progress_for_class(row['_offering'], row['_session_objects'])
            classes.append({
                'class_offering_id': row['class_offering_id'],
                'label': row['label'],
                'subject': row['subject'],
                'level': row['level'],
                'focus': row['focus'],
                'topics': row['topics'],
                'topics_ordered': row['topics_ordered'],
                'topic_progress': topic_progress,
                'session_count': len(sessions),
                'sessions': sessions,
            })
        classes.sort(key=lambda c: c['label'].lower())

        dashboard.append({
            'subject': subject,
            'metrics': [_serialize_dimension(d) for d in get_score_dimensions(None, subject)],
            'feedback_count': len(feedback_for_subject),
            'session_count': sum(c['session_count'] for c in classes),
            'class_count': len(classes),
            'classes': classes,
            'feedback': feedback_for_subject,
        })

    return dashboard
