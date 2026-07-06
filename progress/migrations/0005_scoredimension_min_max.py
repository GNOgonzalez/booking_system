# Generated manually — per-metric score range

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('progress', '0004_subject_scoped_metrics'),
    ]

    operations = [
        migrations.AddField(
            model_name='scoredimension',
            name='min_score',
            field=models.SmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='scoredimension',
            name='max_score',
            field=models.SmallIntegerField(default=5),
        ),
    ]
