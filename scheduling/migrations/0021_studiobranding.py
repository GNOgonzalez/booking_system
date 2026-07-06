from django.db import migrations, models

import scheduling.models


class Migration(migrations.Migration):

    dependencies = [
        ('scheduling', '0020_classrequest'),
    ]

    operations = [
        migrations.CreateModel(
            name='StudioBranding',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('display_name', models.CharField(default='Booking Studio', max_length=120)),
                ('logo', models.FileField(blank=True, upload_to=scheduling.models.studio_logo_upload_path)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'studio branding',
                'verbose_name_plural': 'studio branding',
            },
        ),
    ]
