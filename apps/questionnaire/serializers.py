import collections

from django.conf import settings
from rest_framework import serializers
from rest_framework.fields import empty

from configuration.utils import ConfigurationList
from .models import Questionnaire


class QuestionnaireSerializer(serializers.ModelSerializer):
    """
    Serializes the questionnaire with given configuration.
    """
    compilers = serializers.SerializerMethodField()
    configurations = serializers.SerializerMethodField()
    editors = serializers.SerializerMethodField()
    links = serializers.SerializerMethodField()
    list_data = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    translations = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    class Meta:
        model = Questionnaire
        fields = ('code', 'compilers', 'configurations', 'created', 'data',
                  'editors', 'links', 'list_data', 'name',
                  'status', 'translations', 'updated', 'url')

    def __init__(self, instance=None, data=empty, **kwargs):
        """

        """
        self.config = kwargs.pop('config', None)
        self.language_codes = dict(settings.LANGUAGES).keys()
        self.config_list = ConfigurationList()
        if instance:
            self._obj_metadata = instance.get_metadata()
        super().__init__(instance=instance, data=data, **kwargs)

    def get_compilers(self, obj):
        return self._obj_metadata.get('compilers')

    def get_configurations(self, obj):
        return self._obj_metadata.get('configurations')

    def get_editors(self, obj):
        return self._obj_metadata.get('editors')

    def get_links(self, obj):
        """
        @todo: refactor this!
        """
        links = collections.defaultdict(list)
        from questionnaire.utils import get_link_display
        for link in obj.links.all():

            link_configuration_db = link.configurations.first()
            if link_configuration_db is None:
                continue

            link_configuration = self.config_list.get(
                link_configuration_db.code
            )

            name_data = link_configuration.get_questionnaire_name(link.data)
            try:
                original_language = link.questionnairetranslation_set.first()\
                    .language
            except AttributeError:
                original_language = None

            for language in self.language_codes:
                name = name_data.get(
                    language, name_data.get(original_language))
                links[language].append(get_link_display(
                    link_configuration.keyword, name, link.code))
        return dict(links)

    def get_list_data(self, obj):
        return self.config.get_list_data([obj.data])[0]

    def get_name(self, obj):
        return self.config.get_questionnaire_name(obj.data)

    def get_status(self, obj):
        return self._obj_metadata.get('status')

    def get_translations(self, obj):
        return self._obj_metadata.get('translations')

    def get_url(self, obj):
        return obj.get_absolute_url()
