from django.utils import timezone
from scheduling.models import Booking


def can_book(user, session):
    if user.groups.filter(name='student').exists():
        if (session.status == 'open'
        and session.start_time > timezone.now()
        and session.bookings.filter(status='confirmed').count() < session.capacity
        and not Booking.objects.filter(
            student=user,
            session=session,
            status='confirmed'
             #and has_active_membership(user) # TODO: add membership check
        ).exists()
        ):
            return True
        else:
            return False
    else:
        return False

def create_booking(user, session):
    if can_book(user, session):
        Booking.objects.create(
            student=user,
            session=session,
            status='confirmed'
        )
        return True
    else:
        return False
    
    
def can_cancel(user, booking):
    if booking.status != 'confirmed':
        return False
    if user == booking.student:
        return True
    if user == booking.session.teacher:
        return True
    if user.groups.filter(name='staff').exists():
        return True
    return False

def cancel_booking(user, booking):
    if can_cancel(user, booking):
        booking.status = 'cancelled'
        booking.save()
        return True
    else:
        return False