from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render

from progress.forms import ProgressReportForm
from progress.services import create_report, reports_by_teacher, reports_for_student


@login_required
def progress_student(request):
    if not request.user.groups.filter(name='student').exists():
        return HttpResponseForbidden("You don't have access to this page.")

    reports = reports_for_student(request.user)
    return render(request, 'progress/student_progress.html', {'reports': reports})


@login_required
def progress_teacher(request):
    if not request.user.groups.filter(name='teacher').exists():
        return HttpResponseForbidden("You don't have access to this page.")

    if request.method == 'POST':
        form = ProgressReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            create_report(
                teacher=request.user,
                student=report.student,
                rating=report.rating,
                note=report.note,
                skill=report.skill,
            )
            messages.success(request, 'Progress report saved.')
            return redirect('progress_teacher')
        messages.error(request, 'Could not save report.')
    else:
        form = ProgressReportForm()

    reports = reports_by_teacher(request.user)
    return render(
        request,
        'progress/teacher_progress.html',
        {'form': form, 'reports': reports},
    )
