# Generated by Django 1.11.4 on 2017-09-13 13:34

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("monitorings", "0007_auto_20170820_1544")]

    operations = [
        migrations.AddField(
            model_name="monitoring",
            name="email_footer",
            field=models.TextField(
                default=b"",
                help_text="Footer for sent mail and replies",
                verbose_name="Email footer",
            ),
        )
    ]
