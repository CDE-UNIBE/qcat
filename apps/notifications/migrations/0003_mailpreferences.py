# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.management import call_command
from django.db import migrations, models
import notifications.validators
from django.conf import settings


def load_defaults(apps, schema_editor):
    # model methods can't be accessed during migrations, so the management
    # command is used
    call_command('set_mail_defaults')


def purge_defaults(apps, schema_editor):
    pass


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
                ('wanted_actions', models.CharField(max_length=255, blank=True, validators=[notifications.validators.clean_wanted_actions])),
                ('language', models.CharField(max_length=2, default='en', choices=[('en', 'English'), ('fr', 'French'), ('es', 'Spanish'), ('ru', 'Russian'), ('km', 'Khmer'), ('lo', 'Lao'), ('ar', 'Arabic'), ('bs', 'Bosnian'), ('pt', 'Portuguese')])),
                ('user', models.OneToOneField(to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.RunPython(load_defaults, purge_defaults)
    ]
