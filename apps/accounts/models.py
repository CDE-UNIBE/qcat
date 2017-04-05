from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, Group

from configuration.models import Country, ValueUser
from .conf import settings


class User(AbstractBaseUser, PermissionsMixin):
    """
    The model representing a user of QCAT. This is basically a local
    replication of the user database of :term:`WOCAT` which handles the
    authentication. Therefore, no password is stored.

    No local users can be created, as this would lead to potential conflicts
    of the id between the WOCAT user model and this user model.

    The user model has the following fields:
        * email (varchar, acts as username)
        * firstname (varchar)
        * lastname (varchar)
        * last_login (timestamp, automatically generated)
        * date_joined (timestamp, automatically generated)
        * is_superuser (boolean)
        * password (varchar, empty)
        * language (varchar, empty)
        * wants_messages (boolean, true)

    .. todo::
        How to handle the privileges with regard to different
        configurations (e.g. moderator in WOCAT, editor in UNCCD)
    """
    email = models.EmailField(
        verbose_name='email address', unique=True, max_length=255)
    firstname = models.CharField(max_length=255, null=True, blank=True)
    lastname = models.CharField(max_length=255, null=True, blank=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    typo3_session_id = models.CharField(max_length=255, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    @property
    def is_active(self):
        """
        Indicates if a user account is currently active. Always returns
        True because any user in the database (and thus logged in
        through
        :class:`accounts.authentification.WocatAuthenticationBackend`)
        is considered as being active.

        Returns:
            ``bool``. Always returns ``True``.
        """
        return True

    @property
    def is_staff(self):
        """
        Handles the access to the Django administration interface.

        The following users have access to the administration interface:

            * Superusers (``is_superuser`` set to True)
            * Members of the following :term:`User Groups`:
                * :ref:`usergroups-administrators`

        Returns:
            ``bool``. Returns ``True`` if a user can access the
            administration interface, else ``False``.
        """
        if self.is_superuser is True:
            return True
        return self.groups.filter(
            name__in=['Administrators', 'Translators', 'WOCAT Secretariat']
        ).exists()

    def get_full_name(self):
        """
        A full representation of the user.

        Returns:
            ``str``. The email address of the user.
        """
        return self.email

    def get_short_name(self):
        """
        A short representation of the user.

        Returns:
            ``str``. The email address of the user.
        """
        return self.email

    def get_display_name(self):
        """
        A representation of the user for display purposes.

        Returns:
            ``str``. The display name of the user.
        """
        return '{} {}'.format(self.firstname, self.lastname)

    def get_questionnaires(self):
        """
        Helper function to return the questionnaires of a user along
        with his role in this membership.

        Returns:
            ``list``. A list of tuples where each entry contains the
            following elements:

            - [0]: ``string``. The role of the membership.

            - [1]: ``questionnaire.models.Questionnaire``. The
              questionnaire object.
        """
        questionnaires = []
        for membership in self.questionnairemembership_set.all():
            questionnaires.append((membership.role, membership.questionnaire))
        return questionnaires

    def get_unccd_countries(self):
        """
        Return a list of countries (value objects) related to the current user
        with relation UNCCD Focal Point.

        Returns:
            A list of countries (configuration.models.Value) for which the
            current user is a focal point.
        """
        countries = []

        for relation in self.valueuser_set.filter(
                relation=settings.CONFIGURATION_VALUEUSER_UNCCD).all():
            countries.append(relation.value)
        return countries

    def __str__(self):
        return '{} {}'.format(self.firstname, self.lastname)

    @staticmethod
    def create_new(id, email, lastname='', firstname=''):
        """
        Creates and returns a new user.

        Args:
            ``email`` (str): The email address of the user.

            ``name`` (str): The name of the user.

        Returns:
            :class:`accounts.models.User`. The newly created user.
        """
        user = User.objects.create(
            id=id, email=email, lastname=lastname, firstname=firstname)
        return user

    def update(
            self, email=None, lastname='', firstname='', usergroups=[]):
        """
        Handles the one-way synchronization of the user database by
        updating the values.

        Args:
            email:
            lastname:
            firstname:
            usergroups: A list of dicts representing the usergroups as provided
              by the remote service.
        """
        if (email is None and lastname == self.lastname and
                firstname == self.firstname):
            return

        # TODO: Temporary test of UNCCD flagging.
        if email in settings.TEMP_UNCCD_TEST:
            usergroups.append(
                {
                    'name': 'UNCCD Focal Point',
                    'unccd_country': 'CHE',
                }
            )

        """
        UNCCD Focal Points
        {
            'name': 'UNCCD Focal Point',
            'unccd_country': 'CHE',
        }
        """
        # todo: refactoring needed. prevent passing a mutable as method argument.
        if usergroups:
            new_unccd_group = next((x for x in usergroups if x.get('name') ==
                                    settings.ACCOUNTS_UNCCD_ROLE_NAME), None)
        if not usergroups or not new_unccd_group:
            ValueUser.objects.filter(
                user=self, relation=settings.CONFIGURATION_VALUEUSER_UNCCD
            ).delete()
        else:
            country = Country.get(new_unccd_group.get('unccd_country'))
            if country is not None:
                ValueUser.objects.get_or_create(
                    value=country, user=self,
                    relation=settings.CONFIGURATION_VALUEUSER_UNCCD)

        if email is not None:
            self.email = email
        self.lastname = lastname
        self.firstname = firstname
        self.save()
