# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2016-09-17 13:47
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('monitorings', '0005_auto_20160914_2201'),
    ]

    operations = [
        migrations.AddField(
            model_name='monitoring',
            name='subject',
            field=models.CharField(default='Wniosek', max_length=80, verbose_name='Subject'),
            preserve_default=False,
        ),
    ]
