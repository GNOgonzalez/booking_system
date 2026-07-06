# Generated manually for subject-scoped metrics and JSON scores

from django.db import migrations, models


def migrate_legacy_scores(apps, schema_editor):
    SessionFeedback = apps.get_model('progress', 'SessionFeedback')
    mapping = {
        'grammar': 'grammar_stars',
        'reading': 'reading_stars',
        'writing': 'writing_stars',
        'speaking': 'speaking_stars',
    }
    for fb in SessionFeedback.objects.all():
        if fb.scores:
            continue
        fb.scores = {key: getattr(fb, field, 0) or 0 for key, field in mapping.items()}
        fb.save(update_fields=['scores'])


def migrate_dimension_subjects(apps, schema_editor):
    ScoreDimension = apps.get_model('progress', 'ScoreDimension')
    ScoreDimension.objects.filter(teacher__isnull=True).update(subject='')


class Migration(migrations.Migration):

    dependencies = [
        ('progress', '0003_scoredimension'),
    ]

    operations = [
        migrations.AddField(
            model_name='sessionfeedback',
            name='scores',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='scoredimension',
            name='subject',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Blank = default metrics for all subjects.',
                max_length=100,
            ),
        ),
        migrations.RemoveConstraint(
            model_name='scoredimension',
            name='unique_score_dimension_per_teacher',
        ),
        migrations.RemoveField(
            model_name='scoredimension',
            name='feedback_field',
        ),
        migrations.AddConstraint(
            model_name='scoredimension',
            constraint=models.UniqueConstraint(
                fields=('teacher', 'subject', 'key'),
                name='unique_score_dimension_scope',
            ),
        ),
        migrations.RunPython(migrate_dimension_subjects, migrations.RunPython.noop),
        migrations.RunPython(migrate_legacy_scores, migrations.RunPython.noop),
    ]
