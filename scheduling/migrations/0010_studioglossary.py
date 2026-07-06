# Generated manually — studio glossary terms

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scheduling', '0009_teacherpermission'),
    ]

    operations = [
        migrations.CreateModel(
            name='StudioGlossary',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.SlugField(unique=True)),
                ('singular', models.CharField(max_length=80)),
                ('plural', models.CharField(max_length=80)),
            ],
            options={
                'verbose_name_plural': 'studio glossary',
                'ordering': ['key'],
            },
        ),
    ]
