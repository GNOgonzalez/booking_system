import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scheduling', '0017_classtopic_class_topics'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount_cents', models.PositiveIntegerField()),
                ('currency', models.CharField(default='usd', max_length=3)),
                ('quantity', models.PositiveIntegerField(default=1, help_text='Billing periods purchased (e.g. months).')),
                ('provider', models.CharField(choices=[('mock', 'Mock'), ('stripe', 'Stripe')], default='mock', max_length=20)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed'), ('refunded', 'Refunded')], default='completed', max_length=20)),
                ('stripe_checkout_session_id', models.CharField(blank=True, max_length=200)),
                ('stripe_payment_intent_id', models.CharField(blank=True, max_length=200)),
                ('description', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('membership', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='payments', to='scheduling.membership')),
                ('plan', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='payments', to='scheduling.membershipplan')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payments', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
