from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.http import HttpResponseForbidden


@login_required
def teacher_dashboard(request):
    user = request.user

    if user.groups.filter(name="teacher").exists():
        return render(request, "scheduling/teacher_dashboard.html")

    if user.groups.filter(name="student").exists():
        return redirect("student_dashboard") 

    return HttpResponseForbidden("You don't have access to this page.")


@login_required
def student_dashboard(request):
    user = request.user

    if user.groups.filter(name="student").exists():
        return render(request, "scheduling/student_dashboard.html")

    if user.groups.filter(name="teacher").exists():
        return redirect("teacher_dashboard")  

    return HttpResponseForbidden("You don't have access to this page.")