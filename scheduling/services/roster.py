"""Staff-managed teacher–student assignments plus booking/feedback roster."""

from django.contrib.auth import get_user_model

from scheduling.models import Booking, TeacherStudentAssignment
from scheduling.services.users import get_student, list_students

User = get_user_model()


def _teacher_qs():
    return User.objects.filter(groups__name='teacher')


def get_teacher_user(teacher_id):
    return _teacher_qs().filter(pk=teacher_id).first()


def teachers_for_student(student):
    ids = TeacherStudentAssignment.objects.filter(student=student).values_list('teacher_id', flat=True)
    return _teacher_qs().filter(pk__in=ids).order_by('username')


def students_for_teacher(teacher):
    ids = TeacherStudentAssignment.objects.filter(teacher=teacher).values_list('student_id', flat=True)
    return list_students().filter(pk__in=ids)


def is_assigned(teacher, student):
    return TeacherStudentAssignment.objects.filter(teacher=teacher, student=student).exists()


def _taught_student_ids(teacher):
    booked = Booking.objects.filter(
        status='confirmed',
        session__teacher=teacher,
    ).values_list('student_id', flat=True)
    from progress.models import SessionFeedback

    feedback = SessionFeedback.objects.filter(teacher=teacher).values_list('student_id', flat=True)
    return set(booked) | set(feedback)


def teacher_can_manage_student(teacher, student):
    """Assigned by staff, or already taught (confirmed booking / feedback)."""
    if not teacher or not student:
        return False
    if not teacher.groups.filter(name='teacher').exists():
        return False
    if is_assigned(teacher, student):
        return True
    return student.id in _taught_student_ids(teacher)


def roster_students_for_teacher(teacher):
    """Students this teacher may manage: assigned union taught."""
    assigned_ids = set(
        TeacherStudentAssignment.objects.filter(teacher=teacher).values_list('student_id', flat=True),
    )
    ids = assigned_ids | _taught_student_ids(teacher)
    if not ids:
        return User.objects.none()
    return list_students().filter(pk__in=ids, is_active=True)


def set_student_teachers(student, teacher_ids, staff_user=None):
    """Replace this student's assigned teachers. Invalid IDs are ignored."""
    wanted = set(
        _teacher_qs().filter(pk__in=teacher_ids, is_active=True).values_list('pk', flat=True),
    )
    current = set(
        TeacherStudentAssignment.objects.filter(student=student).values_list('teacher_id', flat=True),
    )
    TeacherStudentAssignment.objects.filter(student=student, teacher_id__in=(current - wanted)).delete()
    for teacher_id in wanted - current:
        TeacherStudentAssignment.objects.create(
            teacher_id=teacher_id,
            student=student,
            created_by=staff_user,
        )
    return teachers_for_student(student)


def set_teacher_students(teacher, student_ids, staff_user=None):
    """Replace this teacher's assigned students. Invalid IDs are ignored."""
    wanted = set()
    for sid in student_ids:
        student = get_student(sid)
        if student is not None and student.is_active:
            wanted.add(student.id)
    current = set(
        TeacherStudentAssignment.objects.filter(teacher=teacher).values_list('student_id', flat=True),
    )
    TeacherStudentAssignment.objects.filter(teacher=teacher, student_id__in=(current - wanted)).delete()
    for student_id in wanted - current:
        TeacherStudentAssignment.objects.create(
            teacher=teacher,
            student_id=student_id,
            created_by=staff_user,
        )
    return students_for_teacher(teacher)
