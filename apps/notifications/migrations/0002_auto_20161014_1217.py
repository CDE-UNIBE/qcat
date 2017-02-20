# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='InformationUpdate',
            fields=[
                ('id', models.AutoField(primary_key=True, auto_created=True, serialize=False, verbose_name='ID')),
                ('info', models.TextField()),
            ],
        ),
        migrations.AlterField(
            model_name='log',
            name='action',
            field=models.PositiveIntegerField(choices=[(1, 'created questionnaire'), (2, 'deleted questionnaire'), (3, 'changed status'), (4, 'invited member'), (5, 'removed member'), (6, 'edited content'), (7, 'editor finished')]),
        ),
        migrations.AddField(
            model_name='informationupdate',
            name='log',
            field=models.OneToOneField(to='notifications.Log'),
        ),
    ]
