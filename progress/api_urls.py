from django.urls import path

from progress import api

urlpatterns = [
    path('', api.MyProgressListView.as_view(), name='api_my_progress'),
    path('teacher/', api.TeacherProgressListCreateView.as_view(), name='api_teacher_progress'),
]
