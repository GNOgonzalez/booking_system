from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from scheduling.forms import AvailabilityBlockForm, SessionForm, SpecialAvailabilityForm
from scheduling.models import AvailabilityBlock, Session, SpecialAvailability
from scheduling.services.availability import session_within_availability
from scheduling.services.meetings import attach_meeting_link
from scheduling.services.sessions import apply_session_defaults
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
            apply_session_defaults(session)
            if not session_within_availability(user, session.start_time, session.end_time):
                messages.error(request, 'Session time is outside your weekly or special-day availability.')
            else:
                session.save()
                if session.meeting_provider != 'none' and not session.meeting_url:
                    attach_meeting_link(session)
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
    special_blocks = SpecialAvailability.objects.filter(teacher=request.user)
    form = AvailabilityBlockForm()
    special_form = SpecialAvailabilityForm()
    return render(
        request,
        'scheduling/teacher_availability_list.html',
        {
            'blocks': blocks,
            'special_blocks': special_blocks,
            'form': form,
            'special_form': special_form,
        },
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
def teacher_special_availability_create(request):
    denied = require_group(request.user, 'teacher')
    if denied:
        return denied

    if request.method == 'POST':
        form = SpecialAvailabilityForm(request.POST)
        if form.is_valid():
            block = form.save(commit=False)
            block.teacher = request.user
            block.save()
            messages.success(request, 'Special availability added.')
        else:
            messages.error(request, 'Could not add special availability.')
    return redirect('teacher_availability_list')


@login_required
@require_POST
def teacher_special_availability_delete(request, block_id):
    denied = require_group(request.user, 'teacher')
    if denied:
        return denied

    block = get_object_or_404(SpecialAvailability, pk=block_id, teacher=request.user)
    block.delete()
    messages.success(request, 'Special availability removed.')
    return redirect('teacher_availability_list')
