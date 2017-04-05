from django.core.management.base import NoArgsCommand
from django.db.models.signals import pre_save

from configuration.cache import get_configuration
from questionnaire.models import Questionnaire
from questionnaire.receivers import prevent_updates_on_published_items


class Command(NoArgsCommand):
    """
    Cast all integer values to booleans for configured field type 'boolean'

    When indexing data on elasticsearch, and no explicit field type is set, the
    field type is derived from the first element. For the unccd cases, this
    causes problems, as some boolen values are stored as 'true'/'false' and some
    as '1'/'0'. This command harmonizes this by setting all data to
    1/0.

    This is not efficient or nice, but needs to be run just once.
    """
    def handle_noargs(self, **options):
        pre_save.disconnect(
            prevent_updates_on_published_items, sender=Questionnaire
        )

        configuration_code = 'unccd'

        config = get_configuration(configuration_code)
        questionnaires = Questionnaire.objects.filter(
            code__startswith=configuration_code)
        self.find_int_values(questionnaires, config)

        pre_save.connect(
            prevent_updates_on_published_items, sender=Questionnaire
        )

    def find_int_values(self, questionnaires, config):
        for questionnaire in questionnaires:
            for qg_keyword, question_group in questionnaire.data.items():
                for questions in question_group:
                    for question_keyword, value in questions.items():
                        if value is True or value is False:
                            question_config = config.get_question_by_keyword(
                                questiongroup_keyword=qg_keyword,
                                keyword=question_keyword
                            )
                            if question_config.field_type == 'bool':
                                self.set_value(
                                    questionnaire, qg_keyword, question_keyword,
                                    self.get_int(value)
                                )

    def get_int(self, value):
        return 1 if value is True else 0

    def set_value(self, questionnaire, qg_keyword, question_keyword, value):
        for questiongroup_data in questionnaire.data[qg_keyword]:
            if question_keyword not in questiongroup_data:
                raise Exception
            questiongroup_data[question_keyword] = value
        questionnaire.save()
