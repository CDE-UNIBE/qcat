# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('questionnaire', '0004_auto_20160104_0842'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='questionnaire',
            name='blocked',
        ),
        migrations.AlterField(
            model_name='questionnairemembership',
            name='role',
            field=models.CharField(max_length=64, choices=[('compiler', 'Compiler'), ('editor', 'Editor'), ('reviewer', 'Reviewer'), ('publisher', 'Publisher'), ('landuser', 'Land User'), ('resourceperson', 'Key resource person')]),
        ),
    ]
