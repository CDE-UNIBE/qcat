"""
This helper script can be used to clean questionnaire data which was stored
incorrectly (according to the configuration) in the database. This mainly due to
historic reasons (incorrect update of configuration) and should only concern
old questionnaires (around ID 500).

DO NOT FORGET TO UPDATE ELASTICSEARCH INDEX AFTER RUNNING THE SCRIPT!
"""

from django.core.management.base import BaseCommand
from django.db.models import Count
from django.db.models.signals import pre_save

from configuration.cache import get_configuration
from questionnaire.models import Questionnaire, QuestionnaireLink
from questionnaire.receivers import prevent_updates_on_published_items
from questionnaire.utils import clean_questionnaire_data


class Command(BaseCommand):
    """
    Run as
        python3 manage.py check_questionnaire_data
    to check the questionnaire data.

    Run as
        python3 manage.py check_questionnaire_data --clean-data
    to actually clean the data and fix all errors which can be fixed
    automatically.
    """
    help = 'Check and possibly clean questionnaire data.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clean-data',
            action='store_true',
            dest='clean_data',
            default=False,
            help='Clean the data. Always check first!'
        )

    def handle(self, *args, **options):

        do_data_clean = options.get('clean_data')
        if do_data_clean:
            pre_save.disconnect(prevent_updates_on_published_items,
                                sender=Questionnaire)

        questionnaires = Questionnaire.with_status.not_deleted().all()
        error_questionnaires = []
        grouped_errors = {}
        for questionnaire in questionnaires:
            configurations = questionnaire.configurations_property

            if not configurations:
                print("\nQuestionnaire with ID {} has no configuration!".format(
                    questionnaire.id))

            for configuration_code in configurations:

                configuration = get_configuration(configuration_code)

                cleaned_data, errors = clean_questionnaire_data(
                    questionnaire.data, configuration)

                if errors:
                    error_questionnaires.append(questionnaire)

                    questionnaire_data = questionnaire.data
                    cleaned = False

                    print_questionnaire_name(questionnaire)

                    for error in errors:

                        if error not in grouped_errors:
                            grouped_errors[error] = []

                        fixable = error in automatic_fixes
                        if fixable:
                            fixable_string = self.style.SQL_COLTYPE('Fixable')
                        else:
                            fixable_string = self.style.NOTICE('Not fixable')

                        fixed_string = ''
                        if do_data_clean and fixable:
                            fix_function = automatic_fixes[error]
                            questionnaire_data = fix_function(
                                questionnaire_data)
                            cleaned = True
                            fixed_string = self.style.SQL_COLTYPE('Fixed.')

                        print_error_message(fixable_string, error, fixed_string)

                        grouped_errors[error].append(questionnaire.id)

                    print('---')
                    print(self.style.WARNING("{} error(s)".format(len(errors))))

                    if cleaned is True:
                        questionnaire.data = questionnaire_data
                        questionnaire.save()

                # Fix the problem if there are too many header images. This can
                # happen if more than one image were uploaded (if upload is
                # slow, additional pictures can be added). It causes the
                # interchange images to be broken. But really, it should be
                # somehow fixed in the code, not afterwards in the data ...
                # TODO: Prevent upload of multiple images in one upload field.
                qg_image_data = questionnaire.data.get('qg_image', [])
                if len(qg_image_data) > 1:
                    print_questionnaire_name(questionnaire)
                    fixable_string = self.style.NOTICE('Not fixable')
                    error = 'Questionnaire has too many "qg_image" ' \
                            'questiongroups'
                    fixed_string = ''
                    print_error_message(fixable_string, error, fixed_string)
                elif len(qg_image_data) == 1:
                    image_data = qg_image_data[0]
                    image = image_data.get('image', '')
                    image_parts = image.split(',')
                    if len(image_parts) > 1:
                        if questionnaire not in error_questionnaires:
                            error_questionnaires.append(questionnaire)

                        print_questionnaire_name(questionnaire)
                        fixable_string = self.style.SQL_COLTYPE('Fixable')
                        error = 'Questionnaire has too many header images.'

                        fixed_string = ''
                        if do_data_clean:
                            last_image = image_parts[len(image_parts) - 1]
                            image_data['image'] = last_image
                            questionnaire.save()
                            fixed_string = self.style.SQL_COLTYPE('Fixed.')

                        print_error_message(fixable_string, error, fixed_string)

            # Check the link count. This fixes the problem where duplicate link
            # entries were created if for example the questionnaire was edited
            # during the review process. This bug should have been fixed on
            # Dec 8, 2016.
            link_count_query = QuestionnaireLink.objects.filter(
                from_questionnaire=questionnaire).values(
                'to_questionnaire_id').annotate(
                total=Count('to_questionnaire_id'))
            duplicate_links = [
                link for link in link_count_query if link['total'] > 1]
            if duplicate_links:
                if questionnaire not in error_questionnaires:
                    error_questionnaires.append(questionnaire)

                print_questionnaire_name(questionnaire)

                for duplicate in duplicate_links:
                    error = 'Too many links ({}) to questionnaire with ID {}.'.\
                        format(duplicate['total'],
                               duplicate['to_questionnaire_id'])
                    fixable_string = self.style.SQL_COLTYPE('Fixable')

                    fixed_string = ''
                    if do_data_clean:
                        to_questionnaire = Questionnaire.objects.get(
                            pk=duplicate['to_questionnaire_id'])
                        # Remove all links
                        questionnaire.remove_link(to_questionnaire, symm=False)
                        # Add a new (single) link
                        questionnaire.add_link(to_questionnaire, symm=False)
                        fixed_string = self.style.SQL_COLTYPE('Fixed.')

                    print_error_message(fixable_string, error, fixed_string)

        if do_data_clean:
            pre_save.connect(prevent_updates_on_published_items,
                             sender=Questionnaire)

        print("\n\n{} questionnaires found with errors (out of {})".format(
            len(error_questionnaires), len(questionnaires)))


def print_questionnaire_name(questionnaire):
    print(
        "\nQuestionnaire [ID: {}, code: {}, status: {}]".format(
            questionnaire.id, questionnaire.code,
            questionnaire.get_status_display()))


def print_error_message(fixable_string, error, fixed_string):
    print("{}: {} {}".format(
        fixable_string, error, fixed_string))


def fix_country_name(data):
    # Fix the case when the "country" key somehow slipped in the "qg_name"
    # questiongroup.
    qg_data_list = data.get('qg_name', [])
    for qg_data in qg_data_list:
        if 'country' in qg_data:
            del qg_data['country']
    return data


def fix_institution_project(data):
    # Fix the case when key "funding_institution" somehow slipped in the
    # questiongroup "qg_funding_project"
    qg_data_list = data.get('qg_funding_project', [])
    for qg_data in qg_data_list:
        if 'funding_institution' in qg_data:
            del qg_data['funding_institution']
    return data


def fix_invalid_project(data):
    # Fix the case when key "funding_project" of questiongroup
    # qg_funding_project does not contain a valid Project ID.
    qg_data_list = data.get('qg_funding_project', [])
    for qg_data in qg_data_list:
        if 'funding_project' in qg_data:
            del qg_data['funding_project']
    return data


def fix_tech_qg_192_condition(data):
    # Questiongroup "tech_qg_192" requires key "tech_adaptation_yes" of
    # questiongroup "tech_qg_230" set to True.
    qg_192_data_list = data.get('tech_qg_192', [])
    qg_230_data_list = data.get('tech_qg_230', [])
    if qg_192_data_list:
        if not qg_230_data_list:
            data['tech_qg_230'] = [{'tech_adaptation_yes': 1}]
        else:
            raise NotImplementedError('qg_230 does exist. Check script.')
    return data


def fix_gender_mixed(data):
    # Fix the case when value of key "tech_gender" of questiongroup "tech_qg_71"
    # is set to "gender_mixed". This changed and now only "gender_women" and
    # "gender_men" can be selected. Therefore map the new value to
    # ["gender_women", "gender_men"].
    qg_data_list = data.get('tech_qg_71', [])
    for qg_data in qg_data_list:
        if 'tech_gender' in qg_data and qg_data.get(
                'tech_gender') == 'gender_mixed':
            qg_data['tech_gender'] = ["gender_women", "gender_men"]
    return data


def fix_person_institution_address(data):
    # Fix the case when question "person_institution_address" somehow slipped
    # into questiongroup "tech_qg_184"
    qg_data_list = data.get('tech_qg_184', [])
    for qg_data in qg_data_list:
        if 'person_institution_address' in qg_data:
            del qg_data['person_institution_address']
    return data


def fix_location_comments(data):
    # Fix the case when question "location_comments" somehow slipped into
    # questiongroup "tech_qg_3".
    qg_data_list = data.get('tech_qg_3', [])
    for qg_data in qg_data_list:
        if 'location_comments' in qg_data:
            del qg_data['location_comments']
    return data


automatic_fixes = {
    'Question with keyword "country" is not valid for Questiongroup with keyword "qg_name"': fix_country_name,
    'Question with keyword "funding_institution" is not valid for Questiongroup with keyword "qg_funding_project"': fix_institution_project,
    'The value is not a valid choice of model "Project"': fix_invalid_project,
    'Questiongroup with keyword "tech_qg_192" requires condition "tech_qg_192".': fix_tech_qg_192_condition,
    'Value "gender_mixed" of key "tech_gender" needs to be a list': fix_gender_mixed,
    'Question with keyword "person_institution_address" is not valid for Questiongroup with keyword "tech_qg_184"': fix_person_institution_address,
    'Question with keyword "location_comments" is not valid for Questiongroup with keyword "tech_qg_3"': fix_location_comments,
}
