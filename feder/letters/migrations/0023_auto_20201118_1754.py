# Generated by Django 2.2.16 on 2020-11-18 17:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("letters", "0022_remove_letter_message"),
    ]

    operations = [
        migrations.AddField(
            model_name="letter",
            name="html_body",
            field=models.TextField(blank=True, verbose_name="Text in HTML"),
        ),
        migrations.AddField(
            model_name="letter",
            name="html_quote",
            field=models.TextField(blank=True, verbose_name="Quote in HTML"),
        ),
        migrations.AlterField(
            model_name="letter",
            name="is_spam",
            field=models.IntegerField(
                choices=[(0, "Unknown"), (1, "Spam"), (2, "Non-spam")],
                db_index=True,
                default=0,
                verbose_name="Is SPAM?",
            ),
        ),
    ]
