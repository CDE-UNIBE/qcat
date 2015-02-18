from datetime import datetime
from django.conf import settings
from django.contrib.gis.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import to_locale, get_language
from django_pgjson.fields import JsonBField


class Configuration(models.Model):
    """
    The model representing a configuration of the
    :class:`questionnaire.models.Questionnaire`.
    """
    data = JsonBField(help_text="""
            The JSON configuration. See section "Questionnaire
            Configuration" of the manual for more information.<br/>
            <strong style="color:red;">Warning!</strong> You should not
            edit existing JSON configurations directly. Instead, create
            a new version and edit there.<br/><strong>Hint</strong>: Use
            <a href="https://jqplay.org/">jq play</a> to format your
            JSON.""")
    code = models.CharField(
        max_length=63, help_text="""
            The internal code of the configuration, e.g. "core", "wocat"
            or "unccd". The same code can be used multiple times but
            only one configuration per code can be "active".""")
    base_code = models.CharField(
        max_length=63, blank=True, help_text="""
            The code of the base configuration from which the
            configuration inherits. An active configuration with the
            given code needs to exist.""")
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    created = models.DateTimeField(auto_now=True)
    active = models.BooleanField(
        default=False, help_text="""
            <strong style="color:red;">Warning!</strong> Only one
            configuration per code can be active. If you set this
            configuration "active", an existing configuration with the
            same code will be set inactive.""")
    activated = models.DateTimeField(null=True, blank=True)

    def clean(self):
        """
        This function is called to validate the model, e.g. before it is
        saved to the database. Custom validation is handled in this
        function, namely:

        * If a ``base_code`` is set, an active configuration with this
          code needs to exist.
        * If there is already an active configuration with the given
          code, the ``active`` flag is set to ``False`` for this
          configuration.

        Raises:
            ``ValidationError``.
        """
        if self.base_code:
            # Check if base_code exists and has an active version.
            if Configuration.get_active_by_code(self.base_code) is None:
                raise ValidationError(
                    'The base code does not exist or does not have an active '
                    'version!')

        # Check if there is already an active configuration. In this case,
        # remove the flag from the previously active configuration.
        previously_active = Configuration.get_active_by_code(self.code)
        if self.active and previously_active is not None:
            previously_active.active = False
            previously_active.save()

        if self.active:
            # Check the configuration
            from configuration.configuration import QuestionnaireConfiguration
            configuration = QuestionnaireConfiguration(self.code, self)
            if configuration.configuration_error is not None:
                raise ValidationError(
                    'Error while parsing the configuration JSON: {}'.format(
                        configuration.configuration_error))

    def save(self, force_insert=False, force_update=False):
        """
        This function is called to save the model. Customized saving
        behavious is handled in this function, namely:

        * If a configuration is saved with ``active=True``, it receives
          a timestamp (``activated``).
        """
        if self.active:
            self.activated = datetime.now()
        super(Configuration, self).save(force_insert, force_update)

    @staticmethod
    def get_active_by_code(code):
        """
        Return the **active** Configuration with a given code if
        available.

        Args:
            ``code`` (str): The code of the Configuration.

        Returns:
            :class:`configuration.models.Configuration` or ``None``. The
            active Configuration object or None if no active
            configuration with the given code.
        """
        try:
            return Configuration.objects.get(code=code, active=True)
        except Configuration.DoesNotExist:
            return None

    def __str__(self):
        return self.name


class Translation(models.Model):
    """
    The model representing all translations of the database entries.

    .. important::
        Every translated model (with a foreign key to this model) needs
        to have a static attribute ``translation_type`` defined.
    """
    translation_type = models.CharField(max_length=63)
    data = JsonBField()

    def clean(self):
        """
        This function is called to validate the model, e.g. before it is
        saved to the database. Custom validation is handled in this
        function, namely:

        * ``translation_type`` needs to be a valid type.

          .. seealso::
              :func:`Translation.get_translation_types`.

        Raises:
            ``ValidationError``.
        """
        if self.translation_type not in self.get_translation_types():
            raise ValidationError(
                'Translation.translation_type needs to be one of: {}'.format(
                    ', '.join(self.get_translation_types())))

    @staticmethod
    def get_translation_types():
        """
        Return all ``translation_type`` attributes of the translated
        models. In order to do this, all related objects are looped
        dynamically.

        Returns:
            ``list``. A list with the ``validation_types`` of the
            translated models, e.g. ``['key', 'value', 'category']``.
        """
        translation_types = []
        for related in Translation._meta.get_all_related_objects():
            translation_types.append(related.model.translation_type)
        return translation_types

    def get_translation(self, keyword, locale=None):
        """
        Return the translation of the instance by looking it up in the
        ``data`` JSON field. If no ``locale`` is provided, the currently
        active locale is used.

        Kwargs:
            ``locale`` (str): The locale to find the translation for.

        Returns:
            ``str`` or ``None``. The translation or ``None`` if no entry
            for the given locale was not found.
        """
        if locale is None:
            locale = to_locale(get_language())
        return self.data.get(keyword, {}).get(locale)

    def __str__(self):
        return self.data.get(settings.LANGUAGES[0][0], '-')


class Key(models.Model):
    """
    The model representing the keys of the
    :class:`questionnaire.models.Questionnaire`.
    """
    translation_type = 'key'

    keyword = models.CharField(max_length=63, unique=True)
    translation = models.ForeignKey(
        'Translation', limit_choices_to={'translation_type': translation_type})
    configuration = JsonBField(help_text="""
            The JSON configuration. See section "Questionnaire
            Configuration" of the manual for more information.<br/>
            <strong>Hint</strong>: Use <a href="https://jqplay.org/">jq
            play</a> to format your JSON.""")

    def get_translation(self, *args, **kwargs):
        """
        Return the translation of the key. Passes all arguments to the
        relative :class:`Translation` model's function.

        .. seealso::
            :func:`Translation.get_translation`
        """
        return self.translation.get_translation(*args, **kwargs)

    @property
    def type_(self):
        """
        Helper function to access the ``type`` of the configuration
        JSON.

        Returns:
            ``str`` or ``None``. The value found at key ``type`` of the
            JSON or None if the key was not found.
        """
        return self.configuration.get('type')

    def __str__(self):
        return self.keyword


class Value(models.Model):
    """
    The model representing the predefined values of the
    :class:`questionnaire.models.Questionnaire`.
    """
    translation_type = 'value'

    keyword = models.CharField(max_length=63, unique=True)
    translation = models.ForeignKey(
        'Translation', limit_choices_to={'translation_type': translation_type})
    key = models.ForeignKey('Key')


class Questiongroup(models.Model):
    """
    The model representing the questiongroups of the
    :class:`questionnaire.models.Questionnaire`
    """
    translation_type = 'value'

    keyword = models.CharField(max_length=63, unique=True)
    translation = models.ForeignKey(
        'Translation', limit_choices_to={'translation_type': translation_type},
        null=True, blank=True)
    configuration = JsonBField(blank=True, help_text="""
            The JSON configuration. See section "Questionnaire
            Configuration" of the manual for more information.<br/>
            <strong>Hint</strong>: Use <a href="https://jqplay.org/">jq
            play</a> to format your JSON.""")

    def get_translation(self, *args, **kwargs):
        """
        Return the translation of the questiongroup. Passes all
        arguments to the relative :class:`Translation` model's function.

        .. seealso::
            :func:`Translation.get_translation`
        """
        return self.translation.get_translation(*args, **kwargs)

    def __str__(self):
        return self.keyword


class Category(models.Model):
    """
    The model representing the categories of the
    :class:`questionnaire.models.Questionnaire`.
    """
    translation_type = 'category'

    keyword = models.CharField(max_length=63, unique=True)
    translation = models.ForeignKey(
        'Translation', limit_choices_to={'translation_type': translation_type})

    def get_translation(self, *args, **kwargs):
        """
        Return the translation of the category. Passes all arguments to
        the relative :class:`Translation` model's function.

        .. seealso::
            :func:`Translation.get_translation`
        """
        return self.translation.get_translation(*args, **kwargs)

    def __str__(self):
        return self.keyword

    class Meta:
        verbose_name_plural = 'categories'
