from django.conf import settings
from django.db import models

from scheduling.models import Session


class Skill(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class ProgressReport(models.Model):
    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='progress_reports',
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='authored_reports',
    )
    session = models.ForeignKey(
        Session,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='progress_reports',
    )
    skill = models.ForeignKey(
        Skill,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='progress_reports',
    )
    rating = models.IntegerField(choices=RATING_CHOICES, default=3)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student.username} — {self.rating}/5 by {self.teacher.username}"


class SessionFeedback(models.Model):
    """Per-session, per-skill star ratings (0-5).

    Modeled after crud_project's StudentSessionFeedback so skill trends are easy
    to chart over time. One record per (session, student).
    """

    STAR_CHOICES = [(i, str(i)) for i in range(0, 6)]

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='session_feedbacks',
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='authored_feedbacks',
    )
    session = models.ForeignKey(
        Session,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='feedbacks',
    )
    grammar_stars = models.IntegerField(choices=STAR_CHOICES, default=0)
    reading_stars = models.IntegerField(choices=STAR_CHOICES, default=0)
    writing_stars = models.IntegerField(choices=STAR_CHOICES, default=0)
    speaking_stars = models.IntegerField(choices=STAR_CHOICES, default=0)
    scores = models.JSONField(default=dict, blank=True)
    class_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['session', 'student'],
                name='unique_feedback_per_session_student',
            ),
        ]

    def __str__(self):
        return (
            f"{self.student.username} — G{self.grammar_stars} R{self.reading_stars} "
            f"W{self.writing_stars} S{self.speaking_stars}"
        )


class ScoreDimension(models.Model):
    """Configurable labels for session feedback score columns.

    Studio defaults use teacher=NULL. Optional subject scopes metrics to a
    class subject (e.g. Japanese vs Piano). Up to 10 active metrics per scope.
    """

    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='score_dimensions',
    )
    subject = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text='Blank = default metrics for all subjects.',
    )
    key = models.SlugField(max_length=50)
    label = models.CharField(max_length=100)
    sort_order = models.PositiveSmallIntegerField(default=0)
    min_score = models.SmallIntegerField(default=0)
    max_score = models.SmallIntegerField(default=5)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['sort_order', 'key']
        constraints = [
            models.UniqueConstraint(
                fields=['teacher', 'subject', 'key'],
                name='unique_score_dimension_scope',
            ),
        ]

    def __str__(self):
        owner = self.teacher.username if self.teacher_id else 'system'
        scope = self.subject or 'all subjects'
        return f"{owner} — {self.label} ({scope})"


def homework_upload_path(instance, filename):
    import uuid

    safe = (filename or 'file').replace('/', '_')[-100:]
    return f'homework/{instance.assignment_id}/{uuid.uuid4().hex}_{safe}'


class HomeworkAssignment(models.Model):
    """Teacher → student homework: file exchange (7-day files) or ongoing journal prompt."""

    KIND_FILE = 'file'
    KIND_JOURNAL = 'journal'
    KIND_CHOICES = [
        (KIND_FILE, 'File exchange'),
        (KIND_JOURNAL, 'Journal prompt'),
    ]

    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='homework_assigned',
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='homework_received',
    )
    session = models.ForeignKey(
        'scheduling.Session',
        on_delete=models.CASCADE,
        related_name='homework_assignments',
    )
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default=KIND_FILE)
    title = models.CharField(max_length=200, blank=True)
    prompt = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='File-exchange threads stop accepting uploads after this time.',
    )

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['session', 'student'],
                name='unique_homework_per_session_student',
            ),
        ]

    def __str__(self):
        label = self.title or self.get_kind_display()
        return f'{label} — {self.student.username} ({self.teacher.username})'


class HomeworkEntry(models.Model):
    """A message in a homework thread — text and/or an attachment (files expire)."""

    assignment = models.ForeignKey(
        HomeworkAssignment,
        on_delete=models.CASCADE,
        related_name='entries',
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='homework_entries',
    )
    body = models.TextField(blank=True)
    attachment = models.FileField(upload_to=homework_upload_path, blank=True)
    attachment_name = models.CharField(max_length=255, blank=True)
    attachment_expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.author.username} on assignment {self.assignment_id}'


class SessionHistoryPrivacy(models.Model):
    """Per-session visibility for cross-teacher history (Phase 16)."""

    session = models.OneToOneField(
        Session,
        on_delete=models.CASCADE,
        related_name='history_privacy',
    )
    hidden_by_student = models.BooleanField(default=False)
    hidden_by_teacher = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'session history privacy'

    @property
    def hidden_from_peers(self):
        return self.hidden_by_student or self.hidden_by_teacher

    def __str__(self):
        flags = []
        if self.hidden_by_student:
            flags.append('student')
        if self.hidden_by_teacher:
            flags.append('teacher')
        return f'Session {self.session_id} hidden by: {", ".join(flags) or "none"}'
