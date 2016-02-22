# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """
    Set the superuser flag for the users with given email addresses.
    """
    help = 'Set user with given email addresses as superusers.'

    def add_arguments(self, parser):
        parser.add_argument('email', nargs='+', type=str)

    def handle(self, *args, **options):
        updated = get_user_model().objects.filter(
            email__in=options['email']
        ).update(
            is_superuser=True
        )
        print(_(u"Updated {} users").format(updated))
