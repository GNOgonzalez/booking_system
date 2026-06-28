from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden
from scheduling.forms import SessionForm
from scheduling.models import Session, Booking
from scheduling.services.booking import create_booking
from django.views.decorators.http import require_POST
from django.utils import timezone

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

@login_required
def student_session_list(request):
    user = request.user
    if not user.groups.filter(name="student").exists():
        return HttpResponseForbidden("You don't have access to this page.")

    sessions = Session.objects.filter(status='open', start_time__gte=timezone.now(),)

    return render(request, "scheduling/student_session_list.html", {"sessions": sessions})

@login_required
def teacher_session_list(request):
    user = request.user
    if not user.groups.filter(name="teacher").exists():
        return HttpResponseForbidden("You don't have access to this page.")

    sessions = Session.objects.all()
    my_sessions = sessions.filter(teacher=user)
    
    return render(request, "scheduling/teacher_session_list.html", {"sessions": my_sessions})

@login_required
def student_booking_list(request):
    user = request.user
    if not user.groups.filter(name="student").exists():
        return HttpResponseForbidden("You don't have access to this page.")

    bookings = Booking.objects.filter(student=user, status='confirmed')

    return render(request, "scheduling/student_booking_list.html", {"bookings": bookings})