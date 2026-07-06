from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from scheduling.models import Booking, Session
from scheduling.services.booking import booking_block_reason, cancel_booking, create_booking
from scheduling.services.calendar import session_to_ics
from scheduling.services.membership import active_membership_for
from scheduling.services.payments import get_available_plans, purchase_membership
from scheduling.views.common import require_group


@login_required
@require_POST
def student_book_session(request, session_id):
    denied = require_group(request.user, 'student')
    if denied:
        return denied

    session = get_object_or_404(Session, pk=session_id)
    result = create_booking(request.user, session)
    if result:
        booking, notifications = result
        if notifications['student_email_sent'] and request.user.email:
            messages.success(
                request,
                f'Booked "{session.title}". Confirmation email sent to {request.user.email}.',
            )
        elif request.user.email:
            messages.success(request, f'Booked "{session.title}".')
        else:
            messages.success(
                request,
                f'Booked "{session.title}". Add an email in Profile to receive confirmations.',
            )
        return redirect('student_booking_list')
    reason = booking_block_reason(request.user, session) or 'Could not book that session.'
    messages.error(request, reason)
    return redirect('student_session_list')


@login_required
def student_session_list(request):
    denied = require_group(request.user, 'student')
    if denied:
        return denied

    sessions = Session.objects.filter(
        status='open',
        start_time__gte=timezone.now(),
    )
    return render(request, 'scheduling/student_session_list.html', {'sessions': sessions})


@login_required
def student_booking_list(request):
    denied = require_group(request.user, 'student')
    if denied:
        return denied

    bookings = Booking.objects.filter(student=request.user, status='confirmed')
    return render(request, 'scheduling/student_booking_list.html', {'bookings': bookings})


@login_required
@require_POST
def student_cancel_booking(request, booking_id):
    denied = require_group(request.user, 'student')
    if denied:
        return denied

    booking = get_object_or_404(
        Booking,
        pk=booking_id,
        student=request.user,
        status='confirmed',
    )
    if cancel_booking(request.user, booking):
        messages.success(request, 'Booking cancelled.')
    else:
        messages.error(request, 'Could not cancel that booking.')
    return redirect('student_booking_list')


@login_required
def booking_calendar(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id, student=request.user)
    ics = session_to_ics(booking.session)
    response = HttpResponse(ics, content_type='text/calendar')
    response['Content-Disposition'] = f'attachment; filename="session-{booking.session_id}.ics"'
    return response


@login_required
def membership_page(request):
    denied = require_group(request.user, 'student')
    if denied:
        return denied

    return render(
        request,
        'scheduling/membership.html',
        {
            'membership': active_membership_for(request.user),
            'plans': get_available_plans(),
        },
    )


@login_required
@require_POST
def membership_purchase(request):
    denied = require_group(request.user, 'student')
    if denied:
        return denied

    plan_id = request.POST.get('plan_id')
    if not plan_id:
        messages.error(request, 'Choose a plan.')
        return redirect('membership_page')
    membership, error = purchase_membership(request.user, plan_id=int(plan_id))
    if error:
        messages.error(request, error)
    else:
        messages.success(request, f'{membership.plan.name} membership active.')
    return redirect('membership_page')
