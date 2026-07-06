import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scheduling', '0026_membershipplan_subject'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='classrequest',
            name='open_to_any_teacher',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='classrequest',
            name='subject',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='classrequest',
            name='level',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='classrequest',
            name='focus',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AlterField(
            model_name='classrequest',
            name='class_offering',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='class_requests',
                to='scheduling.classoffering',
            ),
        ),
        migrations.AlterField(
            model_name='classrequest',
            name='teacher',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='class_requests_received',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
