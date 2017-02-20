# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('questionnaire', '0012_auto_20160804_0736'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='questionnaire',
            name='data_old',
        ),
    ]
