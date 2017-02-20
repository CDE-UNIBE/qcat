# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0002_notetoken'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='notetoken',
            options={'verbose_name': 'Token', 'verbose_name_plural': 'Tokens'},
        ),
        migrations.AlterField(
            model_name='notetoken',
            name='created',
            field=models.DateTimeField(verbose_name='Created', auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='notetoken',
            name='key',
            field=models.CharField(verbose_name='Key', primary_key=True, max_length=40, serialize=False),
        ),
        migrations.AlterField(
            model_name='notetoken',
            name='user',
            field=models.OneToOneField(verbose_name='User', related_name='auth_token', to=settings.AUTH_USER_MODEL),
        ),
    ]
