"""Per-student curriculum tracks: templates, enroll, skip/complete modules."""

from django.db import transaction
from django.utils import timezone

from scheduling.models import (
    CurriculumModule,
    CurriculumTrack,
    StudentCurriculum,
    StudentModuleProgress,
)
from scheduling.services.roster import teacher_can_manage_student
from scheduling.services.teacher_permissions import user_is_staff


def list_templates():
    return (
        CurriculumTrack.objects.filter(is_template=True, is_active=True)
        .prefetch_related('modules')
        .order_by('title')
    )


def list_staff_tracks():
    return CurriculumTrack.objects.prefetch_related('modules').order_by('-is_template', 'title')


def get_track(track_id):
    return CurriculumTrack.objects.prefetch_related('modules').filter(pk=track_id).first()


def get_active_enrollment(student):
    return (
        StudentCurriculum.objects.filter(student=student, is_active=True)
        .select_related('track')
        .prefetch_related('track__modules')
        .first()
    )


def _replace_modules(track, modules_data):
    track.modules.all().delete()
    created = []
    for index, row in enumerate(modules_data or []):
        title = (row.get('title') or '').strip()
        if not title:
            continue
        created.append(
            CurriculumModule.objects.create(
                track=track,
                title=title[:200],
                content=(row.get('content') or '').strip(),
                sort_order=row.get('sort_order', index),
            ),
        )
    return created


def create_track(*, title, description='', is_template=False, is_active=True, created_by=None, modules=None):
    title = (title or '').strip()
    if not title:
        return None, 'Title is required.'
    track = CurriculumTrack.objects.create(
        title=title[:200],
        description=(description or '').strip(),
        is_template=bool(is_template),
        is_active=bool(is_active),
        created_by=created_by,
    )
    _replace_modules(track, modules)
    track = get_track(track.id)
    return track, None


def update_track(track, *, title=None, description=None, is_template=None, is_active=None, modules=None):
    if title is not None:
        title = title.strip()
        if not title:
            return None, 'Title is required.'
        track.title = title[:200]
    if description is not None:
        track.description = description.strip()
    if is_template is not None:
        track.is_template = bool(is_template)
    if is_active is not None:
        track.is_active = bool(is_active)
    track.save()
    if modules is not None:
        _replace_modules(track, modules)
    return get_track(track.id), None


def delete_track(track):
    track.delete()


@transaction.atomic
def enroll_student(student, track, actor=None):
    if track is None or not track.is_active:
        return None, 'That curriculum is not available.'
    StudentCurriculum.objects.filter(student=student, is_active=True).update(is_active=False)
    enrollment = StudentCurriculum.objects.create(
        student=student,
        track=track,
        is_active=True,
        started_at=timezone.now(),
    )
    StudentModuleProgress.objects.filter(
        student=student,
        module__track=track,
    ).delete()
    return enrollment, None


def enroll_student_on_template(student, track):
    if track is None or not track.is_template or not track.is_active:
        return None, 'Pick a published studio curriculum.'
    return enroll_student(student, track)


def can_view_student_curriculum(viewer, student):
    if user_is_staff(viewer):
        return True
    if viewer.id == student.id:
        return True
    return teacher_can_manage_student(viewer, student)


def module_status_map(student, track):
    rows = StudentModuleProgress.objects.filter(student=student, module__track=track)
    return {row.module_id: row.status for row in rows}


def serialize_enrollment(enrollment, student=None):
    if enrollment is None:
        return None
    student = student or enrollment.student
    track = enrollment.track
    statuses = module_status_map(student, track)
    modules = []
    current_id = None
    for module in track.modules.all():
        status = statuses.get(module.id, StudentModuleProgress.STATUS_PENDING)
        modules.append({
            'id': module.id,
            'title': module.title,
            'content': module.content,
            'sort_order': module.sort_order,
            'status': status,
        })
        if current_id is None and status == StudentModuleProgress.STATUS_PENDING:
            current_id = module.id
    for row in modules:
        row['is_current'] = row['id'] == current_id
    return {
        'id': enrollment.id,
        'started_at': enrollment.started_at.isoformat(),
        'track': {
            'id': track.id,
            'title': track.title,
            'description': track.description,
            'is_template': track.is_template,
            'is_active': track.is_active,
            'modules': modules,
        },
    }


def serialize_track(track, *, include_modules=True):
    data = {
        'id': track.id,
        'title': track.title,
        'description': track.description,
        'is_template': track.is_template,
        'is_active': track.is_active,
        'module_count': track.modules.count() if not include_modules else len(track.modules.all()),
    }
    if include_modules:
        data['modules'] = [
            {
                'id': module.id,
                'title': module.title,
                'content': module.content,
                'sort_order': module.sort_order,
            }
            for module in track.modules.all()
        ]
    return data


def set_module_progress(student, module, status, actor=None):
    allowed = {
        StudentModuleProgress.STATUS_PENDING,
        StudentModuleProgress.STATUS_COMPLETED,
        StudentModuleProgress.STATUS_SKIPPED,
    }
    if status not in allowed:
        return None, 'Status must be pending, completed, or skipped.'
    enrollment = get_active_enrollment(student)
    if enrollment is None or enrollment.track_id != module.track_id:
        return None, 'This student is not on that curriculum.'
    row, _ = StudentModuleProgress.objects.update_or_create(
        student=student,
        module=module,
        defaults={'status': status, 'updated_by': actor},
    )
    return row, None


def skip_module(student, module, actor=None):
    return set_module_progress(student, module, StudentModuleProgress.STATUS_SKIPPED, actor=actor)


def complete_module(student, module, actor=None):
    return set_module_progress(student, module, StudentModuleProgress.STATUS_COMPLETED, actor=actor)


@transaction.atomic
def create_custom_track_for_students(*, teacher, title, description='', modules=None, students=None):
    """Teacher-made track (not a template) enrolled onto roster students."""
    track, err = create_track(
        title=title,
        description=description,
        is_template=False,
        created_by=teacher,
        modules=modules,
    )
    if err:
        return None, err, []
    enrolled = []
    skipped = []
    for student in students or []:
        if not teacher_can_manage_student(teacher, student):
            skipped.append(student.username)
            continue
        enrollment, enroll_err = enroll_student(student, track, actor=teacher)
        if enroll_err:
            skipped.append(student.username)
        else:
            enrolled.append(enrollment)
    return track, None, {'enrolled_count': len(enrolled), 'skipped': skipped}
