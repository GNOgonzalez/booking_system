# Generated manually — homework must belong to a session.

import django.db.models.deletion
from django.db import migrations, models


def clear_homework(apps, schema_editor):
    HomeworkEntry = apps.get_model('progress', 'HomeworkEntry')
    HomeworkAssignment = apps.get_model('progress', 'HomeworkAssignment')
    HomeworkEntry.objects.all().delete()
    HomeworkAssignment.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('progress', '0006_homework'),
        ('scheduling', '0011_studiollmconfig'),
    ]

    operations = [
        migrations.RunPython(clear_homework, migrations.RunPython.noop),
        migrations.AddField(
            model_name='homeworkassignment',
            name='session',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='homework_assignments',
                to='scheduling.session',
            ),
            preserve_default=False,
        ),
        migrations.AddConstraint(
            model_name='homeworkassignment',
            constraint=models.UniqueConstraint(
                fields=('session', 'student'),
                name='unique_homework_per_session_student',
            ),
        ),
    ]
