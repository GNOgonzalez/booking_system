"""Progress API views — split from former progress/api.py."""

from progress.api.dashboard import (
    MyProgressListView,
    MySessionFeedbackListView,
    MyStudentDashboardView,
    TeacherProgressListCreateView,
)
from progress.api.feedback import (
    TeacherSessionFeedbackDetailView,
    TeacherSessionFeedbackListCreateView,
)
from progress.api.history import (
    StaffTeacherStudentHistoryView,
    StudentSessionHistoryPrivacyView,
    TeacherSessionHistoryPrivacyView,
    TeacherStudentHistoryView,
)
from progress.api.homework import (
    HomeworkAttachmentDownloadView,
    MyHomeworkDetailView,
    MyHomeworkEntryCreateView,
    MyHomeworkListView,
    TeacherHomeworkDetailView,
    TeacherHomeworkEntryCreateView,
    TeacherHomeworkListCreateView,
)
from progress.api.score_dimensions import (
    ScoreDimensionListView,
    StaffScoreDimensionDetailView,
    StaffScoreDimensionListCreateView,
    StaffScoreDimensionMetaView,
    StaffScoreDimensionReorderView,
    StaffScoreSubjectsView,
)
from progress.api.staff import (
    StaffTeacherFeedbackDetailView,
    StaffTeacherFeedbackListCreateView,
    StaffTeacherHomeworkDetailView,
    StaffTeacherHomeworkEntryCreateView,
    StaffTeacherHomeworkListCreateView,
)

__all__ = [
    'StaffScoreDimensionListCreateView',
    'StaffScoreDimensionDetailView',
    'StaffScoreSubjectsView',
    'StaffScoreDimensionReorderView',
    'StaffScoreDimensionMetaView',
    'StaffTeacherFeedbackListCreateView',
    'StaffTeacherFeedbackDetailView',
    'ScoreDimensionListView',
    'MyProgressListView',
    'MySessionFeedbackListView',
    'MyStudentDashboardView',
    'TeacherSessionFeedbackListCreateView',
    'TeacherSessionFeedbackDetailView',
    'TeacherProgressListCreateView',
    'HomeworkAttachmentDownloadView',
    'MyHomeworkListView',
    'MyHomeworkDetailView',
    'MyHomeworkEntryCreateView',
    'TeacherHomeworkListCreateView',
    'TeacherHomeworkDetailView',
    'TeacherHomeworkEntryCreateView',
    'StaffTeacherHomeworkListCreateView',
    'StaffTeacherHomeworkDetailView',
    'StaffTeacherHomeworkEntryCreateView',
    'TeacherStudentHistoryView',
    'TeacherSessionHistoryPrivacyView',
    'StudentSessionHistoryPrivacyView',
    'StaffTeacherStudentHistoryView',
]
