# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_auto_20160104_0843'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='typo3_session_id',
            field=models.CharField(max_length=255, blank=True),
        ),
    ]
