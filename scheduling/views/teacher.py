from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from integrations.google.meet import create_meet_link
from scheduling.forms import AvailabilityBlockForm, ClassTypeForm, SessionForm
from scheduling.models import AvailabilityBlock, ClassType, Session
from scheduling.services.availability import session_within_availability
from scheduling.views.common import require_group


@login_required
def teacher_create_session(request):
    denied = require_group(request.user, 'teacher')
    if denied:
        return denied

    user = request.user
    if request.method == 'POST':
        form = SessionForm(request.POST, teacher=user)
        if form.is_valid():
            session = form.save(commit=False)
            session.teacher = user
            session.status = 'open'
            if not session.title and session.class_type:
                session.title = session.class_type.name
            if not session_within_availability(user, session.start_time, session.end_time):
                messages.error(request, 'Session time is outside your availability blocks.')
            else:
                session.save()
                if not session.meeting_url:
                    session.meeting_url = create_meet_link(session)
                    session.save(update_fields=['meeting_url'])
                messages.success(request, 'Session created.')
                return redirect('teacher_session_list')
    else:
        form = SessionForm(teacher=user)

    return render(request, 'scheduling/create_session.html', {'form': form})


@login_required
def teacher_session_list(request):
    denied = require_group(request.user, 'teacher')
    if denied:
        return denied

    sessions = Session.objects.filter(teacher=request.user)
    return render(request, 'scheduling/teacher_session_list.html', {'sessions': sessions})


@login_required
def teacher_availability_list(request):
    denied = require_group(request.user, 'teacher')
    if denied:
        return denied

    blocks = AvailabilityBlock.objects.filter(teacher=request.user)
    form = AvailabilityBlockForm()
    return render(
        request,
        'scheduling/teacher_availability_list.html',
        {'blocks': blocks, 'form': form},
    )


@login_required
def teacher_availability_create(request):
    denied = require_group(request.user, 'teacher')
    if denied:
        return denied

    if request.method == 'POST':
        form = AvailabilityBlockForm(request.POST)
        if form.is_valid():
            block = form.save(commit=False)
            block.teacher = request.user
            block.save()
            messages.success(request, 'Availability block added.')
        else:
            messages.error(request, 'Could not add availability block.')
    return redirect('teacher_availability_list')


@login_required
@require_POST
def teacher_availability_delete(request, block_id):
    denied = require_group(request.user, 'teacher')
    if denied:
        return denied

    block = get_object_or_404(AvailabilityBlock, pk=block_id, teacher=request.user)
    block.delete()
    messages.success(request, 'Availability block removed.')
    return redirect('teacher_availability_list')


@login_required
def teacher_class_type_list(request):
    denied = require_group(request.user, 'teacher')
    if denied:
        return denied

    class_types = ClassType.objects.filter(teacher=request.user)
    form = ClassTypeForm()
    return render(
        request,
        'scheduling/teacher_class_type_list.html',
        {'class_types': class_types, 'form': form},
    )


@login_required
def teacher_class_type_create(request):
    denied = require_group(request.user, 'teacher')
    if denied:
        return denied

    if request.method == 'POST':
        form = ClassTypeForm(request.POST)
        if form.is_valid():
            class_type = form.save(commit=False)
            class_type.teacher = request.user
            class_type.save()
            messages.success(request, 'Class type added.')
        else:
            messages.error(request, 'Could not add class type.')
    return redirect('teacher_class_type_list')
