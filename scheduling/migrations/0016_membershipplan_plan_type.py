from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scheduling', '0015_booking_membership'),
    ]

    operations = [
        migrations.AddField(
            model_name='membershipplan',
            name='plan_type',
            field=models.CharField(
                choices=[('subscription', 'Subscription'), ('ticket_pack', 'Ticket pack')],
                default='subscription',
                max_length=20,
            ),
        ),
    ]
