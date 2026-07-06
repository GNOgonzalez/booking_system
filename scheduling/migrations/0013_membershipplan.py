import django.db.models.deletion
from django.db import migrations, models


def seed_membership_plans(apps, schema_editor):
    MembershipPlan = apps.get_model('scheduling', 'MembershipPlan')
    Membership = apps.get_model('scheduling', 'Membership')
    ClassOffering = apps.get_model('scheduling', 'ClassOffering')

    basic = MembershipPlan.objects.create(
        name='Basic',
        description='Standard studio access.',
        price_cents=2000,
        billing_period_days=30,
        is_active=True,
    )
    premium = MembershipPlan.objects.create(
        name='Premium',
        description='Full studio access.',
        price_cents=5000,
        billing_period_days=30,
        is_active=True,
    )
    active_classes = list(ClassOffering.objects.filter(is_active=True))
    if active_classes:
        basic.allowed_classes.set(active_classes)
        premium.allowed_classes.set(active_classes)

    for membership in Membership.objects.all():
        plan_type = getattr(membership, 'plan_type', 'basic')
        membership.plan = premium if plan_type == 'premium' else basic
        membership.save(update_fields=['plan'])


class Migration(migrations.Migration):

    dependencies = [
        ('scheduling', '0012_session_meeting_provider'),
    ]

    operations = [
        migrations.CreateModel(
            name='MembershipPlan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True)),
                ('price_cents', models.PositiveIntegerField(default=0)),
                ('billing_period_days', models.PositiveIntegerField(default=30)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('allowed_classes', models.ManyToManyField(blank=True, help_text='Leave empty to allow all active classes.', related_name='membership_plans', to='scheduling.classoffering')),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.AddField(
            model_name='membership',
            name='plan',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='memberships',
                to='scheduling.membershipplan',
            ),
        ),
        migrations.RunPython(seed_membership_plans, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='membership',
            name='plan_type',
        ),
        migrations.AlterField(
            model_name='membership',
            name='plan',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='memberships',
                to='scheduling.membershipplan',
            ),
        ),
    ]
