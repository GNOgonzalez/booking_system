from django.contrib import admin

from .models import HomeworkAssignment, HomeworkEntry, ProgressReport, ScoreDimension, SessionFeedback, Skill

admin.site.register(Skill)
admin.site.register(ProgressReport)
admin.site.register(ScoreDimension)
admin.site.register(HomeworkAssignment)
admin.site.register(HomeworkEntry)


@admin.register(SessionFeedback)
class SessionFeedbackAdmin(admin.ModelAdmin):
    list_display = (
        'student',
        'teacher',
        'session',
        'grammar_stars',
        'reading_stars',
        'writing_stars',
        'speaking_stars',
        'created_at',
    )
    list_filter = ('teacher',)
    search_fields = ('student__username',)
