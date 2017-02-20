import csv

import os
from django.core.management.base import NoArgsCommand
from django.db.models.signals import pre_save

from questionnaire.models import Questionnaire
from questionnaire.receivers import prevent_updates_on_published_items
from questionnaire.conf import settings


class Command(NoArgsCommand):
    """
    This command updates the UNCCD PRAIS questionnaires to assign their original
    language based on a CSV file which was provided by UNCCD. Also
    questionnaires marked to be deleted are set inactive.

    Requires file qcat_prais_data_language_mapping.csv.

    Usage:
        (env)$ python3 manage.py unccd_language_mapping
    """
    def handle_noargs(self, **options):

        # Temporarily disconnect the signal preventing updates on published
        # Questionnaires.
        pre_save.disconnect(prevent_updates_on_published_items, sender=Questionnaire)

        filename = 'qcat_prais_data_language_mapping.csv'
        with open(os.path.join(os.path.dirname(__file__), filename)) as file:
            reader = csv.reader(file)

            # Skip the header
            next(reader)

            for row in reader:
                map_language(row[0], row[3], row[4])

        # Reconnect the signal.
        pre_save.connect(prevent_updates_on_published_items, sender=Questionnaire)


def map_language(questionnaire_id, language, delete):

    try:
        questionnaire = Questionnaire.objects.get(pk=questionnaire_id)
    except Questionnaire.DoesNotExist:
        print("No questionnaire found with ID {}".format(questionnaire_id))
        return

    if delete:
        questionnaire.is_deleted = True
        questionnaire.status = settings.QUESTIONNAIRE_INACTIVE
        questionnaire.save()

    # Update the translation flag
    translation = questionnaire.questionnairetranslation_set.filter(
        original_language=True).first()
    old_language = translation.language
    translation.language = language
    translation.save()

    # Update the language key in the data dictionary.
    data_new = {}
    for qg_key, qg_list in questionnaire.data.items():
        qg_list_new = []
        for qg_data in qg_list:
            qg_data_new = {}
            for key, value in qg_data.items():
                if isinstance(value, dict):
                    value_new = {language: value[old_language]}
                else:
                    value_new = value
                qg_data_new[key] = value_new
            qg_list_new.append(qg_data_new)
        data_new[qg_key] = qg_list_new
    questionnaire.data = data_new
    questionnaire.save()
