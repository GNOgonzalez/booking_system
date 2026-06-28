"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from scheduling import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('teacher/dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('teacher/sessions/new/', views.teacher_create_session, name='teacher_create_session'),
    path('student/sessions/<int:session_id>/book/', views.student_book_session, name='student_book_session'),
    path('student/sessions/', views.student_session_list, name='student_session_list'),
    path('teacher/sessions/', views.teacher_session_list, name='teacher_session_list'),
    path('student/bookings/', views.student_booking_list, name='student_booking_list'),
]
