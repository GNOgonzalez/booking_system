"""Progress reporting rules. Views/API call these, not the ORM directly."""

from progress.models import ProgressReport


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
