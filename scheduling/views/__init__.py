from scheduling.views.common import require_group, user_in_group
from scheduling.views.dashboard import (
    home,
    staff_dashboard,
    student_dashboard,
    teacher_dashboard,
)
from scheduling.views.messages import curriculum_list, inbox, message_detail
from scheduling.views.student import (
    booking_calendar,
    membership_page,
    membership_purchase,
    student_book_session,
    student_booking_list,
    student_cancel_booking,
    student_session_list,
)
from scheduling.views.teacher import (
    teacher_availability_create,
    teacher_availability_delete,
    teacher_availability_list,
    teacher_class_type_create,
    teacher_class_type_list,
    teacher_create_session,
    teacher_session_list,
)

__all__ = [
    'home',
    'staff_dashboard',
    'student_dashboard',
    'teacher_dashboard',
    'teacher_create_session',
    'teacher_session_list',
    'teacher_availability_list',
    'teacher_availability_create',
    'teacher_availability_delete',
    'teacher_class_type_list',
    'teacher_class_type_create',
    'student_book_session',
    'student_session_list',
    'student_booking_list',
    'student_cancel_booking',
    'booking_calendar',
    'membership_page',
    'membership_purchase',
    'inbox',
    'message_detail',
    'curriculum_list',
    'require_group',
    'user_in_group',
]
