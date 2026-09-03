from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from config.health import healthz, readyz
from scheduling import views
from scheduling.api.google_views import google_oauth_callback

urlpatterns = [
    path('', views.home, name='home'),
    # Both spellings: health checkers differ on the trailing slash.
    path('healthz', healthz, name='healthz'),
    path('healthz/', healthz),
    path('readyz', readyz, name='readyz'),
    path('readyz/', readyz),
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('api/', include('scheduling.api.urls')),
    path('api/progress/', include('progress.api_urls')),
    path('integrations/google/callback/', google_oauth_callback, name='google_oauth_callback'),
    path('teacher/dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('staff/dashboard/', views.staff_dashboard, name='staff_dashboard'),
    path('teacher/sessions/new/', views.teacher_create_session, name='teacher_create_session'),
    path('teacher/sessions/', views.teacher_session_list, name='teacher_session_list'),
    path('teacher/availability/', views.teacher_availability_list, name='teacher_availability_list'),
    path('teacher/availability/new/', views.teacher_availability_create, name='teacher_availability_create'),
    path('teacher/availability/<int:block_id>/delete/', views.teacher_availability_delete, name='teacher_availability_delete'),
    path('teacher/special-availability/new/', views.teacher_special_availability_create, name='teacher_special_availability_create'),
    path('teacher/special-availability/<int:block_id>/delete/', views.teacher_special_availability_delete, name='teacher_special_availability_delete'),
    path('student/sessions/<int:session_id>/book/', views.student_book_session, name='student_book_session'),
    path('student/sessions/', views.student_session_list, name='student_session_list'),
    path('student/bookings/', views.student_booking_list, name='student_booking_list'),
    path('student/bookings/<int:booking_id>/cancel/', views.student_cancel_booking, name='student_cancel_booking'),
    path('student/bookings/<int:booking_id>/calendar.ics', views.booking_calendar, name='booking_calendar'),
    path('student/membership/', views.membership_page, name='membership_page'),
    path('student/membership/purchase/', views.membership_purchase, name='membership_purchase'),
    path('messages/', views.inbox, name='inbox'),
    path('messages/<int:message_id>/', views.message_detail, name='message_detail'),
    path('curriculum/', views.curriculum_list, name='curriculum_list'),
    path('progress/', include('progress.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
