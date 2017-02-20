import collections
import functools
import logging
from copy import copy

from .configuration import QuestionnaireQuestion

logger = logging.getLogger(__name__)


class ConfiguredQuestionnaire:
    """
    Combine given configuration and data into a single ordered dict.
    """
    def __init__(self, config, questionnaire, **data):
        self.values = data
        self.questionnaire = questionnaire
        self.values_keys = self.values.keys()

        # instance variables
        self.store = collections.OrderedDict()
        self.tmp_path = []  # all dict keys until the current element

        # create tree
        self.get_children(config)

    def get_children(self, config):
        """
        Walk through the configuration and build a 'store' with all nested and
        sibling elements, adding the filled in values from self.data.
        """
        children = getattr(config, 'children')

        for child in children:
            # Build nested elements while iterating through them.
            self.active_child_in_store[child.keyword] = {
                'label': str(child.label),
                'children': {}
            }

            # If the current element is not a question, iterate 'down' into the
            # next level of the config.
            if isinstance(child, QuestionnaireQuestion):
                self.put_question_data(child)
            else:
                # Add the 'path' to the current element, so the next iteration
                # can access this element and append to it.
                self.tmp_path.extend([child.keyword, 'children'])
                self.get_children(child)

        # Go back to the parent element.
        self.tmp_path = self.tmp_path[:-2]

    def put_question_data(self, child: QuestionnaireQuestion):
        """
        Store the child's data, including the value.
        """
        self.active_child_in_store[child.keyword] = {
            'label': str(child.label),
            'value': self.get_value(child)
        }

    def get_value(self, child: QuestionnaireQuestion):
        """
        Get the template values as defined in the QuestionnaireQuestion config.
        """
        # Copy the original value, so it can be re-applied. This is important
        # so the other instances of this config get the expected value.
        original_template_value = child.view_options.get('template', {})
        child.view_options['template'] = 'raw'
        value = self.values.get(child.parent_object.keyword)
        # Value may be empty, or a list
        # of dicts for nested questions.
        if not value:
            val = ''
        else:
            # If 'copy' is omitted, the same instance is returned for all values
            # I don't see why - but at this point, this seems the only
            # workaround.
            val = [copy(child.get_details(
                single_value, questionnaire_object=self.questionnaire
            )) for single_value in value]

        if original_template_value:
            child.view_options['template'] = original_template_value
        else:
            del child.view_options['template']
        return val

    @property
    def active_child_in_store(self):
        return functools.reduce(dict.get, self.tmp_path, self.store)
