# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from rest_framework.fields import empty

from configuration.cache import get_configuration
from configuration.configuration import QuestionnaireConfiguration
from configuration.models import Configuration

from .models import Questionnaire


class QuestionnaireSerializer(serializers.ModelSerializer):
    """
    Serializes the questionnaire with given configuration.
    """
    compilers = serializers.ListField()
    editors = serializers.ListField()
    reviewers = serializers.ListField()
    links = serializers.ListField(source='links_property')
    list_data = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    original_locale = serializers.CharField()
    serializer_config = serializers.SerializerMethodField()
    serializer_edition = serializers.SerializerMethodField()
    status = serializers.ListField(source='status_property')
    translations = serializers.ListField()
    flags = serializers.ListField(source='flags_property')
    url = serializers.SerializerMethodField()

    class Meta:
        model = Questionnaire
        fields = ('code', 'compilers', 'created',
                  'editors', 'links', 'list_data', 'name', 'original_locale', 'reviewers',
                  'serializer_config', 'serializer_edition', 'status', 'translations', 'updated',
                  'url', 'flags',)

    def __init__(self, instance=None, data=empty, **kwargs):
        """
        Keyword Args:
            config: configuration.QuestionnaireConfiguration

        Setup the correct config. If no config is passed, use the questionnaires
        default config. The config is required for some fields that can only
        be accessed on the actual configuration object.

        If a model instance is serialized, the 'instance' kwarg is passed.
        If an elasticsearch result is deserialized, the 'data' kwarg is passed.
        """

        if instance:
            self.config = instance.configuration_object

        elif data != empty and data.get('serializer_config'):
            # Restore object from json data. Make sure the serializer_config
            # is valid / exists in the db.
            self.config = get_configuration(
                code=data['serializer_config'],
                edition=data['serializer_edition'])

        else:
            raise ValueError(_(u"Can't serialize questionnaire without a valid "
                               u"configuration."))

        super().__init__(instance=instance, data=data, **kwargs)

    def get_list_data(self, obj, is_attribute=True):
        param = obj.data if is_attribute else obj
        return self.config.get_list_data([param])[0]

    def get_name(self, obj, is_attribute=True):
        param = obj.data if is_attribute else obj
        return self.config.get_questionnaire_name(param)

    def get_serializer_config(self, obj):
        """
        Store the config-id in the serialized data, so the same config can
        be used to deserialize the object, see __init__.
        """
        return self.config.keyword

    def get_serializer_edition(self, obj):
        return self.config.edition

    def get_url(self, obj):
        # Remove language from url, as this is 'None' if executed from command
        # line, or whichever active language if called from the search-admin panel.
        # See: https://redmine.cde.unibe.ch/issues/1716
        url = obj.get_absolute_url()
        return url[url.find('/', 1):]

    def to_internal_value(self, data):
        internal_value = dict(super().to_internal_value(data))
        # Restore readonly fields.
        readonly_fields = [
            'serializer_config', 'serializer_edition', 'list_data', 'name',
            'url']
        for key in readonly_fields:
            internal_value[key] = data[key]
        # Remove "_property" from key
        replace_property_keys = filter(lambda item: item.endswith('_property'), internal_value.keys())
        for key in replace_property_keys:
            internal_value[key.replace('_property', '')] = internal_value.pop(key)
        return internal_value

    def to_list_values(self, **kwargs):
        """
        Prepare validated_data to work with get_list_values.
        """
        if self.validated_data:
            # Prevent circular import
            from questionnaire.utils import prepare_list_values
            return prepare_list_values(
                data=self.validated_data, config=self.config, **kwargs
            )


class QuestionnaireInputSerializer(serializers.ModelSerializer):
    """
    Primarily used for POST requests for validating the Questionnaire with given configuration.
    """

    data = serializers.JSONField(binary=False, required=True)

    class Meta:
        model = Questionnaire
        fields = ['data']
