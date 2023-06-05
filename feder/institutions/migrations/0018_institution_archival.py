# Generated by Django 3.2.19 on 2023-06-05 12:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('institutions', '0017_auto_20190927_1428'),
    ]

    operations = [
        migrations.AddField(
            model_name='institution',
            name='archival',
            field=models.BooleanField(default=False, help_text="Archival institution can't be assigned to monitoring or mass mailing.", verbose_name='Archival institution'),
        ),
    ]
