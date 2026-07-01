from django.urls import path

from progress import views

urlpatterns = [
    path('', views.progress_student, name='progress_student'),
    path('teacher/', views.progress_teacher, name='progress_teacher'),
]
