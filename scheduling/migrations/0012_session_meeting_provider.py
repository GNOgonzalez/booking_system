from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scheduling', '0011_studiollmconfig'),
    ]

    operations = [
        migrations.AddField(
            model_name='session',
            name='meeting_provider',
            field=models.CharField(
                choices=[
                    ('none', 'No video link'),
                    ('google_meet', 'Google Meet'),
                    ('zoom', 'Zoom'),
                ],
                default='google_meet',
                max_length=20,
            ),
        ),
    ]
