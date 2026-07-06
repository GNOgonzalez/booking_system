from django.db import migrations, models


def set_plan_subjects(apps, schema_editor):
    MembershipPlan = apps.get_model('scheduling', 'MembershipPlan')
    ClassOffering = apps.get_model('scheduling', 'ClassOffering')

    for plan in MembershipPlan.objects.all():
        if plan.name.startswith('Japanese'):
            plan.subject = 'Japanese'
            plan.save(update_fields=['subject'])
            continue
        if plan.name.startswith('English'):
            plan.subject = 'English'
            plan.save(update_fields=['subject'])
            continue
        subjects = set(
            ClassOffering.objects.filter(
                membership_plans=plan,
            ).values_list('subject', flat=True).distinct(),
        )
        subjects.discard('')
        if len(subjects) == 1:
            plan.subject = subjects.pop()
            plan.save(update_fields=['subject'])


class Migration(migrations.Migration):

    dependencies = [
        ('scheduling', '0025_class_catalog'),
    ]

    operations = [
        migrations.AddField(
            model_name='membershipplan',
            name='subject',
            field=models.CharField(
                blank=True,
                help_text='When set, members may book any active class with this subject.',
                max_length=100,
            ),
        ),
        migrations.RunPython(set_plan_subjects, migrations.RunPython.noop),
    ]
