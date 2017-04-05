# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.management import call_command
from django.db import migrations, models


def load_defaults(apps, schema_editor):
    call_command('set_mail_defaults')
    Log = apps.get_model('notifications', 'Log')
    Log.objects.all().update(was_sent=True)


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0003_auto_20170405_1053'),
    ]

    operations = [
        migrations.RunPython(load_defaults)
    ]
