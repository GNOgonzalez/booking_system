import django.db.models.deletion
from django.db import migrations, models


def migrate_topics(apps, schema_editor):
    ClassOffering = apps.get_model('scheduling', 'ClassOffering')
    ClassTopic = apps.get_model('scheduling', 'ClassTopic')
    Session = apps.get_model('scheduling', 'Session')
    MembershipPlan = apps.get_model('scheduling', 'MembershipPlan')

    groups = {}
    for offering in ClassOffering.objects.all().order_by('id'):
        key = (offering.teacher_id, offering.subject, offering.level, offering.focus)
        groups.setdefault(key, []).append(offering)

    for offerings in groups.values():
        canonical = offerings[0]
        for offering in offerings:
            topic, _ = ClassTopic.objects.get_or_create(
                class_offering=canonical,
                title=offering.topic,
                defaults={
                    'sort_order': ClassTopic.objects.filter(class_offering=canonical).count(),
                },
            )
            if offering.id != canonical.id:
                Session.objects.filter(class_offering_id=offering.id).update(
                    class_offering_id=canonical.id,
                    class_topic_id=topic.id,
                )
                for plan in MembershipPlan.objects.filter(allowed_classes=offering):
                    plan.allowed_classes.add(canonical)
                    plan.allowed_classes.remove(offering)
                offering.delete()
            else:
                Session.objects.filter(
                    class_offering_id=canonical.id,
                    class_topic__isnull=True,
                ).update(class_topic_id=topic.id)


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ('scheduling', '0016_membershipplan_plan_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='ClassTopic',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=150)),
                ('sort_order', models.PositiveIntegerField(default=0)),
                (
                    'class_offering',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='topics',
                        to='scheduling.classoffering',
                    ),
                ),
            ],
            options={
                'ordering': ['sort_order', 'title'],
            },
        ),
        migrations.AddField(
            model_name='classoffering',
            name='topics_ordered',
            field=models.BooleanField(
                default=False,
                help_text='When enabled, topics are meant to be taught in sort order.',
            ),
        ),
        migrations.AddField(
            model_name='session',
            name='class_topic',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='sessions',
                to='scheduling.classtopic',
            ),
        ),
        migrations.RemoveConstraint(
            model_name='classoffering',
            name='unique_class_offering_per_teacher',
        ),
        migrations.RunPython(migrate_topics, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='classoffering',
            name='topic',
        ),
        migrations.AlterModelOptions(
            name='classoffering',
            options={
                'ordering': ['subject', 'level', 'focus'],
                'verbose_name': 'class',
                'verbose_name_plural': 'classes',
            },
        ),
        migrations.AddConstraint(
            model_name='classoffering',
            constraint=models.UniqueConstraint(
                fields=('teacher', 'subject', 'level', 'focus'),
                name='unique_class_offering_per_teacher',
            ),
        ),
        migrations.AddConstraint(
            model_name='classtopic',
            constraint=models.UniqueConstraint(
                fields=('class_offering', 'title'),
                name='unique_topic_per_class',
            ),
        ),
    ]
