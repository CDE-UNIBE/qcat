# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings
import django_pgjson.fields
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('questionnaire', '0014_auto_20161108_1501'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ContentUpdate',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data', django_pgjson.fields.JsonBField()),
            ],
        ),
        migrations.CreateModel(
            name='Log',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('action', models.PositiveIntegerField(choices=[(1, 'created questionnaire'), (2, 'deleted questionnaire'), (3, 'changed status'), (4, 'invited'), (5, 'removed'), (6, 'edited content')])),
                ('catalyst', models.ForeignKey(to=settings.AUTH_USER_MODEL, help_text='Person triggering the log', related_name='catalyst')),
                ('questionnaire', models.ForeignKey(to='questionnaire.Questionnaire')),
                ('subscribers', models.ManyToManyField(to=settings.AUTH_USER_MODEL, related_name='subscribers', help_text='All people that are members of the questionnaire')),
            ],
            options={
                'ordering': ['-created'],
            },
        ),
        migrations.CreateModel(
            name='MemberUpdate',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(max_length=50)),
                ('affected', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
                ('log', models.OneToOneField(to='notifications.Log')),
            ],
        ),
        migrations.CreateModel(
            name='ReadLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_read', models.BooleanField(default=False)),
                ('log', models.ForeignKey(to='notifications.Log', on_delete=django.db.models.deletion.PROTECT)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=django.db.models.deletion.PROTECT)),
            ],
        ),
        migrations.CreateModel(
            name='StatusUpdate',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.PositiveIntegerField(blank=True, null=True, choices=[(1, 'Draft'), (2, 'Submitted'), (3, 'Reviewed'), (4, 'Public'), (5, 'Rejected'), (6, 'Inactive')])),
                ('is_rejected', models.BooleanField(default=False)),
                ('message', models.TextField()),
                ('log', models.OneToOneField(to='notifications.Log')),
            ],
        ),
        migrations.AddField(
            model_name='contentupdate',
            name='log',
            field=models.OneToOneField(to='notifications.Log'),
        ),
        migrations.AlterUniqueTogether(
            name='readlog',
            unique_together=set([('log', 'user')]),
        ),
    ]
