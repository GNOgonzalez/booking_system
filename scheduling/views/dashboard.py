from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from scheduling.views.common import require_group


@login_required
def home(request):
    user = request.user
    if user.groups.filter(name='teacher').exists():
        return redirect('teacher_dashboard')
    if user.groups.filter(name='student').exists():
        return redirect('student_dashboard')
    if user.groups.filter(name='staff').exists():
        return redirect('staff_dashboard')
    return redirect('admin:index')


@login_required
def teacher_dashboard(request):
    denied = require_group(request.user, 'teacher')
    if denied:
        return denied
    if request.user.groups.filter(name='student').exists():
        return redirect('student_dashboard')
    return render(request, 'scheduling/teacher_dashboard.html')


@login_required
def student_dashboard(request):
    denied = require_group(request.user, 'student')
    if denied:
        return denied
    if request.user.groups.filter(name='teacher').exists():
        return redirect('teacher_dashboard')
    return render(request, 'scheduling/student_dashboard.html')


@login_required
def staff_dashboard(request):
    denied = require_group(request.user, 'staff')
    if denied:
        return denied
    return render(request, 'scheduling/staff_dashboard.html')
