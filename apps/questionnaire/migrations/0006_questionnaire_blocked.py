# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('questionnaire', '0005_auto_20160121_1135'),
    ]

    operations = [
        migrations.AddField(
            model_name='questionnaire',
            name='blocked',
            field=models.ForeignKey(blank=True, related_name='blocks_questionnaire', null=True, to=settings.AUTH_USER_MODEL),
        ),
    ]
