import floppyforms as forms
from django.forms import BaseFormSet, formset_factory
from django.template.loader import render_to_string
from django.utils.translation import ugettext as _

from configuration.models import (
    Category,
    Configuration,
    Key,
    Questiongroup,
)
from qcat.errors import (
    ConfigurationError,
    ConfigurationErrorInvalidCondition,
    ConfigurationErrorInvalidConfiguration,
    ConfigurationErrorInvalidOption,
    ConfigurationErrorInvalidQuestiongroupCondition,
    ConfigurationErrorNoConfigurationFound,
    ConfigurationErrorNotInDatabase,
)
from qcat.utils import (
    find_dict_in_list,
    is_empty_list_of_dicts,
)
from questionnaire.upload import (
    get_interchange_urls_by_identifier,
    get_url_by_identifier,
)


class BaseConfigurationObject(object):
    """
    This is the base class for all Questionnaire Configuration objects.
    """

    def __init__(self, parent_object, configuration):
        """
        Sets the following attributes for each configuration object:

            ``self.configuration``: The configuration dictionary.

            ``self.keyword``: The keyword identifier of the object.

            ``self.configuration_object``: The database configuration
                object

            ``self.configuration_keyword``: The code of the current
                configuration

            ``self.parent_object``: The parent configuration object.

            ``self.label``: The (translated) label.

            ``self.children``: The child configuration objects if
                available.
        """
        validate_type(
            configuration, dict, self.name_current, 'list of dicts',
            self.name_parent)
        self.configuration = configuration
        self.validate_options()

        keyword = self.configuration.get('keyword')
        if not isinstance(keyword, str):
            raise ConfigurationErrorInvalidConfiguration(
                'keyword', 'str', self.name_current)
        self.keyword = keyword

        if isinstance(self, (
                QuestionnaireSection, QuestionnaireCategory,
                QuestionnaireSubcategory)):
            try:
                self.configuration_object = Category.objects.get(
                    keyword=self.keyword)
            except Category.DoesNotExist:
                raise ConfigurationErrorNotInDatabase(Category, self.keyword)
        elif isinstance(self, QuestionnaireQuestiongroup):
            try:
                self.configuration_object = Questiongroup.objects.get(
                    keyword=self.keyword)
            except Questiongroup.DoesNotExist:
                raise ConfigurationErrorNotInDatabase(
                    Questiongroup, self.keyword)
        elif isinstance(self, QuestionnaireQuestion):
            try:
                self.configuration_object = Key.objects.get(
                    keyword=self.keyword)
            except Key.DoesNotExist:
                raise ConfigurationErrorNotInDatabase(Key, self.keyword)
        else:
            raise Exception('Unknown instance')

        self.configuration_keyword = parent_object.configuration_keyword
        self.parent_object = parent_object

        self.helptext = ''
        self.label = ''
        self.label_view = ''
        self.numbering = ''
        translation = self.configuration_object.translation
        if translation:
            self.helptext = translation.get_translation(
                'helptext', self.configuration_keyword)
            self.label = translation.get_translation(
                'label', self.configuration_keyword)
            self.label_view = translation.get_translation(
                'label_view', self.configuration_keyword)
            if self.label_view is None:
                self.label_view = self.label
            self.numbering = translation.get_numbering(
                self.configuration_keyword)

        # Should be at the bottom of the function
        children = []
        configuration_children = self.configuration.get(self.name_children)
        if configuration_children:
            if (not isinstance(configuration_children, list)
                    or len(configuration_children) == 0):
                raise ConfigurationErrorInvalidConfiguration(
                    self.name_children, 'list of dicts', self.name_current)
            for configuration_child in configuration_children:
                children.append(
                    self.Child(self, configuration_child))
            self.children = children

    def validate_options(self):
        """
        Validate a configuration dict to check if it contains invalid
        options as keys.

        Raises:
            :class:`qcat.errors.ConfigurationErrorInvalidOption`
        """
        invalid_options = list(
            set(self.configuration) - set(self.valid_options))
        if len(invalid_options) > 0:
            raise ConfigurationErrorInvalidOption(
                invalid_options[0], self.configuration, self)

    @staticmethod
    def merge_configurations(obj, base_configuration, specific_configuration):
        """
        Merges two configuration dicts into a single one. The base
        configuration is extended by the specific configuration.

        Children are identified by their keyword and merged. The merging
        of the children is handled by the respective class.

        Args:
            ``obj`` (BaseConfigurationObject): A configuration object.

            ``base_configuration`` (dict): The base configuration on which the
            specific configuration is based.

            ``specific_configuration`` (dict): The specific configuration
            extending the base configuration.

        Returns:
            ``dict``. The merged configuration.
        """
        validate_type(
            base_configuration, dict, obj.name_current, dict, obj.name_parent)
        validate_type(
            specific_configuration, dict, obj.name_current, dict,
            obj.name_parent)

        merged_children = []
        base_children = base_configuration.get(obj.name_children, [])
        specific_children = specific_configuration.get(obj.name_children, [])

        if base_children:
            validate_type(
                base_children, list, obj.name_children, list, obj.name_current)
        validate_type(
            specific_children, list, obj.name_children, list, obj.name_current)

        # Collect all base configurations and find eventual specific
        # configurations for these children
        for base_child in base_children:
            specific_child = find_dict_in_list(
                specific_children, 'keyword', base_child.get('keyword'))
            merged_children.append(
                obj.Child.merge_configurations(
                    obj.Child, base_child.copy(), specific_child.copy()))

        # Collect all specific configurations which are not part of the
        # base children
        for specific_child in specific_children:
            base_child = find_dict_in_list(
                base_children, 'keyword', specific_child.get('keyword'))
            if not base_child:
                merged_children.append(specific_child.copy())

        # Collect all remaining attributes of specific, except the
        # children which are already copied.
        for specific_key, specific_value in specific_configuration.items():
            if specific_key == obj.name_children:
                continue
            base_configuration[specific_key] = specific_value

        if obj.name_children:
            base_configuration[obj.name_children] = merged_children
        else:
            base_configuration.update(specific_configuration)

        return base_configuration


class QuestionnaireQuestion(BaseConfigurationObject):
    """
    A class representing the configuration of a Question of the
    Questionnaire. A Question basically consists of the Key and optional
    Values (for Questions with predefined Answers)
    """
    valid_options = [
        'keyword',
        'view_options',
        'form_options',
    ]
    valid_field_types = [
        'char',
        'text',
        'bool',
        'measure',
        'checkbox',
        'image_checkbox',
        'image',
        'select_type',
        'select',
        'radio',
        'todo',
        'cb_bool',
        'user_id',
        'user_display',
    ]
    translation_original_prefix = 'original_'
    translation_translation_prefix = 'translation_'
    translation_old_prefix = 'old_'
    value_image_path = 'assets/img/'
    name_current = 'questions'
    name_parent = 'questiongroups'
    name_children = ''
    Child = None

    def __init__(self, parent_object, configuration):
        """
        Parameter ``configuration`` is a ``dict`` containing the
        configuration of the Question. It needs to have the following
        format::

          {
            # The keyword of the key of the question.
            "keyword": "KEY",

            # (optional)
            "view_options": {
              # Default: "default"
              "template": "TEMPLATE_NAME",

              # Default: ""
              "label": "none",

              # Default: ""
              "header": "small",

              # Default: false
              "in_list": true,

              # Default: false
              "is_name": true,

              # Default: false
              "filter": true
            },

            # (optional)
            "form_options": {
              # Default: "default"
              "template": "TEMPLATE_NAME",

              # Default: None
              "max_length": 500,

              # Default: 3
              "num_rows": 5,

              # Default: ""
              "colclass": "top-margin",

              # Default: ""
              "helptext": "tooltip",

              # Default: ""
              "label": "placeholder",

              # Default: []
              "conditions": [],

              # Default: false
              "conditional": true,

              # Default: []
              "questiongroup_conditions": [],
            }
          }

        .. seealso::
            For more information on the format and the configuration
            options, please refer to the documentation:
            :doc:`/configuration/questiongroup`

        Raises:
            :class:`qcat.errors.ConfigurationErrorInvalidConfiguration`,
            ``ConfigurationErrorNotInDatabase``.
        """
        super(QuestionnaireQuestion, self).__init__(
            parent_object, configuration)
        self.questiongroup = parent_object

        self.key_config = self.configuration_object.configuration

        self.field_type = self.key_config.get('type', 'char')
        if self.field_type not in self.valid_field_types:
            raise ConfigurationErrorInvalidOption(
                self.field_type, 'type', 'Key')

        view_options = self.key_config.get('view_options', {})
        if configuration.get('view_options'):
            view_options.update(configuration.get('view_options'))
        self.view_options = view_options

        form_options = self.key_config.get('form_options', {})
        if configuration.get('form_options'):
            form_options.update(configuration.get('form_options'))
        self.form_options = form_options

        self.in_list = self.view_options.get('in_list', False) is True
        self.is_name = self.view_options.get('is_name', False) is True

        self.max_length = self.form_options.get('max_length', None)
        if self.max_length and not isinstance(self.max_length, int):
            self.max_length = None
        self.num_rows = self.form_options.get('num_rows', 3)

        self.filterable = self.view_options.get('filter', False) is True

        self.images = []
        self.choices = ()
        self.choices_helptexts = []
        self.value_objects = []
        if self.field_type in ['bool']:
            self.choices = ((1, _('Yes')), (0, _('No')))
        elif self.field_type in ['cb_bool']:
            self.choices = ((1, self.label),)
        elif self.field_type in [
                'measure', 'checkbox', 'image_checkbox', 'select_type',
                'select', 'radio']:
            self.value_objects = self.configuration_object.values.all()
            if len(self.value_objects) == 0:
                raise ConfigurationErrorNotInDatabase(
                    self, '[values of key {}]'.format(self.keyword))
            if self.field_type in ['select_type', 'select']:
                choices = [('', '-', '')]
            else:
                choices = []
            ordered_values = False
            for i, v in enumerate(self.value_objects):
                if v.order_value:
                    ordered_values = True
                if self.field_type in ['measure']:
                    choices.append((i + 1, v.get_translation(
                        'label', self.configuration_keyword),
                        v.get_translation(
                            'helptext', self.configuration_keyword)))
                else:
                    choices.append((v.keyword, v.get_translation(
                        'label', self.configuration_keyword),
                        v.get_translation(
                            'helptext', self.configuration_keyword)))
                if self.field_type in ['image_checkbox']:
                    self.images.append('{}{}'.format(
                        self.value_image_path,
                        v.configuration.get('image_name')))
            if ordered_values is False:
                try:
                    choices = sorted(choices, key=lambda tup: tup[1])
                except TypeError:
                    pass
            self.choices = tuple([c[:2] for c in choices])
            self.choices_helptexts = [c[2] for c in choices]

        self.additional_translations = {}
        if self.field_type in ['measure']:
            translation = self.configuration_object.translation
            label_left = translation.get_translation(
                'label_left', self.configuration_keyword)
            label_right = translation.get_translation(
                'label_right', self.configuration_keyword)
            self.additional_translations.update(
                {'label_left': label_left, 'label_right': label_right})

        self.conditional = self.form_options.get('conditional', False)

        conditions = []
        for condition in self.form_options.get('conditions', []):
            try:
                cond_value, cond_expression, cond_key = condition.split('|')
            except ValueError:
                raise ConfigurationErrorInvalidCondition(
                    condition, 'Needs to have form "value|condition|key"')
            # Check that value exists
            if cond_value not in [str(v[0]) for v in self.choices]:
                raise ConfigurationErrorInvalidCondition(
                    condition, 'Value "{}" of condition not found in the Key\''
                    's choices'.format(cond_value))
            # Check the condition expression
            try:
                cond_expression = eval(cond_expression)
            except SyntaxError:
                raise ConfigurationErrorInvalidCondition(
                    condition, 'Expression "{}" is not a valid Python '
                    'condition'.format(cond_expression))
            if not isinstance(cond_expression, bool):
                raise ConfigurationErrorInvalidCondition(
                    condition,
                    'Only the following Python expressions are valid: bool')
            # TODO
            # Check that the key exists in the same questiongroup.
            # cond_key_object = self.questiongroup.get_question_by_key_keyword(
            #     cond_key)
            # if cond_key_object is None:
            #     raise ConfigurationErrorInvalidCondition(
            #         condition,
            #         'Key "{}" is not in the same questiongroup'.format(
            #             cond_key))
            # if not (
            #         self.field_type == 'image_checkbox' and
            #         cond_key_object.field_type == 'image_checkbox'):
            #     raise ConfigurationErrorInvalidCondition(
            #         condition, 'Only valid for types "image_checkbox"')
            conditions.append((cond_value, cond_expression, cond_key))
        self.conditions = conditions

        questiongroup_conditions = []
        for questiongroup_condition in self.form_options.get(
                'questiongroup_conditions', []):
            try:
                cond_expression, cond_name = questiongroup_condition.split('|')
            except ValueError:
                raise ConfigurationErrorInvalidQuestiongroupCondition(
                    questiongroup_condition,
                    'Needs to have form "expression|name"')
            # Check the condition expression
            try:
                cond_expression = eval('{}{}'.format(0, cond_expression))
            except SyntaxError:
                raise ConfigurationErrorInvalidQuestiongroupCondition(
                    questiongroup_condition,
                    'Expression "{}" is not a valid Python condition'.format(
                        cond_expression))
            questiongroup_conditions.append(questiongroup_condition)

        self.questiongroup_conditions = questiongroup_conditions

        # TODO
        self.required = False

    def add_form(
            self, formfields, templates, options, show_translation=False,
            edit_mode='edit'):
        """
        Adds one or more fields to a dictionary of formfields.

        Args:
            ``formfields`` (dict): A dictionary of formfields.

            ``templates`` (dict): A dictionary with templates to be used
            to render the questions.

            ``options`` (dict): A dictionary with configuration options
            to be used by the template when rendering the questions.

            ``show_translation`` (bool): A boolean indicating whether to
            add additional fields for translation (``True``) or not
            (``False``). Defaults to ``False``.

            ``edit_mode`` (string): A string indicating the current mode
            of the form (eg. if it is read-only). Defaults to ``edit``.
            Valid options are:

                * ``edit``: Default form rendering.

                * ``view``: Read-only mode, all form fields rendered as
                  disabled.

        Returns:
            ``dict``. The updated formfields dictionary.

            ``dict``. The updated templates dictionary.
        """
        form_template = 'default'
        if self.field_type == 'measure':
            form_template = 'inline_3'
        elif self.field_type == 'image_checkbox':
            form_template = 'no_label'
        form_template = 'form/question/{}.html'.format(
            self.form_options.get('template', form_template))
        readonly_attrs = {'readonly': 'readonly'}
        field = None
        translation_field = None
        widget = None
        field_options = {
            'label': self.form_options.get('label'),
            'colclass': self.form_options.get('colclass'),
            'helptext': self.helptext,
            'helptext_position': self.form_options.get('helptext'),
            'helptext_choices': self.choices_helptexts,
            'additional_translations': self.additional_translations,
        }

        attrs = {}
        if edit_mode == 'view':
            # Read-only mode, disable all input fields.
            attrs.update({'disabled': 'disabled'})

        if self.field_type == 'char':
            max_length = self.max_length
            if max_length is None:
                max_length = 2000
            if self.form_options.get('label') == 'placeholder':
                attrs.update({'placeholder': self.label})
            widget = TextInput(attrs)
            widget.options = field_options
            field = forms.CharField(
                label=self.label, widget=widget,
                required=self.required, max_length=max_length)
            translation_field = forms.CharField(
                label=self.label, widget=forms.TextInput(attrs=readonly_attrs),
                required=self.required, max_length=max_length)
        elif self.field_type in ['user_id', 'user_display']:
            widget = HiddenInput()
            if self.field_type == 'user_id':
                widget.css_class = 'select-user-id'
            elif self.field_type == 'user_display':
                widget.css_class = 'select-user-display'
            field = forms.CharField(
                label=None, widget=widget, required=self.required)
        elif self.field_type == 'text':
            max_length = self.max_length
            if max_length is None:
                max_length = 5000
            attrs.update({'rows': self.num_rows})
            widget = forms.Textarea(attrs=attrs)
            field = forms.CharField(
                label=self.label, widget=widget,
                required=self.required, max_length=max_length)
            translation_field = forms.CharField(
                label=self.label, widget=forms.Textarea(attrs=readonly_attrs),
                required=self.required)
        elif self.field_type == 'bool':
            widget = RadioSelect(choices=self.choices, attrs=attrs)
            widget.options = field_options
            if self.form_options.get('extra') == 'inline':
                widget.template_name = 'form/field/radio_inline.html'
            field = forms.IntegerField(
                label=self.label, widget=widget,
                required=self.required)
        elif self.field_type == 'measure':
            widget = MeasureSelect(attrs=attrs)
            widget.options = field_options
            if self.form_options.get('extra', '') == 'stacked':
                widget = MeasureSelectStacked()
            field = forms.ChoiceField(
                label=self.label, choices=self.choices, widget=widget,
                required=self.required)
        elif self.field_type == 'select':
            widget = Select(attrs=attrs)
            widget.options = field_options
            widget.searchable = False
            field = forms.ChoiceField(
                label=self.label, choices=self.choices, widget=widget,
                required=self.required)
        elif self.field_type == 'radio':
            widget = RadioSelect(choices=self.choices, attrs=attrs)
            widget.options = field_options
            field = forms.ChoiceField(
                label=self.label, choices=self.choices, widget=widget,
                required=self.required)
        elif self.field_type in ['checkbox', 'cb_bool']:
            widget = Checkbox(attrs=attrs)
            widget.options = field_options
            field = forms.MultipleChoiceField(
                label=self.label, widget=widget, choices=self.choices,
                required=self.required)
        elif self.field_type == 'image_checkbox':
            # Make the image paths available to the widget
            widget = ImageCheckbox(attrs=attrs)
            widget.images = self.images
            widget.options = field_options
            field = forms.MultipleChoiceField(
                label=self.label, widget=widget, choices=self.choices,
                required=self.required)
        elif self.field_type == 'image':
            widget = ImageUpload(attrs=attrs)
            formfields['file_{}'.format(self.keyword)] = forms.FileField(
                widget=widget, required=self.required, label=self.label)
            field = forms.CharField(
                required=self.required, widget=forms.HiddenInput())
        elif self.field_type == 'select_type':
            widget = Select(attrs=attrs)
            widget.options = field_options
            widget.searchable = True
            field = forms.ChoiceField(
                label=self.label, widget=widget, choices=self.choices,
                required=self.required)
        elif self.field_type == 'todo':
            field = forms.CharField(
                label=self.label,
                widget=forms.TextInput(
                    attrs={'readonly': 'readonly', 'value': '[TODO]'}),
                required=self.required)
        else:
            raise ConfigurationErrorInvalidOption(
                self.field_type, 'type', self)

        if translation_field is None:
            # Values which are not translated
            formfields[self.keyword] = field
            templates[self.keyword] = form_template
            options[self.keyword] = field_options
        else:
            # Store the old values in a hidden field
            old = forms.CharField(
                label=self.label, widget=forms.HiddenInput(),
                required=self.required)
            if show_translation:
                formfields['{}{}'.format(
                    self.translation_translation_prefix,
                    self.keyword)] = translation_field
            formfields['{}{}'.format(
                self.translation_original_prefix, self.keyword)] = field
            formfields['{}{}'.format(
                self.translation_old_prefix, self.keyword)] = old
            for f in [
                '{}{}'.format(
                    self.translation_translation_prefix,
                    self.keyword),
                '{}{}'.format(
                    self.translation_original_prefix, self.keyword),
                '{}{}'.format(
                    self.translation_old_prefix, self.keyword)
            ]:
                templates[f] = form_template
                options[f] = field_options

        if widget:
            widget.conditional = self.conditional
            widget.conditions = self.conditions
            widget.questiongroup_conditions = ','.join(
                self.questiongroup_conditions)

        return formfields, templates, options

    def get_details(self, data={}, measure_label=None):
        MAX_MEASURE_LEVEL = 5
        template_values = {
            'view_label': self.view_options.get('label'),
            'header': self.view_options.get('header'),
            'extra': self.view_options.get('extra'),
            'additional_translations': self.additional_translations,
        }
        value = data.get(self.keyword)
        if self.field_type in [
                'bool', 'measure', 'checkbox', 'image_checkbox',
                'select_type', 'select', 'cb_bool', 'radio']:
            # Look up the labels for the predefined values
            if not isinstance(value, list):
                value = [value]
            values = self.lookup_choices_labels_by_keywords(value)
        if self.field_type in ['char', 'text', 'todo', 'user_display']:
            template_name = 'textarea'
            template_values.update({
                'key': self.label_view,
                'value': value,
            })
        elif self.field_type in ['bool', 'select_type', 'select']:
            template_name = 'textinput'
            template_values.update({
                'key': self.label_view,
                'value': values[0],
            })
        elif self.field_type in ['measure']:
            template_name = 'measure_bar'
            level = None
            try:
                pos = [c[1] for c in self.choices].index(values[0])
                level = round(pos / len(self.choices) * MAX_MEASURE_LEVEL)
            except ValueError:
                pass
            if measure_label is None:
                key = self.label_view
            else:
                key = measure_label
            template_values.update({
                'key': key,
                'value': values[0],
                'level': level,
            })
        elif self.field_type in ['checkbox', 'cb_bool', 'radio']:
            template_name = 'checkbox'
            if self.view_options.get('extra') == 'raw_values':
                # Also add the raw keywords of the values.
                value_keywords = []
                for v in value:
                    if v is not None:
                        i = [y[0] for y in list(self.choices)].index(v)
                        value_keywords.append(self.choices[i][0])
                values = list(zip(values, value_keywords))
            template_values.update({
                'key': self.label_view,
                'values': values,
            })
        elif self.field_type in ['image_checkbox']:
            conditional_outputs = []
            for v in value:
                conditional_rendered = None
                for cond in self.conditions:
                    if v != cond[0]:
                        continue
                    cond_key_object = self.questiongroup.\
                        get_question_by_key_keyword(cond[2])
                    conditional_rendered = cond_key_object.get_details(data)
                conditional_outputs.append(conditional_rendered)

            # Look up the image paths for the values
            images = []
            value_keywords = []
            for v in value:
                if v is not None:
                    i = [y[0] for y in list(self.choices)].index(v)
                    value_keywords.append(self.choices[i][0])
                    images.append(self.images[i])
            template_name = 'image_checkbox'
            if self.conditional:
                template_name = 'image_checkbox_conditional'
            template_values.update({
                'key': self.label_view,
                'values': list(zip(
                    values, images, conditional_outputs, value_keywords)),
            })
        elif self.field_type in ['image']:
            value = get_url_by_identifier(value)
            template_name = 'image'
            template_values.update({
                'key': self.label_view,
                'value': value,
            })
        elif self.field_type in ['user_id']:
            return
        else:
            raise ConfigurationErrorInvalidOption(
                self.field_type, 'type', self)

        if (self.form_options.get('extra', '') == 'stacked'
                or self.view_options.get('extra', '') == 'stacked'):
            if self.view_options.get('label', '') == 'none':
                key = None
            # Add all values and their measure value.
            all_values = []
            for choice in self.choices:
                current_level = 1
                for v in values:
                    if v == choice[1]:
                        current_level = MAX_MEASURE_LEVEL
                all_values.append((current_level, choice[1]))
            template_values.update({'all_values': all_values})

        template_name = self.view_options.get('template', template_name)
        if template_name == 'raw':
            return template_values
        template = 'details/field/{}.html'.format(template_name)
        return render_to_string(template, template_values)

    def lookup_choices_labels_by_keywords(self, keywords):
        """
        Small helper function to lookup the label of choices (values of
        the keys) based on their keyword. If a label is not found, an
        empty string is added as label.

        Args:
            ``keywords`` (list): A list with value keywords.

        Returns:
            ``list``. A list with labels of the values.
        """
        labels = []
        for keyword in keywords:
            if (not isinstance(keyword, str) and not isinstance(keyword, bool)
                    and not isinstance(keyword, int)):
                labels.append('')
            labels.append(dict(self.choices).get(keyword))
        return labels


class QuestionnaireQuestiongroup(BaseConfigurationObject):
    """
    A class representing the configuration of a Questiongroup of the
    Questionnaire.
    """
    valid_options = [
        'keyword',
        'questions',
        'view_options',
        'form_options',
    ]
    default_template = 'default'
    default_min_num = 1
    name_current = 'questiongroups'
    name_parent = 'subcategories'
    name_children = 'questions'
    Child = QuestionnaireQuestion

    def __init__(self, parent_object, configuration):
        """
        Parameter ``configuration`` is a ``dict`` containing the
        configuration of the Questiongroup. It needs to have the
        following format::

          {
            # The keyword of the questiongroup.
            "keyword": "QUESTIONGROUP_KEYWORD",

            # (optional)
            "view_options": {
              # Default: "default"
              "template": "TEMPLATE_NAME",

              # Default: ""
              "extra": "measure_other",

              # Default: ""
              "colclass": "top-margin"
            },

            # (optional)
            "form_options": {
              # Default: "default"
              "template": "TEMPLATE_NAME",

              # Default: 1
              "min_num": 2,

              # Default: 1
              "max_num: 3,

              # Default: ""
              "numbered": "NUMBERED",

              # Default: ""
              "detail_level": "DETAIL_LEVEL",

              # Default: ""
              "questiongroup_condition": "CONDITION_NAME",
            },

            # A list of questions.
            "questions": [
              # ...
            ]
          }

        .. seealso::
            For more information on the format and the configuration
            options, please refer to the documentation:
            :doc:`/configuration/questiongroup`

        Raises:
            :class:`qcat.errors.ConfigurationErrorInvalidConfiguration`
        """
        super(QuestionnaireQuestiongroup, self).__init__(
            parent_object, configuration)
        self.questions = self.children

        self.configuration = self.configuration_object.configuration

        view_options = self.configuration.get('view_options', {})
        if configuration.get('view_options'):
            view_options.update(configuration.get('view_options'))
        self.view_options = view_options

        form_options = self.configuration.get('form_options', {})
        if configuration.get('form_options'):
            form_options.update(configuration.get('form_options'))
        self.form_options = form_options

        self.min_num = self.form_options.get('min_num', self.default_min_num)
        if not isinstance(self.min_num, int) or self.min_num < 1:
            raise ConfigurationErrorInvalidConfiguration(
                'min_num', 'integer >= 1', 'questiongroup')

        self.max_num = self.form_options.get('max_num', self.min_num)
        if not isinstance(self.max_num, int) or self.max_num < 1:
            raise ConfigurationErrorInvalidConfiguration(
                'max_num', 'integer >= 1', 'questiongroup')

        self.questiongroup_condition = self.form_options.get(
            'questiongroup_condition')

        self.numbered = self.form_options.get('numbered', '')
        if self.numbered not in ['inline', 'prefix']:
            self.numbered = ''

        self.detail_level = self.form_options.get('detail_level')

        # TODO
        self.required = False

    def get_form(
            self, post_data=None, initial_data=None, show_translation=False,
            edit_mode='edit', edited_questiongroups=[]):
        """
        Returns:
            ``forms.formset_factory``. A formset consisting of one or
            more form fields representing a set of questions belonging
            together and which can possibly be repeated multiple times.
        """
        form_template = 'form/questiongroup/{}.html'.format(
            self.form_options.get('template', 'default'))
        formfields = {}
        templates = {}
        options = {}
        for f in self.questions:
            formfields, templates, options = f.add_form(
                formfields, templates, options, show_translation,
                edit_mode=edit_mode)

        if self.numbered != '':
            formfields['__order'] = forms.IntegerField(
                label='order', widget=forms.HiddenInput())
            if isinstance(initial_data, list):
                initial_data = sorted(
                    initial_data, key=lambda qg: qg.get('__order', 0))

        Form = type('Form', (forms.Form,), formfields)

        formset_options = {
            'max_num': self.max_num,
            'min_num': self.min_num,
            'extra': 0,
            'validate_max': True,
            'validate_min': True,
        }

        if self.required is True:
            FormSet = formset_factory(
                Form, formset=RequiredFormSet, **formset_options)
        else:
            FormSet = formset_factory(Form, **formset_options)

        if initial_data and len(initial_data) == 1 and initial_data[0] == {}:
            initial_data = None

        has_changes = False
        if self.keyword in edited_questiongroups:
            has_changes = True

        config = {
            'keyword': self.keyword,
            'helptext': self.helptext,
            'label': self.label,
            'templates': templates,
            'options': options,
            'questiongroup_condition': self.questiongroup_condition,
            'numbered': self.numbered,
            'detail_level': self.detail_level,
            'template': form_template,
            'extra': self.view_options.get('extra'),
            'has_changes': has_changes,
        }

        return config, FormSet(
            post_data, prefix=self.keyword, initial=initial_data)

    def get_rendered_questions(self, data):
        questiongroups = []
        for d in data:
            rendered_questions = []
            if self.view_options.get('extra') == 'measure_other':
                measure_label = d.get(self.questions[0].keyword, '')
                rendered_questions.append(
                    self.questions[1].get_details(
                        d, measure_label=measure_label))
                if len(self.questions) > 2:
                    for question in self.questions[2:]:
                        if question.conditional:
                            continue
                        rendered_questions.append(question.get_details(d))
            else:
                for question in self.questions:
                    if question.conditional:
                        continue

                    question_details = question.get_details(d)
                    if question_details:
                        rendered_questions.append(question_details)
            questiongroups.append(rendered_questions)
        return questiongroups

    def get_details(self, data=[]):
        view_template = 'details/questiongroup/{}.html'.format(
            self.view_options.get('template', 'default'))
        questiongroups = self.get_rendered_questions(data)
        config = {
            'numbered': self.numbered,
            'columns': self.view_options.get('columns'),
            'extra': self.view_options.get('extra'),
            'colclass': self.view_options.get('colclass'),
            'label': self.label,
        }
        if self.view_options.get('raw_questions', False) is True:
            raw_questions = []
            for d in data:
                raw_questions.append(self.get_raw_data([d]))
            return render_to_string(
                view_template, {
                    'raw_questions': raw_questions,
                    'config': config,
                })
        rendered = render_to_string(
            view_template, {
                'questiongroups': questiongroups,
                'config': config,
            })
        return rendered

    def get_question_by_key_keyword(self, key_keyword):
        for question in self.questions:
            if question.keyword == key_keyword:
                return question
        return None

    def get_raw_data(self, data):
        """
        Return only the raw data of a questiongroup. Data belonging to
        this questiongroup is returned as a flat dictionary. Predefined
        values are looked up to return their display value. The label of
        the key is also added to the dict.

        Args:
            ``questionnaire_data`` (dict): The questionnaire data
            dictionary.

        Returns:
            ``dict``. A flat dictionary with only the keys and values of
            the current questiongroup.
        """
        raw_data = {}
        for question in self.questions:
            for questiongroup_data in data:
                question_data = questiongroup_data.get(
                    question.keyword)
                # Still look up the display values for fields
                # with predefined internal values.
                if question.field_type in [
                        'bool', 'measure', 'checkbox',
                        'image_checkbox', 'select_type', 'radio']:
                    if not isinstance(question_data, list):
                        question_data = [question_data]
                    question_data = question.\
                        lookup_choices_labels_by_keywords(
                            question_data)
                raw_data[question.keyword] = question_data
                raw_data['label_{}'.format(question.keyword)]\
                    = question.label_view
        return raw_data


class QuestionnaireSubcategory(BaseConfigurationObject):
    """
    A class representing the configuration of a Subcategory of the
    Questionnaire.
    """
    valid_options = [
        'keyword',
        'questiongroups',
        'subcategories',
        'form_options',
        'view_options',
    ]
    name_current = 'subcategories'
    name_parent = 'categories'
    name_children = 'questiongroups'
    Child = QuestionnaireQuestiongroup

    def __init__(self, parent_object, configuration):
        """
        Parameter ``configuration`` is a ``dict`` containing the
        configuration of the Subcategory. It needs to have the following
        format::

          {
            # The keyword of the subcategory.
            "keyword": "SUBCAT_KEYWORD",

            # (optional)
            "view_options": {
              # Default: "default"
              "template": "TEMPLATE_NAME",

              # Default: None
              "table_grouping": []
            },

            # (optional)
            "form_options": {
              # Default: "default"
              "template": "TEMPLATE_NAME"
            },

            # A list of questiongroups.
            "questiongroups": [
              # ...
            ],

            # A list of subcategories.
            "subcategories": [
              # ...
            ]
          }

        .. seealso::
            For more information on the format and the configuration
            options, please refer to the documentation:
            :doc:`/configuration/subcategory`

        Raises:
            :class:`qcat.errors.ConfigurationErrorInvalidConfiguration`,
            ``ConfigurationErrorNotInDatabase``.
        """
        super(QuestionnaireSubcategory, self).__init__(
            parent_object, configuration)

        view_options = self.configuration.get('view_options', {})
        if configuration.get('view_options'):
            view_options.update(configuration.get('view_options'))
        self.view_options = view_options

        form_options = self.configuration.get('form_options', {})
        if configuration.get('form_options'):
            form_options.update(configuration.get('form_options'))
        self.form_options = form_options

        # A Subcategory can have further subcategories or questiongroups
        subcategories = []
        conf_subcategories = self.configuration.get('subcategories', [])
        for conf_subcategory in conf_subcategories:
            subcategories.append(
                QuestionnaireSubcategory(self, conf_subcategory))
        self.subcategories = subcategories

        questiongroups = []
        conf_questiongroups = self.configuration.get('questiongroups', [])
        for conf_questiongroup in conf_questiongroups:
            questiongroups.append(
                QuestionnaireQuestiongroup(self, conf_questiongroup))
        self.questiongroups = questiongroups

        if len(self.subcategories) > 0:
            self.children = self.subcategories
        else:
            self.children = self.questiongroups

        self.table_grouping = self.view_options.get('table_grouping', None)
        self.table_headers = []
        self.table_helptexts = []
        if self.table_grouping:
            for questiongroup in self.questiongroups:
                if questiongroup.keyword in [
                        g[0] for g in self.table_grouping]:
                    for question in questiongroup.questions:
                        self.table_headers.append(question.label)
                        self.table_helptexts.append(question.helptext)

    def get_form(
            self, post_data=None, initial_data={}, show_translation=False,
            edit_mode='edit', edited_questiongroups=[]):
        """
        Returns:
            ``dict``. A dict with configuration elements, namely ``label``.
            ``list``. A list of formsets of question groups, together
            forming a subcategory.
        """
        form_template = 'form/subcategory/{}.html'.format(
            self.form_options.get('template', 'default'))
        formsets = []
        config = {
            'label': self.label,
            'helptext': self.helptext,
            'numbering': self.numbering,
            'form_template': form_template,
            'extra': self.form_options.get('extra'),
        }
        has_changes = False
        for questiongroup in self.questiongroups:
            questionset_initial_data = initial_data.get(questiongroup.keyword)
            formsets.append(
                questiongroup.get_form(
                    post_data=post_data, initial_data=questionset_initial_data,
                    show_translation=show_translation, edit_mode=edit_mode,
                    edited_questiongroups=edited_questiongroups))
            config['next_level'] = 'questiongroups'
            if questiongroup.keyword in edited_questiongroups:
                has_changes = True
        for subcategory in self.subcategories:
            formsets.append(
                subcategory.get_form(
                    post_data=post_data, initial_data=initial_data,
                    show_translation=show_translation, edit_mode=edit_mode,
                    edited_questiongroups=edited_questiongroups))
            config['next_level'] = 'subcategories'

        config.update({'has_changes': has_changes})

        if self.table_grouping:
            config.update({
                'table_grouping': self.table_grouping,
                'table_headers': self.table_headers,
                'table_helptexts': self.table_helptexts,
            })

        return config, formsets

    def get_details(self, data={}):
        """
        Returns:
            ``string``. A rendered representation of the subcategory
            with its questiongroups.

            ``bool``. A boolean indicating whether the subcategory and
            its questiongroups have some data in them or not.
        """
        view_template = 'details/subcategory/{}.html'.format(
            self.view_options.get('template', 'default'))
        rendered_questiongroups = []
        rendered_questions = []
        raw_questiongroups = []
        has_content = False
        for questiongroup in self.questiongroups:
            questiongroup_data = data.get(questiongroup.keyword, [])
            if not is_empty_list_of_dicts(questiongroup_data):
                has_content = True
                if self.table_grouping and questiongroup.keyword in [
                        item for sublist in self.table_grouping
                        for item in sublist]:
                    # Order the values of the questiongroups according
                    # to their questions
                    q_order = [q.keyword for q in questiongroup.questions]
                    # qg_data = []
                    # Add empty values for all keys not available to
                    # keep the order inside the table even with empty
                    # values.
                    for qg in questiongroup_data:
                        for q in q_order:
                            if q not in qg:
                                qg[q] = []
                    sorted_questiongroup_data = [
                        sorted(qg.items(), key=lambda i: q_order.index(i[0]))
                        for qg in questiongroup_data]

                    data_labelled = []
                    for qg in sorted_questiongroup_data:
                        qg_labelled = []
                        for q in qg:
                            q_value = q[1]
                            q_obj = questiongroup.get_question_by_key_keyword(
                                q[0])
                            if not q_obj:
                                continue
                            if not isinstance(q_value, list):
                                q_value = [q_value]
                            values = []
                            for v in q_value:
                                q_choice = next((
                                    item for item in q_obj.choices if
                                    item[0] == v), None)
                                if q_choice:
                                    values.append(q_choice[1])
                                else:
                                    values.append(v)
                            qg_labelled.append((q_obj.label, values))
                        data_labelled.append(qg_labelled)
                    raw_questiongroups.append({
                        'qg_keyword': questiongroup.keyword,
                        'data': sorted_questiongroup_data,
                        'data_labelled': data_labelled,
                        'label': questiongroup.label,
                        'extra': questiongroup.view_options.get('extra'),
                    })
                elif self.view_options.get('raw_questions', False) is True:
                    rendered_questions.append({
                        'qg': questiongroup.keyword,
                        'extra': questiongroup.view_options.get('extra'),
                        'questions': questiongroup.get_rendered_questions(
                            questiongroup_data),
                    })
                else:
                    questiongroup_config = {
                        'keyword': questiongroup.keyword,
                        'label': questiongroup.label,
                        'extra': questiongroup.view_options.get('extra'),
                    }
                    rendered_questiongroups.append((
                        questiongroup_config,
                        questiongroup.get_details(questiongroup_data)))
        subcategories = []
        for subcategory in self.subcategories:
            sub_rendered, sub_has_content = subcategory.get_details(data=data)
            if sub_has_content:
                subcategories.append(sub_rendered)
                has_content = True

        template_values = {
            'questiongroups': rendered_questiongroups,
            'questions': rendered_questions,
            'subcategories': subcategories,
            'label': self.label_view,
            'numbering': self.numbering,
            'helptext': self.helptext,
            'header': self.view_options.get('header'),
        }
        if self.table_grouping:
            template_values.update({
                'table_grouping': self.table_grouping,
                'table_headers': self.table_headers,
                'raw_questiongroups': raw_questiongroups,
            })
        rendered = render_to_string(view_template, template_values)
        return rendered, has_content


class QuestionnaireCategory(BaseConfigurationObject):
    """
    A class representing the configuration of a Category of the
    Questionnaire.
    """
    valid_options = [
        'keyword',
        'subcategories',
        'view_options',
    ]
    name_current = 'categories'
    name_parent = 'sections'
    name_children = 'subcategories'
    Child = QuestionnaireSubcategory

    def __init__(self, parent_object, configuration):
        """
        Parameter ``configuration`` is a ``dict`` containing the
        configuration of the Category. It needs to have the following
        format::

          {
            # The keyword of the category.
            "keyword": "CAT_KEYWORD",

            # (optional)
            "view_options": {
              # Default: "default"
              "template": "TEMPLATE_NAME",

              # Default: false
              "include_toc": true,

              # Default: false
              "use_raw_data": true,

              # Default: false
              "with_metadata": true,

              # Default: {}
              "additional_data": {
                "QUESTIONGROUP": ["KEY"]
              }
            },

            # A list of subcategories.
            "subcategories": [
              {
                # ...
              }
            ]
          }

        .. seealso::
            For more information on the format and the configuration
            options, please refer to the documentation:
            :doc:`/configuration/category`
        """
        super(QuestionnaireCategory, self).__init__(
            parent_object, configuration)
        self.subcategories = self.children

        view_options = self.configuration.get('view_options', {})
        if configuration.get('view_options'):
            view_options.update(configuration.get('view_options'))
        self.view_options = view_options

        form_options = self.configuration.get('form_options', {})
        if configuration.get('form_options'):
            form_options.update(configuration.get('form_options'))
        self.form_options = form_options

    def get_form(
            self, post_data=None, initial_data={}, show_translation=False,
            edit_mode='edit', edited_questiongroups=[]):
        """
        Returns:
            ``dict``. A dict with configuration elements, namely ``label``.
            ``list``. A list of a list of subcategory formsets.
        """
        subcategory_formsets = []
        for subcategory in self.subcategories:
            subcategory_formsets.append(
                subcategory.get_form(
                    post_data=post_data, initial_data=initial_data,
                    show_translation=show_translation, edit_mode=edit_mode,
                    edited_questiongroups=edited_questiongroups))
        has_changes = False
        for qg in self.get_questiongroups():
            if qg.keyword in edited_questiongroups:
                has_changes = True
                break
        config = {
            'label': self.label,
            'numbering': self.numbering,
            'helptext': self.helptext,
            'has_changes': has_changes,
        }
        configuration = self.view_options.get('configuration')
        if configuration:
            config.update({'configuration': configuration})
        return config, subcategory_formsets

    def get_details(
            self, data={}, permissions=[], edit_step_route='',
            questionnaire_object=None, csrf_token=None,
            edited_questiongroups=[], view_mode='view'):
        view_template = 'details/category/{}.html'.format(
            self.view_options.get('template', 'default'))
        rendered_subcategories = []
        with_content = 0
        raw_data = {}
        metadata = {}
        for subcategory in self.subcategories:
            rendered_subcategory, has_content = subcategory.get_details(data)
            if has_content:
                category_config = {
                    'keyword': subcategory.keyword
                }
                rendered_subcategories.append(
                    (rendered_subcategory, category_config))
                with_content += 1

        if (self.view_options.get('with_metadata', False) is True
                and questionnaire_object is not None):
            metadata = questionnaire_object.get_metadata()

        if self.view_options.get('use_raw_data', False) is True:
            raw_data = self.get_raw_category_data(data)

        additional_data = {}
        additional_keys = self.view_options.get('additional_data', {})
        if additional_keys != {}:
            for qg in self.parent_object.parent_object.get_questiongroups():
                if qg.keyword not in [
                        a[0] for a in additional_keys.items()]:
                    continue

                qg_data = data.get(qg.keyword, [])
                for key in additional_keys[qg.keyword]:
                    question = qg.get_question_by_key_keyword(key)
                    additional_entry = []
                    for d in qg_data:
                        k = d.get(key)
                        if k is None:
                            continue
                        if question.field_type in [
                                'bool', 'measure', 'checkbox',
                                'image_checkbox', 'select_type', 'radio']:
                            if not isinstance(k, list):
                                k = [k]
                            k = question.\
                                lookup_choices_labels_by_keywords(k)
                        additional_entry.append(k)
                    additional_data[key] = additional_entry
                    additional_data[
                        'label_{}'.format(key)] = question.label_view

        questionnaire_identifier = 'new'
        if questionnaire_object is not None:
            questionnaire_identifier = questionnaire_object.code

        toc_content = []
        if self.view_options.get('include_toc', False) is True:
            toc_content = self.parent_object.parent_object.get_toc_data()

        configuration = self.view_options.get(
            'configuration', self.configuration_keyword)

        has_changes = False
        for qg in self.get_questiongroups():
            if qg.keyword in edited_questiongroups:
                has_changes = True
                break

        return render_to_string(
            view_template, {
                'subcategories': rendered_subcategories,
                'raw_data': raw_data,
                'additional_data': additional_data,
                'metadata': metadata,
                'label': self.label,
                'numbering': self.numbering,
                'keyword': self.keyword,
                'csrf_token': csrf_token,
                'permissions': permissions,
                'view_mode': view_mode,
                'complete': with_content,
                'total': len(self.subcategories),
                'progress': int(with_content / len(self.subcategories) * 100),
                'edit_step_route': edit_step_route,
                'configuration_name': configuration,
                'toc_content': tuple(toc_content),
                'questionnaire_identifier': questionnaire_identifier,
                'has_changes': has_changes,
            })

    def get_raw_category_data(self, questionnaire_data):
        """
        Return only the raw data of a category. The entire questionnaire
        data is scanned for the questiongroups belonging to the current
        category. Only the data of these questiongroups is then
        returned as a flat dict.

        .. important::
            This function may return unexpected outputs when used on
            categories with repeating questiongroups or with keys having
            the same keyword.

        Args:
            ``questionnaire_data`` (dict): The questionnaire data
            dictionary.

        Returns:
            ``dict``. A flat dictionary with only the keys and values of
            the current category.
        """
        raw_category_data = {}
        for subcategory in self.subcategories:
            for questiongroup in subcategory.questiongroups:
                questiongroups_data = questionnaire_data.get(
                    questiongroup.keyword, {})
                raw_category_data.update(questiongroup.get_raw_data(
                    questiongroups_data))
        return raw_category_data

    def get_questiongroups(self):
        def unnest_questiongroups(nested):
            ret = []
            try:
                for child in nested.children:
                    if not isinstance(child, QuestionnaireQuestiongroup):
                        ret.extend(unnest_questiongroups(child))
                    else:
                        ret.append(child)
            except AttributeError:
                pass
            return ret
        return unnest_questiongroups(self)


class QuestionnaireSection(BaseConfigurationObject):
    """
    A class representing the configuration of a Section of the
    Questionnaire.
    """
    valid_options = [
        'categories',
        'keyword',
        'view_options',
    ]
    name_current = 'sections'
    name_parent = None
    name_children = 'categories'
    Child = QuestionnaireCategory

    def __init__(self, parent_object, configuration):
        """
        Parameter ``configuration`` is a ``dict`` containing the
        configuration of the Section. It needs to have the following
        format::

          {
            # The keyword of the section.
            "keyword": "SECTION_KEYWORD",

            # (optional)
            "view_options": {
              # Default: "default"
              "template": "TEMPLATE_NAME",

              # Default: false
              "review_panel": true,

              # Default: false
              "include_toc": true,

              # Default: false
              "media_gallery": true
            },

            # A list of categories.
            "categories": [
              {
                # ...
              }
            ]
          }

        .. seealso::
            For more information on the format and the configuration
            options, please refer to the documentation:
            :doc:`/configuration/section`
        """
        super(QuestionnaireSection, self).__init__(
            parent_object, configuration)
        self.categories = self.children

        view_options = self.configuration.get('view_options', {})
        if configuration.get('view_options'):
            view_options.update(configuration.get('view_options'))
        self.view_options = view_options

        form_options = self.configuration.get('form_options', {})
        if configuration.get('form_options'):
            form_options.update(configuration.get('form_options'))
        self.form_options = form_options

    def get_details(
            self, data={}, permissions=[], review_config={},
            edit_step_route='', questionnaire_object=None, csrf_token=None,
            edited_questiongroups=[], view_mode='view'):

        view_template = 'details/section/{}.html'.format(
            self.view_options.get('template', 'default'))

        if self.view_options.get('review_panel', False) is not True:
            review_config = {}

        rendered_categories = []
        for category in self.categories:
            rendered_categories.append(category.get_details(
                data, permissions=permissions, edit_step_route=edit_step_route,
                questionnaire_object=questionnaire_object,
                csrf_token=csrf_token,
                edited_questiongroups=edited_questiongroups,
                view_mode=view_mode))

        toc_content = []
        if self.view_options.get('include_toc', False) is True:
            toc_content = self.parent_object.get_toc_data()

        media_content = []
        media_additional = {}
        if self.view_options.get('media_gallery', False) is True:
            media_data = self.parent_object.get_image_data(
                data, interchange_as_list=True)
            media_content = media_data.get('content', [])
            media_additional = media_data.get('additional', {})

        return render_to_string(view_template, {
            'label': self.label,
            'keyword': self.keyword,
            'categories': rendered_categories,
            'toc_content': toc_content,
            'media_content': media_content,
            'media_additional': media_additional,
            'review_config': review_config,
        })

    def get_questiongroups(self):
        def unnest_questiongroups(nested):
            ret = []
            try:
                for child in nested.children:
                    if not isinstance(child, QuestionnaireQuestiongroup):
                        ret.extend(unnest_questiongroups(child))
                    else:
                        ret.append(child)
            except AttributeError:
                pass
            return ret
        return unnest_questiongroups(self)


class QuestionnaireConfiguration(BaseConfigurationObject):
    """
    A class representing the configuration of a Questionnaire.

    .. seealso::
        For more information on the format and the configuration
        options, please refer to the documentation:
        :doc:`/configuration/questionnaire`
    """
    valid_options = [
        'sections',
        'links',
    ]
    name_current = '-'
    name_parent = '-'
    name_children = 'sections'
    Child = QuestionnaireSection

    def __init__(self, keyword, configuration_object=None):
        self.keyword = keyword
        self.configuration_keyword = keyword
        self.sections = []
        self.configuration_object = configuration_object
        if self.configuration_object is None:
            self.configuration_object = Configuration.get_active_by_code(
                self.keyword)
        self.configuration_error = None
        try:
            self.read_configuration()
        except Exception as e:
            if isinstance(e, ConfigurationError):
                self.configuration_error = e
            else:
                raise e

    def get_configuration_errors(self):
        return self.configuration_error

    def add_category(self, category):
        self.categories.append(category)

    def get_category(self, keyword):
        for section in self.sections:
            for category in section.categories:
                if category.keyword == keyword:
                    return category
        return None

    def get_questiongroups(self):
        def unnest_questiongroups(nested):
            ret = []
            try:
                for child in nested.children:
                    if not isinstance(child, QuestionnaireQuestiongroup):
                        ret.extend(unnest_questiongroups(child))
                    else:
                        ret.append(child)
            except AttributeError:
                pass
            return ret
        return unnest_questiongroups(self)

    def get_questiongroup_by_keyword(self, keyword):
        for questiongroup in self.get_questiongroups():
            if questiongroup.keyword == keyword:
                return questiongroup
        return None

    def get_question_by_keyword(self, questiongroup_keyword, keyword):
        questiongroup = self.get_questiongroup_by_keyword(
            questiongroup_keyword)
        if questiongroup is not None:
            return questiongroup.get_question_by_key_keyword(keyword)
        return None

    def get_details(
            self, data={}, permissions=[], review_config={},
            edit_step_route='', questionnaire_object=None, csrf_token=None,
            edited_questiongroups=[], view_mode='view'):
        rendered_sections = []
        for section in self.sections:
            rendered_sections.append(section.get_details(
                data, permissions=permissions, review_config=review_config,
                edit_step_route=edit_step_route,
                questionnaire_object=questionnaire_object,
                csrf_token=csrf_token,
                edited_questiongroups=edited_questiongroups,
                view_mode=view_mode))
        return rendered_sections

    def get_toc_data(self):
        sections = []
        for section in self.sections:
            categories = []
            for category in section.categories:
                categories.append((category.keyword, category.label))
            sections.append(
                (section.keyword, section.label, tuple(categories)))
        return tuple(sections)

    def get_image_data(self, data, interchange_as_list=False):
        """
        Return image data from outside the category. Loops through all
        the fields to find the questiongroups containing images. For all
        these, basic information about the images are collected and
        returned as a list of dictionaries.

        Args:
            ``data`` (dict): A questionnaire data dictionary.

        Kwargs:
            ``interchange_as_list`` (bool): An boolean passed as
            ``as_list`` to :func:`get_interchange_urls_by_identifier`
            to return the interchange URLs as list instead of string.

        Returns:
            ``list``. A list of dictionaries for each image. Each
            dictionary has the following entries:

            - ``image``: The URL of the original image.

            - ``interchange``: The data which can be used for the
              interchange of images.

            - ``caption``: The caption of the image. Corresponds to
              field ``image_caption``.

            - ``date_location``: The date and location of the image.
              Corresponds to field ``image_date_location``.

            - ``photographer``: The photographer of the image.
              Corresponds to field ``image_photographer``.
        """
        image_questiongroups = []
        additional_data = {}
        for questiongroup in self.get_questiongroups():
            if questiongroup.keyword == 'qg_image_remarks':
                additional_data.update(
                    questiongroup.get_raw_data(
                        data.get('qg_image_remarks', [])))
            for question in questiongroup.questions:
                if question.field_type == 'image' and data.get(
                        questiongroup.keyword) is not None:
                    image_questiongroups.extend(
                        data.get(questiongroup.keyword))

        images = []
        for image in image_questiongroups:
            images.append({
                'image': get_url_by_identifier(image.get('image')),
                'interchange': get_interchange_urls_by_identifier(
                    image.get('image'), as_list=interchange_as_list),
                'caption': image.get('image_caption'),
                'date_location': image.get('image_date_location'),
                'photographer': image.get('image_photographer')
            })
        return {
            'content': images,
            'additional': additional_data,
        }

    def get_filter_configuration(self):
        """
        Return the data needed to create the filter panels. Loops the
        sections and within them the fields can be filtered.

        Returns:
            ``dict``. A dictionary with a list entry for section filters
            (``sections``) and additional entries for special filters
            such as ``countries``.

            Each section dictionary contains a list of dictionaries for
            each key within the section which can be filtered. Each
            dictionary has the following entries:

            - ``keyword``: The keyword of the section.

            - ``label``: The label of the section.

            - ``filters``: A list of dictionaries for each key of this
              section which is filterable. Each dictionary has the
              following entries:

              - ``keyword``: The keyword of the key.

              - ``label``: The label of the key.

              - ``values``: If available, the values as list of tuples.

              - ``type``: The type of the field (eg. ``checkbox``).

              - ``images`` : If available, the images as list of tuples.

              - ``questiongroup``: The keyword of the questiongroup.

            Each special filter (eg. ``countries``) contains a list of
            tuples with [0] the internal value and the [1] display value.
        """
        filter_configuration = []

        for section in self.sections:
            for cat in section.categories:
                for questiongroup in cat.get_questiongroups():
                    for question in questiongroup.questions:
                        if question.filterable is True:

                            s = next((
                                item for item in filter_configuration if
                                item["keyword"] == cat.keyword), None)

                            if not s:
                                s = {
                                    'keyword': cat.keyword,
                                    'label': cat.label,
                                    'filters': [],
                                }
                                filter_configuration.append(s)

                            s['filters'].append({
                                'keyword': question.keyword,
                                'label': question.label,
                                'values': question.choices,
                                'type': question.field_type,
                                'images': question.images,
                                'questiongroup': questiongroup.keyword,
                            })

        countries = []
        country_question = self.get_question_by_keyword(
            'qg_location', 'country')
        if country_question:
            countries = country_question.choices[1:]

        return {
            'sections': filter_configuration,
            'countries': countries,
        }

    def get_list_data(self, questionnaire_data_list):
        """
        Get the data for the list representation of questionnaires.
        Which questions are shown depends largely on the option
        ``in_list`` of the question configuration.

        Args:
            ``questionnaire_data_list`` (list): A list of Questionnaire
            data dicts.

        Returns:
            ``list``. A list of dicts. A dict containing the keys and
            values to be appearing in the list. The values are not
            translated.
        """
        # Collect which keys are to be shown in the list.
        list_configuration = []
        for questiongroup in self.get_questiongroups():
            for question in questiongroup.questions:
                if question.in_list is True:
                    list_configuration.append((
                        questiongroup.keyword, question.keyword,
                        question.field_type))

        questionnaire_value_list = []
        for questionnaire_data in questionnaire_data_list:
            questionnaire_value = {}
            for list_entry in list_configuration:
                for question_data in questionnaire_data.get(list_entry[0], []):
                    key = list_entry[1]
                    value = question_data.get(list_entry[1])
                    if list_entry[2] == 'image':
                        key = 'image'
                        value = get_url_by_identifier(value, 'default')
                    if list_entry[2] in [
                            'bool', 'measure', 'checkbox', 'image_checkbox',
                            'select_type']:
                        # Look up the labels for the predefined values
                        if not isinstance(value, list):
                            value = [value]
                        qg = self.get_questiongroup_by_keyword(list_entry[0])
                        if qg is None:
                            break
                        k = qg.get_question_by_key_keyword(list_entry[1])
                        if k is None:
                            break
                        values = k.lookup_choices_labels_by_keywords(value)
                        if list_entry[2] in ['bool', 'measure', 'select_type']:
                            value = values[0]
                    questionnaire_value[key] = value
            questionnaire_value_list.append(questionnaire_value)
        return questionnaire_value_list

    def get_links_configuration(self):
        try:
            return self.links_configuration
        except:
            return []

    def get_name_keywords(self):
        """
        Return the keywords of the question and questiongroup which
        contain the name of the questionnaire as defined in the
        configuration by the ``is_name`` parameter.
        """
        question_keyword = None
        questiongroup_keyword = None
        for questiongroup in self.get_questiongroups():
            for question in questiongroup.questions:
                if question.is_name is True:
                    question_keyword = question.keyword
                    questiongroup_keyword = questiongroup.keyword
        return question_keyword, questiongroup_keyword

    def get_questionnaire_name(self, questionnaire_data):
        """
        Return the value of the key flagged with ``is_name`` of a
        Questionnaire.

        Args:
            ``questionnaire_data`` (dict): A translated questionnaire
            data dictionary.

        Returns:
            ``str``. Returns the value of the key or ``Unknown`` if the
            key was not found in the data dictionary.
        """
        question_keyword, questiongroup_keyword = self.get_name_keywords()
        if question_keyword:
            for x in questionnaire_data.get(questiongroup_keyword, []):
                return x.get(question_keyword)
        return {'en': _('Unknown name')}

    def get_user_fields(self):
        """
        [0]: questiongroup keyword
        [1]: key keyword (id)
        [2]: key keyword (displayname)
        [3]: user role
        """
        user_fields = []
        for questiongroup in self.get_questiongroups():
            user_role = questiongroup.form_options.get('user_role')
            if user_role is None:
                continue
            for question in questiongroup.questions:
                if question.field_type != 'user_id':
                    continue
                user_fields.append(
                    (questiongroup.keyword, question.keyword,
                        question.form_options.get('display_field'), user_role))
        return user_fields

    def read_configuration(self):
        """
        This function reads an active configuration of a Questionnaire.
        If a configuration is found, it loads the configuration of all
        its sections.

        The configuration of the questionnaire needs to have the
        following format::

          {
            # See class QuestionnaireSection for the format of sections.
            "sections": [
              # ...
            ]
          }

        .. seealso::
            :class:`configuration.configuration.QuestionnaireSection`

        .. seealso::
            :doc:`/configuration/questionnaire`
        """
        if self.configuration_object is None:
            raise ConfigurationErrorNoConfigurationFound(self.keyword)

        specific_configuration = self.configuration_object.data
        base_configuration = {}
        if self.configuration_object.base_code:
            base_code = self.configuration_object.base_code
            base_configuration_object = Configuration.get_active_by_code(
                base_code)
            if base_configuration_object is None:
                raise ConfigurationErrorNoConfigurationFound(base_code)
            base_configuration = base_configuration_object.data

        self.configuration = self.merge_configurations(
            self, base_configuration, specific_configuration)
        self.validate_options()

        conf_sections = self.configuration.get('sections')
        validate_type(
            conf_sections, list, 'sections', 'list of dicts', '-')

        for conf_section in conf_sections:
            self.sections.append(QuestionnaireSection(self, conf_section))
        self.children = self.sections

        self.links_configuration = self.configuration.get('links', [])


def validate_type(obj, type_, conf_name, type_name, parent_conf_name):
    """
    Validate a type of object.

    Args:
        ``obj`` (obj): The object to validate.

        ``type_`` (type): A Python type (e.g. ``list``, ``dict``).

        ``conf_name`` (str): The name of the configuration entry (used
        for the error message)

        ``type_name`` (str): The name of the expected type (used for the
        error message)

        ``parent_conf_name`` (str): The name of the parent configuration
        entry (used for the error message)

    Raises:
        :class:`qcat.errors.ConfigurationErrorInvalidConfiguration`
    """
    if not isinstance(obj, type_):
        raise ConfigurationErrorInvalidConfiguration(
            conf_name, type_name, parent_conf_name)


class TextInput(forms.TextInput):
    template_name = 'form/field/textinput.html'

    def get_context_data(self):
        ctx = super(TextInput, self).get_context_data()
        ctx.update({
            'options': self.options,
        })
        return ctx


class HiddenInput(forms.TextInput):
    template_name = 'form/field/hidden.html'

    def get_context_data(self):
        ctx = super(HiddenInput, self).get_context_data()
        ctx.update({
            'css_class': self.css_class
        })
        return ctx


class RadioSelect(forms.RadioSelect):
    """
    A custom form class for a Radio Select field. Allows to overwrite
    the template used.
    """
    template_name = 'form/field/radio.html'

    def get_context_data(self):
        """
        Add the questiongroup conditions to the context data so they are
        available within the template of the widget.
        """
        ctx = super(RadioSelect, self).get_context_data()
        ctx.update({
            'questiongroup_conditions': self.questiongroup_conditions,
            'options': self.options,
        })
        return ctx


class Select(forms.Select):
    template_name = 'form/field/select.html'

    def get_context_data(self):
        """
        Add a variable (searchable or not) to the context data so it is
        available within the template of the widget.
        """
        ctx = super(Select, self).get_context_data()
        ctx.update({
            'searchable': self.searchable,
            'options': self.options,
        })
        return ctx


class MeasureSelect(forms.RadioSelect):
    template_name = 'form/field/measure.html'

    def get_context_data(self):
        """
        Add the questiongroup conditions to the context data so they are
        available within the template of the widget.
        """
        ctx = super(MeasureSelect, self).get_context_data()
        ctx.update({
            'questiongroup_conditions': self.questiongroup_conditions,
            'options': self.options,
        })
        return ctx


class MeasureSelectStacked(forms.RadioSelect):
    template_name = 'form/field/measure_stacked.html'

    def get_context_data(self):
        """
        Add the questiongroup conditions to the context data so they are
        available within the template of the widget.
        """
        ctx = super(MeasureSelectStacked, self).get_context_data()
        ctx.update({
            'questiongroup_conditions': self.questiongroup_conditions,
            'options': self.options,
        })
        return ctx


class Checkbox(forms.CheckboxSelectMultiple):
    template_name = 'form/field/checkbox.html'

    def get_context_data(self):
        """
        Add the questiongroup conditions to the context data so they are
        available within the template of the widget.
        """
        ctx = super(Checkbox, self).get_context_data()
        ctx.update({
            'questiongroup_conditions': self.questiongroup_conditions,
            'options': self.options,
        })
        return ctx


class ImageCheckbox(forms.CheckboxSelectMultiple):
    template_name = 'form/field/image_checkbox.html'

    def get_context_data(self):
        """
        Add the image paths to the context data so they are available
        within the template of the widget.
        """
        ctx = super(ImageCheckbox, self).get_context_data()
        ctx.update({
            'images': self.images,
            'conditional': self.conditional,
            'conditions': self.conditions,
            'options': self.options,
        })
        return ctx


class ImageUpload(forms.FileInput):
    template_name = 'form/field/image_upload.html'


class RequiredFormSet(BaseFormSet):
    def __init__(self, *args, **kwargs):
        super(RequiredFormSet, self).__init__(*args, **kwargs)
        for form in self.forms:
            form.empty_permitted = True
