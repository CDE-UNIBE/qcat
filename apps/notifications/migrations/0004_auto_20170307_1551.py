# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import notifications.validators


def set_all_sent(apps, schema_editor):
    Log = apps.get_model('notifications', 'Log')
    Log.objects.all().update(was_sent=True)


def unset_all_sent(apps, schema_editor):
    # field is deleted.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0003_mailpreferences'),
    ]

    operations = [
        migrations.AddField(
            model_name='log',
            name='was_sent',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='mailpreferences',
            name='wanted_actions',
            field=models.CharField(verbose_name='Subscribed for following changes in the review status', max_length=255, blank=True, validators=[notifications.validators.clean_wanted_actions]),
        ),
        migrations.AddField(
            model_name='mailpreferences',
            name='has_changed_language',
            field=models.BooleanField(default=False)
        ),
        migrations.RunPython(set_all_sent, unset_all_sent)
    ]
