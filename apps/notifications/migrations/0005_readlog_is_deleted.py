# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0004_auto_20170307_1551'),
    ]

    operations = [
        migrations.AddField(
            model_name='readlog',
            name='is_deleted',
            field=models.BooleanField(default=False),
        ),
    ]
