from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden
from scheduling.forms import SessionForm
from scheduling.models import Session
from scheduling.services.booking import create_booking
from django.views.decorators.http import require_POST

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

@login_required
def teacher_create_session(request):
    user = request.user
    if user.groups.filter(name="teacher").exists():
        if request.method == "POST":
            form = SessionForm(request.POST)
            if form.is_valid():
                session =form.save(commit=False)
                session.teacher = user
                session.status = 'open'
                session.save()
                return redirect("teacher_dashboard")
        else: 
            form = SessionForm()
        
        return render(request, "scheduling/create_session.html", {"form": form})

    else:
        return HttpResponseForbidden("You don't have access to this page.")

@login_required
@require_POST
def student_book_session(request, session_id):
    user = request.user
    if user.groups.filter(name="student").exists():
        session = get_object_or_404(Session, pk=session_id)
        if create_booking(user, session):
            return redirect("student_dashboard")
        else:
            return redirect("student_dashboard")
    else:
        return HttpResponseForbidden("You don't have access to this page.")