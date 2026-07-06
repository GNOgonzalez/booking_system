"""Homework file exchange and journal prompts — business rules for views/API."""

from datetime import timedelta

from django.utils import timezone

from progress.models import HomeworkAssignment, HomeworkEntry
from scheduling.services.markdown import render_safe_markdown

HOMEWORK_FILE_TTL_DAYS = 7


def homework_file_ttl():
    return timedelta(days=HOMEWORK_FILE_TTL_DAYS)


def validate_homework_file(uploaded_file):
    from scheduling.services.uploads import validate_homework_file as _validate
    return _validate(uploaded_file)


def purge_expired_homework_attachments():
    """Delete stored files past their expiry — journal text entries are kept."""
    now = timezone.now()
    removed = 0
    for entry in HomeworkEntry.objects.filter(
        attachment_expires_at__lt=now,
    ).exclude(attachment=''):
        if entry.attachment:
            entry.attachment.delete(save=False)
            removed += 1
        entry.attachment = ''
        entry.attachment_name = ''
        entry.attachment_expires_at = None
        entry.save(update_fields=['attachment', 'attachment_name', 'attachment_expires_at'])
    return removed


def assignment_is_expired(assignment, *, now=None):
    now = now or timezone.now()
    if assignment.kind == HomeworkAssignment.KIND_JOURNAL:
        return False
    return assignment.expires_at is not None and assignment.expires_at < now


def entry_attachment_active(entry, *, now=None):
    now = now or timezone.now()
    if not entry.attachment or not entry.attachment.name:
        return False
    if entry.attachment_expires_at and entry.attachment_expires_at < now:
        return False
    return True


def user_can_view_assignment(user, assignment):
    if not user.is_authenticated:
        return False
    if user.groups.filter(name='staff').exists():
        return True
    if assignment.teacher_id == user.id:
        return True
    if assignment.student_id == user.id:
        return True
    return False


def user_can_post_entry(user, assignment):
    if not user_can_view_assignment(user, assignment):
        return False
    if assignment.teacher_id == user.id or user.groups.filter(name='staff').exists():
        return True
    if assignment.student_id != user.id:
        return False
    if assignment.kind == HomeworkAssignment.KIND_JOURNAL:
        return True
    return not assignment_is_expired(assignment)


def assignments_for_student(student):
    purge_expired_homework_attachments()
    return (
        HomeworkAssignment.objects.filter(student=student)
        .select_related('teacher', 'student', 'session')
        .prefetch_related('entries')
    )


def assignments_for_teacher(teacher):
    purge_expired_homework_attachments()
    return (
        HomeworkAssignment.objects.filter(teacher=teacher)
        .select_related('teacher', 'student', 'session')
        .prefetch_related('entries')
    )


def _validate_homework_session(teacher, student, session):
    from scheduling.models import Booking

    if session is None:
        return 'Session is required.'
    if session.teacher_id != teacher.id:
        return 'Session does not belong to this teacher.'
    if not Booking.objects.filter(
        session=session,
        student=student,
        status='confirmed',
    ).exists():
        return 'Student must have a confirmed booking on this session.'
    return None


def create_homework_assignment(*, teacher, student, session, kind, title='', prompt='', initial_file=None):
    if kind not in (HomeworkAssignment.KIND_FILE, HomeworkAssignment.KIND_JOURNAL):
        return None, 'Invalid homework type.'
    session_error = _validate_homework_session(teacher, student, session)
    if session_error:
        return None, session_error
    if HomeworkAssignment.objects.filter(session=session, student=student).exists():
        return None, 'Homework already exists for this student on this session.'
    prompt = (prompt or '').strip()
    if kind == HomeworkAssignment.KIND_JOURNAL and not prompt:
        return None, 'Journal prompts need instructions for the student.'
    if kind == HomeworkAssignment.KIND_FILE and not prompt and not initial_file:
        return None, 'Add a message or attach a file.'
    if initial_file:
        error = validate_homework_file(initial_file)
        if error:
            return None, error

    expires_at = None
    if kind == HomeworkAssignment.KIND_FILE:
        expires_at = timezone.now() + homework_file_ttl()

    assignment = HomeworkAssignment.objects.create(
        teacher=teacher,
        student=student,
        session=session,
        kind=kind,
        title=(title or '').strip(),
        prompt=prompt,
        expires_at=expires_at,
    )
    if initial_file:
        ok, err = add_homework_entry(
            assignment,
            author=teacher,
            body=prompt,
            uploaded_file=initial_file,
        )
        if not ok:
            assignment.delete()
            return None, err
    return assignment, None


def add_homework_entry(assignment, *, author, body='', uploaded_file=None):
    if not user_can_post_entry(author, assignment):
        return False, 'This homework is closed or you do not have access.'
    body = (body or '').strip()
    if not body and not uploaded_file:
        return False, 'Add a message or attach a file.'
    if uploaded_file:
        if assignment.kind == HomeworkAssignment.KIND_JOURNAL:
            return False, 'Journal entries are text only — no file uploads.'
        if assignment_is_expired(assignment):
            return False, 'This file exchange has expired.'
        error = validate_homework_file(uploaded_file)
        if error:
            return False, error

    entry = HomeworkEntry(
        assignment=assignment,
        author=author,
        body=body,
    )
    if uploaded_file:
        entry.attachment = uploaded_file
        entry.attachment_name = uploaded_file.name
        entry.attachment_expires_at = timezone.now() + homework_file_ttl()
    entry.save()
    return True, None


def serialize_entry(entry, *, request=None):
    active = entry_attachment_active(entry)
    download_url = None
    if active and request is not None:
        download_url = request.build_absolute_uri(
            f'/api/progress/homework/entries/{entry.id}/download/',
        )
    return {
        'id': entry.id,
        'author_id': entry.author_id,
        'author_name': entry.author.username,
        'author_role': (
            'teacher' if entry.author_id == entry.assignment.teacher_id else 'student'
        ),
        'body': entry.body,
        'body_html': render_safe_markdown(entry.body),
        'has_attachment': active,
        'attachment_name': entry.attachment_name if active else '',
        'attachment_expires_at': entry.attachment_expires_at,
        'download_url': download_url,
        'created_at': entry.created_at,
    }


def serialize_assignment(assignment, *, request=None, include_entries=True):
    now = timezone.now()
    expired = assignment_is_expired(assignment)
    data = {
        'id': assignment.id,
        'kind': assignment.kind,
        'title': assignment.title,
        'prompt': assignment.prompt,
        'teacher_id': assignment.teacher_id,
        'teacher_name': assignment.teacher.username,
        'student_id': assignment.student_id,
        'student_name': assignment.student.username,
        'session_id': assignment.session_id,
        'session_title': assignment.session.title if assignment.session_id else '',
        'session_start_time': assignment.session.start_time if assignment.session_id else None,
        'session_subject': (
            assignment.session.class_offering.subject
            if assignment.session_id and assignment.session.class_offering_id
            else ''
        ),
        'created_at': assignment.created_at,
        'expires_at': assignment.expires_at,
        'is_expired': expired,
        'days_remaining': None,
        'entry_count': assignment.entries.count(),
    }
    if assignment.kind == HomeworkAssignment.KIND_FILE and assignment.expires_at:
        delta = assignment.expires_at - now
        data['days_remaining'] = max(0, delta.days)
    if include_entries:
        data['entries'] = [
            serialize_entry(e, request=request) for e in assignment.entries.all()
        ]
    return data
