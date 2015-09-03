# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('alerts', '0002_auto_20150830_2231'),
    ]

    operations = [
        migrations.AlterField(
            model_name='alert',
            name='author',
            field=models.ForeignKey(related_name='alert_author', verbose_name='Author', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='alert',
            name='solver',
            field=models.ForeignKey(related_name='alert_solver', verbose_name='Solver', to=settings.AUTH_USER_MODEL, null=True),
        ),
    ]