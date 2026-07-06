from django.urls import path

from progress import api

urlpatterns = [
    path('', api.MyProgressListView.as_view(), name='api_my_progress'),
    path(
        'sessions/<int:session_id>/history-privacy/',
        api.StudentSessionHistoryPrivacyView.as_view(),
        name='api_student_session_history_privacy',
    ),
    path('teacher/', api.TeacherProgressListCreateView.as_view(), name='api_teacher_progress'),
    path('feedback/', api.MySessionFeedbackListView.as_view(), name='api_my_feedback'),
    path('dashboard/', api.MyStudentDashboardView.as_view(), name='api_my_dashboard'),
    path('homework/', api.MyHomeworkListView.as_view(), name='api_my_homework'),
    path('homework/<int:pk>/', api.MyHomeworkDetailView.as_view(), name='api_my_homework_detail'),
    path(
        'homework/<int:pk>/entries/',
        api.MyHomeworkEntryCreateView.as_view(),
        name='api_my_homework_entry',
    ),
    path(
        'homework/entries/<int:entry_id>/download/',
        api.HomeworkAttachmentDownloadView.as_view(),
        name='api_homework_download',
    ),
    path(
        'homework/teacher/',
        api.TeacherHomeworkListCreateView.as_view(),
        name='api_teacher_homework',
    ),
    path(
        'homework/teacher/<int:pk>/',
        api.TeacherHomeworkDetailView.as_view(),
        name='api_teacher_homework_detail',
    ),
    path(
        'homework/teacher/<int:pk>/entries/',
        api.TeacherHomeworkEntryCreateView.as_view(),
        name='api_teacher_homework_entry',
    ),
    path(
        'feedback/teacher/',
        api.TeacherSessionFeedbackListCreateView.as_view(),
        name='api_teacher_feedback',
    ),
    path(
        'feedback/teacher/<int:pk>/',
        api.TeacherSessionFeedbackDetailView.as_view(),
        name='api_teacher_feedback_detail',
    ),
    path('score-dimensions/', api.ScoreDimensionListView.as_view(), name='api_score_dimensions'),
    path(
        'staff/score-dimensions/',
        api.StaffScoreDimensionListCreateView.as_view(),
        name='api_staff_score_dimensions',
    ),
    path(
        'staff/score-dimensions/reorder/',
        api.StaffScoreDimensionReorderView.as_view(),
        name='api_staff_score_dimensions_reorder',
    ),
    path(
        'staff/score-dimensions/meta/',
        api.StaffScoreDimensionMetaView.as_view(),
        name='api_staff_score_dimensions_meta',
    ),
    path(
        'staff/score-dimensions/subjects/',
        api.StaffScoreSubjectsView.as_view(),
        name='api_staff_score_subjects',
    ),
    path(
        'staff/score-dimensions/<int:pk>/',
        api.StaffScoreDimensionDetailView.as_view(),
        name='api_staff_score_dimension_detail',
    ),
    path(
        'staff/teachers/<int:teacher_id>/feedback/',
        api.StaffTeacherFeedbackListCreateView.as_view(),
        name='api_staff_teacher_feedback',
    ),
    path(
        'staff/teachers/<int:teacher_id>/feedback/<int:pk>/',
        api.StaffTeacherFeedbackDetailView.as_view(),
        name='api_staff_teacher_feedback_detail',
    ),
    path(
        'staff/teachers/<int:teacher_id>/students/<int:student_id>/history/',
        api.StaffTeacherStudentHistoryView.as_view(),
        name='api_staff_teacher_student_history',
    ),
    path(
        'staff/teachers/<int:teacher_id>/homework/',
        api.StaffTeacherHomeworkListCreateView.as_view(),
        name='api_staff_teacher_homework',
    ),
    path(
        'staff/teachers/<int:teacher_id>/homework/<int:pk>/',
        api.StaffTeacherHomeworkDetailView.as_view(),
        name='api_staff_teacher_homework_detail',
    ),
    path(
        'staff/teachers/<int:teacher_id>/homework/<int:pk>/entries/',
        api.StaffTeacherHomeworkEntryCreateView.as_view(),
        name='api_staff_teacher_homework_entry',
    ),
]
