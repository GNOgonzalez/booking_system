"""Staff studio reports — financials, bookings, teacher and student stats."""

from collections import defaultdict
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models import Count, Sum
from django.utils import timezone

from scheduling.models import Booking, Membership, Payment, Session
from scheduling.services.payments import payment_mode

User = get_user_model()


def _format_money(cents):
    return {'cents': cents, 'display': f'${cents / 100:,.2f}'}


def staff_reports(*, days=30):
    now = timezone.now()
    since = now - timedelta(days=days)

    payments = Payment.objects.filter(
        status=Payment.STATUS_COMPLETED,
        created_at__gte=since,
    ).select_related('plan', 'user')
    total_revenue_cents = payments.aggregate(total=Sum('amount_cents'))['total'] or 0

    by_plan = defaultdict(lambda: {'count': 0, 'revenue_cents': 0})
    by_provider = defaultdict(int)
    for payment in payments:
        by_plan[payment.plan.name]['count'] += 1
        by_plan[payment.plan.name]['revenue_cents'] += payment.amount_cents
        by_provider[payment.provider] += 1

    recent_payments = [
        {
            'id': p.id,
            'user': p.user.username,
            'plan_name': p.plan.name,
            'amount': _format_money(p.amount_cents),
            'provider': p.provider,
            'created_at': p.created_at,
        }
        for p in payments.order_by('-created_at')[:10]
    ]

    bookings_qs = Booking.objects.filter(created_at__gte=since).select_related(
        'session__class_offering',
        'session__teacher',
        'student',
    )
    confirmed = bookings_qs.filter(status='confirmed').count()
    cancelled = bookings_qs.filter(status='cancelled').count()
    tickets_spent = (
        bookings_qs.filter(status='confirmed').aggregate(total=Sum('tickets_spent'))['total'] or 0
    )

    by_subject = defaultdict(lambda: {'bookings': 0, 'tickets': 0})
    for booking in bookings_qs.filter(status='confirmed'):
        offering = booking.session.class_offering if booking.session_id else None
        subject = offering.subject if offering else 'Unknown'
        by_subject[subject]['bookings'] += 1
        by_subject[subject]['tickets'] += booking.tickets_spent

    booking_by_subject = [
        {'subject': subject, **stats}
        for subject, stats in sorted(by_subject.items(), key=lambda row: -row[1]['bookings'])
    ]

    recent_bookings = [
        {
            'id': b.id,
            'student': b.student.username,
            'session_title': b.session.title if b.session_id else '',
            'teacher': b.session.teacher.username if b.session_id and b.session.teacher_id else '',
            'subject': (
                b.session.class_offering.subject
                if b.session_id and b.session.class_offering_id
                else None
            ),
            'status': b.status,
            'tickets_spent': b.tickets_spent,
            'created_at': b.created_at,
        }
        for b in bookings_qs.order_by('-created_at')[:10]
    ]

    teacher_group = Group.objects.filter(name='teacher').first()
    teacher_rows = []
    if teacher_group:
        for teacher in User.objects.filter(groups=teacher_group).order_by('username'):
            sessions_taught = Session.objects.filter(teacher=teacher, start_time__gte=since).count()
            upcoming = Session.objects.filter(teacher=teacher, start_time__gt=now, status='open').count()
            bookings_received = Booking.objects.filter(
                session__teacher=teacher,
                created_at__gte=since,
                status='confirmed',
            ).count()
            teacher_rows.append({
                'id': teacher.id,
                'username': teacher.username,
                'is_active': teacher.is_active,
                'sessions_in_period': sessions_taught,
                'upcoming_sessions': upcoming,
                'bookings_in_period': bookings_received,
            })
    teacher_rows.sort(key=lambda row: -row['bookings_in_period'])

    student_group = Group.objects.filter(name='student').first()
    students = User.objects.filter(groups=student_group) if student_group else User.objects.none()
    active_students = students.filter(is_active=True).count()
    inactive_students = students.filter(is_active=False).count()
    with_membership = (
        Membership.objects.filter(is_active=True, user__in=students)
        .values('user')
        .distinct()
        .count()
    )
    tickets_remaining = (
        Membership.objects.filter(is_active=True, user__in=students).aggregate(
            total=Sum('tickets_remaining'),
        )['total']
        or 0
    )

    top_students = []
    for row in (
        Booking.objects.filter(created_at__gte=since, status='confirmed', student__in=students)
        .values('student__username', 'student_id')
        .annotate(booking_count=Count('id'), tickets=Sum('tickets_spent'))
        .order_by('-booking_count')[:10]
    ):
        top_students.append({
            'id': row['student_id'],
            'username': row['student__username'],
            'bookings': row['booking_count'],
            'tickets_spent': row['tickets'] or 0,
        })

    try:
        from progress.models import SessionFeedback

        feedback_in_period = SessionFeedback.objects.filter(created_at__gte=since).count()
        for teacher_row in teacher_rows:
            teacher_row['feedback_in_period'] = SessionFeedback.objects.filter(
                teacher_id=teacher_row['id'],
                created_at__gte=since,
            ).count()
    except Exception:
        feedback_in_period = 0
        for teacher_row in teacher_rows:
            teacher_row['feedback_in_period'] = 0

    sessions_in_period = Session.objects.filter(start_time__gte=since).count()
    open_sessions = Session.objects.filter(start_time__gt=now, status='open').count()

    return {
        'period_days': days,
        'generated_at': now,
        'financials': {
            'mode': payment_mode(),
            'total_revenue': _format_money(total_revenue_cents),
            'payment_count': payments.count(),
            'by_plan': [
                {
                    'plan_name': name,
                    'count': stats['count'],
                    'revenue': _format_money(stats['revenue_cents']),
                }
                for name, stats in sorted(by_plan.items(), key=lambda row: -row[1]['revenue_cents'])
            ],
            'by_provider': dict(by_provider),
            'recent_payments': recent_payments,
        },
        'bookings': {
            'total': bookings_qs.count(),
            'confirmed': confirmed,
            'cancelled': cancelled,
            'tickets_spent': tickets_spent,
            'by_subject': booking_by_subject,
            'recent': recent_bookings,
        },
        'sessions': {
            'in_period': sessions_in_period,
            'open_upcoming': open_sessions,
        },
        'teachers': {
            'count': len(teacher_rows),
            'rows': teacher_rows,
        },
        'students': {
            'active': active_students,
            'inactive': inactive_students,
            'with_active_membership': with_membership,
            'tickets_remaining': tickets_remaining,
            'top_by_bookings': top_students,
        },
        'progress': {
            'feedback_in_period': feedback_in_period,
        },
    }
