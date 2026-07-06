import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scheduling', '0014_booking_tickets'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='membership',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='bookings',
                to='scheduling.membership',
            ),
        ),
    ]
