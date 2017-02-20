# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('questionnaire', '0015_merge'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='questionnaire',
            options={'ordering': ['-updated'], 'permissions': (('review_questionnaire', 'Can review questionnaire'), ('publish_questionnaire', 'Can publish questionnaire'), ('assign_questionnaire', 'Can assign questionnaire (for review/publish)'), ('view_questionnaire', 'Can view questionnaire'), ('edit_questionnaire', 'Can edit questionnaire'), ('delete_questionnaire', 'Can delete questionnaire'), ('flag_unccd_questionnaire', 'Can flag UNCCD questionnaire'), ('unflag_unccd_questionnaire', 'Can unflag UNCCD questionnaire'))},
        ),
        migrations.AlterField(
            model_name='questionnairetranslation',
            name='language',
            field=models.CharField(max_length=63, choices=[('en', 'English'), ('fr', 'French'), ('es', 'Spanish'), ('ru', 'Russian'), ('km', 'Khmer'), ('ar', 'Arabic'), ('bs', 'Bosnian'), ('pt', 'Portuguese')]),
        ),
    ]
