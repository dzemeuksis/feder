# -*- coding: utf-8 -*-
# Generated by Django 1.11.10 on 2018-02-27 18:23
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('letters', '0014_auto_20180220_2337'),
    ]

    operations = [
        migrations.AddField(
            model_name='letter',
            name='way',
            field=models.IntegerField(choices=[(0, 'Traditional'), (1, 'E-mail'), (2, 'E-mail')], default=1),
        ),
    ]
