# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2016-09-15 20:42
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('questionaries', '0002_auto_20160915_0432'),
        ('tasks', '0003_auto_20160915_0613'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='answer',
            unique_together={('survey', 'question')},
        ),
    ]
