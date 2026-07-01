from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from scheduling.api import views

urlpatterns = [
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('me/', views.MeView.as_view(), name='api_me'),
    path('me/password/', views.PasswordChangeView.as_view(), name='api_password_change'),
    path('sessions/open/', views.OpenSessionListView.as_view(), name='api_open_sessions'),
    path('bookings/', views.MyBookingListView.as_view(), name='api_my_bookings'),
    path('bookings/create/', views.BookingCreateView.as_view(), name='api_booking_create'),
    path('bookings/<int:booking_id>/cancel/', views.BookingCancelView.as_view(), name='api_booking_cancel'),
    path('teacher/sessions/', views.TeacherSessionListCreateView.as_view(), name='api_teacher_sessions'),
    path('teacher/availability/', views.TeacherAvailabilityListCreateView.as_view(), name='api_teacher_availability'),
    path('teacher/availability/<int:pk>/', views.TeacherAvailabilityDeleteView.as_view(), name='api_teacher_availability_delete'),
    path('teacher/class-types/', views.TeacherClassTypeListCreateView.as_view(), name='api_teacher_class_types'),
    path('messages/', views.InboxListView.as_view(), name='api_inbox'),
    path('curriculum/', views.CurriculumListView.as_view(), name='api_curriculum'),
    path('membership/', views.MembershipView.as_view(), name='api_membership'),
]
