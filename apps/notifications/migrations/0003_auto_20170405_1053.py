# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import notifications.validators
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('notifications', '0002_auto_20161014_1217'),
    ]

    operations = [
        migrations.CreateModel(
            name='MailPreferences',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('subscription', models.CharField(max_length=10, default='all', choices=[('none', 'No emails at all'), ('todo', 'Only emails that I need to work on'), ('all', 'All emails')])),
                ('wanted_actions', models.CharField(verbose_name='Subscribed for following changes in the review status', max_length=255, blank=True, validators=[notifications.validators.clean_wanted_actions])),
                ('language', models.CharField(max_length=2, default='en', choices=[('en', 'English'), ('fr', 'French'), ('es', 'Spanish'), ('ru', 'Russian'), ('km', 'Khmer'), ('lo', 'Lao'), ('ar', 'Arabic'), ('bs', 'Bosnian'), ('pt', 'Portuguese')])),
                ('has_changed_language', models.BooleanField(default=False)),
                ('user', models.OneToOneField(to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='log',
            name='was_sent',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='readlog',
            name='is_deleted',
            field=models.BooleanField(default=False),
        ),
    ]
