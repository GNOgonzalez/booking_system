"""Booking tickets — spend and refund credits from a student's membership."""

from scheduling.models import Membership


def session_ticket_cost(session):
    if session.class_offering_id:
        return session.class_offering.ticket_cost
    return 1


def membership_can_afford_session(membership, session):
    if membership is None:
        return False
    return membership.tickets_remaining >= session_ticket_cost(session)


def grant_tickets(membership, amount):
    if amount <= 0:
        return
    membership.tickets_remaining += amount
    membership.save(update_fields=['tickets_remaining'])


def spend_tickets_for_session(membership, session):
    cost = session_ticket_cost(session)
    if membership.tickets_remaining < cost:
        return False, cost
    membership.tickets_remaining -= cost
    membership.save(update_fields=['tickets_remaining'])
    return True, cost


def hold_tickets(membership, amount):
    if amount <= 0 or membership is None:
        return False
    if membership.tickets_remaining < amount:
        return False
    membership.tickets_remaining -= amount
    membership.save(update_fields=['tickets_remaining'])
    return True


def release_tickets(membership, amount):
    grant_tickets(membership, amount)


def refund_booking_tickets(booking):
    if booking.tickets_spent <= 0:
        return
    membership = booking.membership
    if membership is None:
        membership = (
            Membership.objects.filter(user=booking.student, is_active=True)
            .order_by('-valid_until', '-id')
            .first()
        )
    if membership is None:
        membership = Membership.objects.filter(user=booking.student).order_by('-id').first()
    if membership is not None:
        grant_tickets(membership, booking.tickets_spent)
