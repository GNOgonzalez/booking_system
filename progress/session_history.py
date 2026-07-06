"""Cross-teacher past session history and privacy rules (audit Phase 16)."""

from django.contrib.auth import get_user_model
from django.utils import timezone

from progress.models import SessionFeedback, SessionHistoryPrivacy
from progress.services import (
    _serialize_dimension,
    _session_row,
    _topic_progress_for_class,
    feedback_scores,
    get_score_dimensions,
    subject_for_session,
)
from scheduling.models import Booking
from scheduling.services.teacher_permissions import user_is_staff

User = get_user_model()

STAFF_PRIVACY_DISCLAIMER = (
    'Other teachers won\'t see this lesson. Studio staff may still access records '
    'for safety and policy reasons.'
)


def privacy_flags(session):
    row = getattr(session, 'history_privacy', None)
    if row is None:
        return {
            'hidden_by_student': False,
            'hidden_by_teacher': False,
            'hidden_from_peers': False,
        }
    return {
        'hidden_by_student': row.hidden_by_student,
        'hidden_by_teacher': row.hidden_by_teacher,
        'hidden_from_peers': row.hidden_from_peers,
    }


def is_past_session(session):
    return session.end_time <= timezone.now()


def teacher_shares_student(viewer, student):
    if not viewer.groups.filter(name='teacher').exists():
        return False
    if Booking.objects.filter(
        student=student,
        status='confirmed',
        session__teacher=viewer,
    ).exists():
        return True
    return SessionFeedback.objects.filter(teacher=viewer, student=student).exists()


def staff_can_view_session(viewer, session=None):
    return user_is_staff(viewer)


def peer_can_view_session(viewer, session, student):
    if session.teacher_id == viewer.id:
        return True
    flags = privacy_flags(session)
    if flags['hidden_from_peers']:
        return False
    return teacher_shares_student(viewer, student)


def _feedback_payload(feedback):
    return {
        'id': feedback.id,
        'teacher_name': feedback.teacher.username,
        'session_id': feedback.session_id,
        'scores': feedback_scores(feedback),
        'class_notes': feedback.class_notes,
        'created_at': feedback.created_at,
    }


def _collect_past_sessions(student):
    bookings = (
        Booking.objects.filter(student=student, status='confirmed')
        .select_related(
            'session__class_offering',
            'session__class_topic',
            'session__teacher',
            'session__history_privacy',
        )
        .prefetch_related('session__class_offering__topics')
        .order_by('-session__start_time')
    )
    feedback_rows = list(
        SessionFeedback.objects.filter(student=student)
        .select_related('session__class_offering', 'session__class_topic', 'teacher', 'session__history_privacy')
        .prefetch_related('session__class_offering__topics')
        .order_by('created_at')
    )
    feedback_by_session = {fb.session_id: fb for fb in feedback_rows if fb.session_id}

    sessions = {}
    for booking in bookings:
        session = booking.session
        if session is None or not is_past_session(session):
            continue
        sessions[session.id] = session
    for fb in feedback_rows:
        if fb.session_id and fb.session and is_past_session(fb.session):
            sessions[fb.session_id] = fb.session

    return sessions, feedback_rows, feedback_by_session


def _build_sections(student, *, viewer, include_hidden_for_staff=False):
    sessions_map, feedback_rows, feedback_by_session = _collect_past_sessions(student)
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
                '_session_objects': [],
                '_offering': offering,
            }
        return bucket[offering.id]

    for session in sessions_map.values():
        offering = session.class_offering
        if offering is None or not offering.subject:
            continue
        if include_hidden_for_staff:
            if not staff_can_view_session(viewer):
                continue
        elif not peer_can_view_session(viewer, session, student):
            continue
        subject = offering.subject
        subjects.add(subject)
        row = _ensure_class(subject, offering)
        session_data = _session_row(session, has_feedback=session.id in feedback_by_session)
        session_data['privacy'] = privacy_flags(session)
        session_data['is_own_session'] = session.teacher_id == getattr(viewer, 'id', None)
        if session.id in feedback_by_session and (
            include_hidden_for_staff
            or session.teacher_id == getattr(viewer, 'id', None)
            or not session_data['privacy']['hidden_from_peers']
        ):
            session_data['feedback'] = _feedback_payload(feedback_by_session[session.id])
        row['sessions'].append(session_data)
        row['_session_objects'].append(session)

    sections = []
    for subject in sorted(subjects):
        feedback_for_subject = [
            fb for fb in feedback_rows if subject_for_session(fb.session) == subject
        ]
        classes = []
        for row in classes_by_subject.get(subject, {}).values():
            sessions = sorted(row['sessions'], key=lambda s: s['start_time'], reverse=True)
            if not sessions:
                continue
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
        visible_feedback = []
        for fb in feedback_for_subject:
            if fb.session_id is None:
                continue
            if include_hidden_for_staff or peer_can_view_session(viewer, fb.session, student):
                visible_feedback.append(fb)
        sections.append({
            'subject': subject,
            'metrics': [_serialize_dimension(d) for d in get_score_dimensions(None, subject)],
            'feedback_count': len(visible_feedback),
            'session_count': sum(c['session_count'] for c in classes),
            'class_count': len(classes),
            'classes': classes,
            'feedback': [_feedback_payload(fb) for fb in visible_feedback],
        })
    return sections


def student_history_for_teacher(viewer, student):
    if not teacher_shares_student(viewer, student):
        return None, 'You do not share this student.'
    return _build_sections(student, viewer=viewer), None


def student_history_for_staff(viewer, student):
    if not staff_can_view_session(viewer):
        return None, 'Staff only.'
    student_obj = User.objects.filter(pk=getattr(student, 'pk', student), groups__name='student').first()
    if student_obj is None:
        return None, 'Student not found.'
    return _build_sections(student_obj, viewer=viewer, include_hidden_for_staff=True), None


def set_session_history_privacy(actor, session, *, hidden_by_student=None, hidden_by_teacher=None):
    if session is None or not is_past_session(session):
        return None, 'Privacy applies to past sessions only.'

    is_staff = user_is_staff(actor)

    if hidden_by_student is not None:
        booked = session.bookings.filter(student=actor, status='confirmed').exists()
        if not booked and not is_staff:
            return None, 'Only the student on this session can change student privacy.'

    if hidden_by_teacher is not None:
        if session.teacher_id != actor.id and not is_staff:
            return None, 'Only the teaching teacher can change teacher privacy on this session.'

    privacy, _ = SessionHistoryPrivacy.objects.get_or_create(session=session)
    if hidden_by_student is not None:
        privacy.hidden_by_student = bool(hidden_by_student)
    if hidden_by_teacher is not None:
        privacy.hidden_by_teacher = bool(hidden_by_teacher)
    privacy.save()
    return privacy, None
