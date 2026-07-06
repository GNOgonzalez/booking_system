from django.db import migrations, models


def seed_ticket_defaults(apps, schema_editor):
    MembershipPlan = apps.get_model('scheduling', 'MembershipPlan')
    Membership = apps.get_model('scheduling', 'Membership')

    for plan in MembershipPlan.objects.all():
        if plan.name.lower() == 'premium':
            plan.ticket_allowance = 25
        else:
            plan.ticket_allowance = 10
        plan.save(update_fields=['ticket_allowance'])

    for membership in Membership.objects.select_related('plan'):
        if membership.tickets_remaining == 0:
            membership.tickets_remaining = membership.plan.ticket_allowance
            membership.save(update_fields=['tickets_remaining'])


class Migration(migrations.Migration):

    dependencies = [
        ('scheduling', '0013_membershipplan'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='tickets_spent',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='classoffering',
            name='ticket_cost',
            field=models.PositiveIntegerField(
                default=1,
                help_text='Booking tickets required to reserve a session for this class.',
            ),
        ),
        migrations.AddField(
            model_name='membership',
            name='tickets_remaining',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='membershipplan',
            name='ticket_allowance',
            field=models.PositiveIntegerField(
                default=10,
                help_text='Tickets granted each time a student purchases one billing period.',
            ),
        ),
        migrations.RunPython(seed_ticket_defaults, migrations.RunPython.noop),
    ]
