# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('questionnaire', '0012_auto_20160804_0736'),
    ]

    operations = [
        migrations.CreateModel(
            name='Lock',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, auto_created=True, verbose_name='ID')),
                ('questionnaire_code', models.CharField(max_length=50)),
                ('start', models.DateTimeField(auto_now_add=True)),
                ('is_finished', models.BooleanField(default=False)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.RemoveField(
            model_name='questionnaire',
            name='blocked',
        ),
        migrations.AlterField(
            model_name='questionnairetranslation',
            name='language',
            field=models.CharField(max_length=63, choices=[('en', 'English'), ('es', 'Spanish'), ('fr', 'French'), ('ru', 'Russian'), ('pt', 'Portuguese'), ('ar', 'Arabic')]),
        ),
    ]
