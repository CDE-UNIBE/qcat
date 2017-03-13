import collections
import contextlib
import logging
from itertools import chain

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse, reverse_lazy
from django.db.models import Q
from django.http import (
    Http404,
    HttpResponse,
    JsonResponse,
    HttpResponseRedirect)
from django.middleware.csrf import get_token
from django.shortcuts import (
    render,
    redirect,
    get_object_or_404,
)
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _, get_language
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from django.views.generic import DeleteView, View
from django.views.generic.base import TemplateResponseMixin
from braces.views import LoginRequiredMixin

from accounts.decorators import force_login_check
from accounts.views import QuestionnaireSearchView
from configuration.cache import get_configuration
from configuration.utils import get_filter_configuration
from configuration.utils import (
    get_configuration_index_filter,
)
from questionnaire.signals import change_questionnaire_data
from questionnaire.upload import (
    retrieve_file,
    UPLOAD_THUMBNAIL_CONTENT_TYPE,
)
from search.search import advanced_search

from .errors import QuestionnaireLockedException
from .models import Questionnaire, File, QUESTIONNAIRE_ROLES, Lock


from .utils import (
    clean_questionnaire_data,
    get_active_filters,
    get_link_data,
    get_list_values,
    get_query_status_filter,
    get_questiongroup_data_from_translation_form,
    get_questionnaire_data_in_single_language,
    get_questionnaire_data_for_translation_form,
    handle_review_actions,
    query_questionnaire,
    query_questionnaires)
from .view_utils import (
    ESPagination,
    get_page_parameter,
    get_pagination_parameters,
    get_paginator,
    get_limit_parameter,
)
from .conf import settings

logger = logging.getLogger(__name__)


class QuestionnaireLinkSearchView(QuestionnaireSearchView, LoginRequiredMixin):
    """
    Search for a questionnaire to add as a link. Used in the questionnaire form
    as an ajax search. Searches by "term" in name and returns only
    questionnaires of the given configuration and visible to the current user
    (own drafts etc.)
    """
    configuration_code = None

    def dispatch(self, request, *args, **kwargs):
        # QuestionnaireSearchView's dispatch method checks for is_staff.
        return super(LoginRequiredMixin, self).dispatch(request, *args, **kwargs)

    def get_paginate_by(self, queryset):
        return 11

    def get_queryset(self):
        term = self.request.GET.get('term', '')
        return Questionnaire.with_status.not_deleted().filter(
            get_query_status_filter(self.request)
        ).filter(
            configurations__code=self.configuration_code
        ).filter(
            Q(data__qs_name=term)
        ).distinct()


def generic_questionnaire_view_step(
        request, identifier, step, configuration_code, page_title=''):
    """
    A generic view to show the form of a single step of a new or edited
    questionnaire.

    .. important::
        This view renders the form but has no submit logic implemented.
        It is to be used for display purposes (read-only) only!

    Args:
        ``request`` (django.http.HttpRequest): The request object.

        ``identifier`` (str): The identifier of a questionnaire.

        ``step`` (str): The code of the questionnaire category.

        ``configuration_code`` (str): The code of the questionnaire
        configuration.

    Kwargs:
        ``page_title`` (str): The page title to be used in the HTML
        template. Defaults to ``QCAT Form``.

    Returns:
        ``HttpResponse``. A rendered Http Response.
    """
    questionnaire_object = query_questionnaire(request, identifier).first()
    if questionnaire_object is None:
        raise Http404

    data = questionnaire_object.data

    questionnaire_configuration = get_configuration(configuration_code)
    category = questionnaire_configuration.get_category(step)

    if category is None:
        raise Http404

    valid = True
    show_translation = False
    edit_mode = 'view'
    original_locale = None
    current_locale = get_language()
    initial_data = get_questionnaire_data_for_translation_form(
        data, current_locale, original_locale)

    # TODO: Add inherited data here.
    category_config, subcategories = category.get_form(
        post_data=request.POST or None, initial_data=initial_data,
        show_translation=show_translation, edit_mode=edit_mode)

    toc_content = []
    for subcategory_config, __ in subcategories:
        toc_content.append((
            subcategory_config.get('keyword'), subcategory_config.get('label'),
            subcategory_config.get('numbering')
        ))

    return render(request, 'form/category.html', {
        'subcategories': subcategories,
        'config': category_config,
        'title': page_title,
        'valid': valid,
        'edit_mode': edit_mode,
        'configuration_name': configuration_code,
        'toc_content': toc_content,
    })


class StepsMixin:
    """
    Get a list with all steps for current questionnaire.
    """
    def get_steps(self):
        # Flattened list with all categories.
        categories = list(chain.from_iterable(
            (section.categories for section in self.questionnaire_configuration.sections)
        ))
        return [category.keyword for category in categories]


class QuestionnaireRetrieveMixin(TemplateResponseMixin):
    """
    Base class for all views that are used to update a questionnaire. At least the url_namespace must be set
    when using this view.

    """
    new_identifier = 'new'
    questionnaire_configuration = None
    url_namespace = None
    configuration_code = None
    template_name = ''

    @property
    def identifier(self):
        return self.kwargs.get('identifier', self.new_identifier)

    @property
    def questionnaire_configuration(self):
        return get_configuration(self.get_configuration_code())

    def get_template_names(self):
        return self.template_name or 'questionnaire/details.html'

    def get_configuration_code(self):
        return self.configuration_code or self.url_namespace

    @property
    def has_object(self):
        return self.identifier != self.new_identifier

    def get_object(self):
        """
        Returns: questionnaires.models.Questionnaire or {}
        """
        if self.has_object:
            obj = query_questionnaire(self.request, self.identifier).first()
            if not obj:
                raise Http404()
            return obj

        return {}

    @property
    def questionnaire_data(self):
        return self.object.data if self.has_object else {}

    @property
    def questionnaire_links(self):
        return self.object.links.all() if self.has_object else []

    def get_detail_url(self, step):
        """
        The detail view of the current object with #top as anchor.

        Returns: string
        """
        if self.view_mode == 'view' or self.has_object:
            url = self.object.get_absolute_url()
        else:
            url = reverse('{}:questionnaire_new'.format(self.url_namespace))

        return '{url}#{step}'.format(url=url, step=step)

    def get_edit_url(self, step):
        """
        The edit view of the current object with #top as anchor.

        Returns: string
        """
        if self.has_object:
            url = reverse('{}:questionnaire_edit'.format(self.url_namespace),
                          args=[self.object.code])
        else:
            url = reverse('{}:questionnaire_new'.format(self.url_namespace))

        return '{url}#{step}'.format(url=url, step=step)

    def get_context_data(self, **kwargs):
        """
        The context data of the view. The required content is based on the previously existing views and the template
        markup.

        Returns: dict
        """
        if 'view' not in kwargs:
            kwargs['view'] = self
        return kwargs


class QuestionnaireEditMixin(LoginRequiredMixin):
    """
    Require login for editing questionnaires.
    """

    def dispatch(self, request, *args, **kwargs):
        request.session[settings.ACCOUNTS_ENFORCE_LOGIN_NAME] = True
        return super().dispatch(request, *args, **kwargs)


class InheritedDataMixin:
    """
    Get the inherited data of linked questionnaires. Used to add read-only data
    of (parent) questionnaires to modules.
    """
    def get_inherited_data(self, original_locale=None):
        """
        Args:
            original_locale: If provided, the data is passed to
                get_questionnaire_data_for_translation_form before it is
                returned.

        Returns:
            dict.
        """
        data = {}
        inherited_data = self.questionnaire_configuration.get_inherited_data()
        for inherited_config, inherited_qgs in inherited_data.items():
            inherited_obj = self.object.links.filter(
                configurations__code=inherited_config).first()

            if inherited_obj is None:
                continue

            additional_qgs = {}
            for inherited_qg, current_qg in inherited_qgs.items():
                additional_qgs[current_qg] = inherited_obj.data.get(
                    inherited_qg, [])

            if original_locale is not None:
                additional_data = get_questionnaire_data_for_translation_form(
                    additional_qgs, get_language(), original_locale)
            else:
                additional_data = additional_qgs

            data.update(additional_data)

        return data


class QuestionnaireSaveMixin(StepsMixin):
    """
    Validate and save data for object. Errors are written to
    """
    category = None
    url_namespace = None

    def dispatch(self, request, *args, **kwargs):
        self.errors = []
        self.form_has_errors = False
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('{}:questionnaire_edit'.format(self.url_namespace),
                       kwargs={'identifier': self.object.code})

    def validate(self, subcategories, original_locale):
        """
        Validation is executed in two steps:

        - Validate given section
        - Validate complete questionnaire, with merged new section

        If either fails, an error is added to request.messages - else the
        object is saved and a redirect to the success url is returned.

        Returns: tuple (is_valid, data)

        """
        data, is_valid = self._validate_formsets(
            subcategories, get_language(), original_locale
        )
        links = get_link_data(self.questionnaire_links)

        # Check if any links were modified.
        link_questiongroups = self.category.get_link_questiongroups()
        if data and link_questiongroups:
            for link_qg in link_questiongroups:
                link_data = data.get(link_qg, [])
                if link_data:
                    try:
                        link_configuration_code = link_qg.rsplit('__', 1)[1]
                    except IndexError:
                        self.errors.append('There was a problem submitting the link')
                        valid = False
                        continue

                # The links initially available
                initial_links = links.get(link_configuration_code, [])
                new_links = []

                for link in link_data:
                    link_id = link.get('link_id')
                    if not link_id:
                        continue

                    try:
                        link_object = Questionnaire.with_status.not_deleted().get(pk=link_id)
                    except Questionnaire.DoesNotExist:
                        self.errors.append('The linked questionnaire with ID {} does not exist'.format(link_id))
                        valid = False
                        continue

                    # Check if the link is already in the session, in which case
                    # there is no need to get the link data again
                    link_found = False
                    for old_link in initial_links:
                        if old_link.get('id') == link_id:
                            link_found = True
                            new_links.extend(old_link)

                    if link_found is False:
                        current_link_data = get_link_data(
                            [link_object],
                            link_configuration_code=link_configuration_code
                        )
                        new_links.extend(current_link_data.get(
                            link_configuration_code))

                links[link_configuration_code] = new_links

        if not is_valid:
            return is_valid, data
        else:
            # Links will be saved only when everything is valid.
            self.links = links
            # Merge validated data to complete questionnaire and validate this again.
            return self.merge_and_validate(data)

    def merge_and_validate(self, data):
        """
        Merge data from current section to questionnaire and validate complete questionnaire data.

        Args:
            data: dict

        Returns:
            tuple: is_valid, data

        Todo: discuss with lukas: what happens if the section data is valid, but the whole questionnaire is invalid?

        """
        if self.has_object:
            self.object.data.update(data)
            data = self.object.data

        questionnaire_data, errors = clean_questionnaire_data(data, self.questionnaire_configuration)
        if errors:
            self.errors.extend(errors)
        return not bool(self.errors), questionnaire_data

    def can_lock_object(self):
        # Try to lock questionnaire, raise an error if it is locked already.
        if not self.has_object:
            return True
        try:
            Questionnaire().lock_questionnaire(self.identifier, self.request.user)
        except QuestionnaireLockedException as e:
            self.errors.append(e)
            return False
        return True

    def save(self, subcategories, original_locale):
        """
        Validate and save the questionnaire.
        """
        is_valid, data = self.validate(subcategories, original_locale)

        if not is_valid or not self.can_lock_object():
            return self.form_invalid()
        else:
            return self.form_valid(data)

    def form_valid(self, data: dict):
        """
        Save the new questionnaire data and create a log for the change.
        """
        try:
            questionnaire = Questionnaire.create_new(
                configuration_code=self.get_configuration_code(),
                data=data,
                user=self.request.user,
                previous_version=self.object if self.has_object else None
            )
            self.object = questionnaire
        except ValidationError as e:
            self.errors.append(e)
            return self.form_invalid()

        self.save_questionnaire_links()
        questionnaire.unlock_questionnaire()
        messages.success(self.request, _('Data successfully saved.'))
        change_questionnaire_data.send(
            sender=settings.NOTIFICATIONS_EDIT_CONTENT,
            questionnaire=questionnaire,
            user=self.request.user
        )
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self):
        """
        Some errors are non-form errors and are displayed with as messages. The context (or better: the templates)
        doesn't display the errors yet.
        """
        for error in self.errors:
            messages.error(self.request, error)
        return self.render_to_response(self.get_context_data(errors=self.errors))

    def _validate_formsets(self, nested_formsets, current_locale, original_locale):
        """
        Helper function to validate a set of nested formsets. Unnests
        the formsets and validates each of them. Returns the cleaned
        data if the formsets are valid.

        Args:
            ``nested_formsets`` (list): A nested list of tuples with
            formsets. Each tuple contains of the configuration [0] and
            the formsets [1]

            ``current_locale`` (str): The current locale.

            ``original_locale`` (str): The original locale in which the
            questionnaire was originally created.

        Returns:
            ``dict``. The cleaned data dictionary if the formsets are
            valid. Else ``None``.

            ``bool``. A boolean indicating whether the formsets are
            valid or not.
        """

        def unnest_formets(nested_formsets):
            """
            Small helper function to unnest nested formsets. Returns them
            all in a flat array.
            """
            ret = []
            for __, f in nested_formsets:
                if isinstance(f, list):
                    ret.extend(unnest_formets(f))
                else:
                    ret.append(f)
            return ret

        data = {}
        is_valid = True
        formsets = unnest_formets(nested_formsets)
        for formset in formsets:
            is_valid = is_valid and formset.is_valid()

            if is_valid is False:
                self.form_has_errors = True
                return {}, False

            for f in formset.forms:
                questiongroup_keyword = f.prefix.split('-')[0]
                cleaned_data = get_questiongroup_data_from_translation_form(
                    f.cleaned_data, current_locale, original_locale
                )
                try:
                    data[questiongroup_keyword].append(cleaned_data)
                except KeyError:
                    data[questiongroup_keyword] = [cleaned_data]

        return data, True

    def get_success_url_next_section(self, identifier, current):
        """
        The 'step' we need is the keyword of the next 'category'. This category is part of the section.

        Args:
            current: string (the current step)
            identifier: string to identify the questionnaire in the url pattern

        Returns:
            url

        """

        # Current or next step may not exist - use the default
        # redirect.
        steps = self.get_steps()
        with contextlib.suppress(ValueError, IndexError):
            current_step = steps.index(current)
            url = reverse('{}:questionnaire_new_step'.format(self.url_namespace), kwargs={
                'identifier': identifier,
                'step': steps[current_step + 1]
            })
            return HttpResponseRedirect(url)

    def save_questionnaire_links(self):
        """
        Save the linked questionnaires to for the current object.
        """
        if not hasattr(self, 'links') or not self.links:
            return

        # Collect the IDs of all (newly) linked questionnaires
        linked_ids = []
        for __, linked_questionnaires in self.links.items():
            linked_ids.extend([x.get('id') for x in linked_questionnaires])

        # Remove all currently linked questionnaires which are not in this list
        for removed in self.object.links.exclude(id__in=linked_ids):
            self.object.remove_link(removed)

        existing_links = self.object.links.all()

        # Add links to all questionnaires in the list
        for linked in linked_ids:
            with contextlib.suppress(Questionnaire.DoesNotExist):
                link = Questionnaire.objects.get(pk=linked)
                if link not in existing_links:
                    self.object.add_link(link)


class QuestionnaireMapView(TemplateResponseMixin, View):
    """
    A generic view to show the map of a questionnaire (in a modal)
    """
    http_method_names = ['get']
    template_name = 'details/modal_map.html'
    url_namespace = None

    def get_object(self):
        questionnaire_object = query_questionnaire(
            self.request, self.kwargs.get('identifier')).first()
        if questionnaire_object is None:
            raise Http404()
        return questionnaire_object

    @xframe_options_exempt
    def get(self, request, *args, **kwargs):
        questionnaire_object = self.get_object()

        configuration = get_configuration(configuration_code=self.url_namespace)
        geometry = configuration.get_questionnaire_geometry(
            questionnaire_object.data)

        context = {
            'geometry': geometry,
        }

        return self.render_to_response(context=context)


class QuestionnaireView(QuestionnaireRetrieveMixin, StepsMixin, InheritedDataMixin, View):

    http_method_names = ['get', 'post']
    view_mode = 'view'

    def get(self, request, *args, **kwargs):
        """
        Display the questionnaire overview.
        """
        self.object = self.get_object()

        questionnaire_data = self.questionnaire_data
        if self.has_object:
            inherited_data = self.get_inherited_data()
            questionnaire_data.update(inherited_data)

        data = get_questionnaire_data_in_single_language(
            questionnaire_data=questionnaire_data, locale=get_language(),
            original_locale=self.object.original_locale if self.object else None
        )

        other_version_status = None
        if self.has_object:
            all_versions = query_questionnaire(request, self.object.code)
            if len(all_versions) > 1:
                other_version_status = all_versions[1].get_status_display()

        roles, permissions = [], []
        can_edit, blocked_by = None, None
        review_config = {}
        if request.user.is_authenticated():
            if self.has_object:
                roles, permissions = self.object.get_roles_permissions(
                    self.request.user)

                # Display a message regarding the state for editing (locked / available)
                can_edit = self.object.can_edit(request.user)
                level, message = self.object.get_blocked_message(request.user)
                blocked_by = message
                messages.add_message(request, level, message)
            else:
                # User is always compiler of new questionnaires.
                role = settings.QUESTIONNAIRE_COMPILER
                roles = [(role, dict(QUESTIONNAIRE_ROLES).get(role))]
                permissions = ['edit_questionnaire']

            review_config = self.get_review_config(
                permissions=permissions, roles=roles,
                blocked_by=blocked_by if not can_edit else False,
                other_version_status=other_version_status
            )

        csrf_token = get_token(
            self.request) if 'edit_questionnaire' in permissions else None

        images = self.questionnaire_configuration.get_image_data(data).get(
            'content', [])

        # TODO: Highlight changes disabled.
        # For the time being, the function to show changes has been
        # disabled. Delete the following line to reenable it.
        edited_questiongroups = []

        complete, total = self.questionnaire_configuration.get_completeness(
            data)
        completeness_percentage = int(round(complete / total * 100))

        sections = self.questionnaire_configuration.get_details(
            data, permissions=permissions,
            edit_step_route='{}:questionnaire_new_step'.format(
                self.url_namespace),
            questionnaire_object=self.object or None,
            csrf_token=csrf_token,
            edited_questiongroups=edited_questiongroups,
            view_mode=self.view_mode,
            links=self.get_links(),
            review_config=review_config,
            user=request.user if request.user.is_authenticated() else None,
            completeness_percentage=completeness_percentage
        )

        modules = {}
        links = {}
        module_form_config = {}
        available_modules = self.questionnaire_configuration.get_modules()
        if self.has_object:
            for link_config, link_list in self.get_links().items():
                if link_config in available_modules:
                    modules[link_config] = link_list
                else:
                    links[link_config] = link_list

            if request.user.is_authenticated() and available_modules:
                module_form_config = {
                    'questionnaire_id': self.object.id,
                    'check_url': reverse(
                        '{}:check_modules'.format(self.url_namespace)),
                    'questionnaire_configuration': self.url_namespace,
                }

        context = {
            'images': images,
            'sections': sections,
            'links': links,
            'modules': modules,
            'module_form_config': module_form_config,
            'questionnaire_identifier': self.identifier,
            'url_namespace': self.url_namespace,
            'permissions': permissions,
            'edited_questiongroups': edited_questiongroups,
            'view_mode': 'edit',
            'is_blocked': not can_edit,
            'toc_content': self.questionnaire_configuration.get_toc_data(),
            'has_content': bool(data),
            'review_config': review_config,
            'questionnaires_in_progress': self.questionnaires_in_progress(),
            'base_template': '{}/base.html'.format(self.url_namespace),
        }
        return self.render_to_response(context=context)

    def post(self, request, *args, **kwargs):
        """
        Handle review actions.
        """
        obj = self.get_object()
        review = handle_review_actions(
            request, obj, self.get_configuration_code()
        )
        if isinstance(review, HttpResponse):
            return review
        return redirect(obj.get_absolute_url())

    def get_object(self):
        if self.identifier == self.new_identifier:
            raise Http404()
        return super().get_object()

    def get_review_config(self, permissions, roles, **kwargs):
        """
        Create a dict with the review_config, this is required for proper display
        of the review panel.

        Args:
            permissions: list
            url: string
            **kwargs:

        Returns: dict

        """
        status = self.object.status if self.has_object else 0
        permissions = permissions or []
        workflow_users = {}
        if 'assign_questionnaire' in permissions:
            if status == settings.QUESTIONNAIRE_DRAFT:
                workflow_users['editors'] = self.object.get_users_by_role(
                    'editor')
            elif status == settings.QUESTIONNAIRE_SUBMITTED:
                workflow_users['reviewers'] = self.object.get_users_by_role(
                    'reviewer')
            elif status == settings.QUESTIONNAIRE_REVIEWED:
                workflow_users['publishers'] = self.object.get_users_by_role(
                    'publisher')

        welcome_info = {}
        if not self.has_object:
            welcome_info = {
                'data_type': self.url_namespace,
                'first_section_url': reverse(
                    '{}:questionnaire_new_step'.format(self.url_namespace),
                    kwargs={
                        'identifier': self.identifier,
                        'step': self.get_steps()[0]
                    })
            }
        url = ''
        if self.has_object:
            if self.view_mode == 'edit':
                url = self.object.get_absolute_url()
            else:
                url = self.object.get_edit_url()

        return {
            'review_status': status,
            'csrf_token_value': get_token(self.request),
            'permissions': permissions,
            'roles': roles,
            'mode': self.view_mode,
            'url': url,
            'is_blocked': bool(kwargs.get('blocked_by', False)),
            'blocked_by': kwargs.get('blocked_by', ''),
            'form_action_url': self.get_detail_url(step=''),
            # flag if this questionnaire has a published version - controlling the first tab.
            'has_release': self.has_release(),
            'other_version_status': kwargs.get('other_version_status'),
            **workflow_users,
            **welcome_info,
        }

    def get_links(self):
        """
        Prepare links as expected by the template.

        Returns: dict
        """
        if not self.has_object:
            return None

        status_filter = get_query_status_filter(self.request)

        linked_questionnaires = self.object.links.filter(
            status_filter, configurations__isnull=False)
        links_by_configuration = collections.defaultdict(list)
        links_by_configuration_codes = collections.defaultdict(list)

        for linked in linked_questionnaires:
            configuration_code = linked.configurations.first().code
            linked_questionnaire_code = linked.code
            if linked_questionnaire_code not in links_by_configuration_codes[
                    configuration_code]:
                links_by_configuration[configuration_code].append(linked)
                links_by_configuration_codes[configuration_code].append(
                    linked_questionnaire_code)

        link_display = {}
        for configuration, links in links_by_configuration.items():
            link_display[configuration] = get_list_values(
                configuration_code=configuration, questionnaire_objects=links,
                with_links=False
            )
        return link_display

    def has_release(self):
        return self.has_object and self.object.has_release

    def questionnaires_in_progress(self):
        """
        Get all questionnaires that given user is currently working on.

        Returns:
            queryset

        """
        if not self.request.user.is_authenticated():
            return []
        return Questionnaire.with_status.not_deleted().filter(
            status=settings.QUESTIONNAIRE_DRAFT,
            questionnairemembership__user=self.request.user,
            questionnairemembership__role__in=[
                settings.QUESTIONNAIRE_COMPILER, settings.QUESTIONNAIRE_EDITOR
            ]
        )

    def get_detail_url(self, step):
        return super().get_detail_url(step='top')


class QuestionnaireEditView(QuestionnaireEditMixin, QuestionnaireView):
    """
    Refactored function based view: generic_questionnaire_new
    """
    http_method_names = ['get']
    view_mode = 'edit'

    @method_decorator(ensure_csrf_cookie)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_object(self):
        return QuestionnaireRetrieveMixin.get_object(self)


class QuestionnaireStepView(QuestionnaireEditMixin, QuestionnaireRetrieveMixin,
                            InheritedDataMixin, QuestionnaireSaveMixin, View):
    """
    A section of the questionnaire.
    """
    edit_mode = 'edit'
    template_name = 'form/category.html'

    def set_attributes(self):
        """
        Shared calls (pseudo setup) for get and post
        """
        self.object = self.get_object()
        self.category = self.questionnaire_configuration.get_category(self.kwargs['step'])
        if not self.category:
            raise Http404()
        self.category_config, self.subcategories = self.get_subcategories()

    def get(self, request, *args, **kwargs):
        """
        Display the form for the selected step,
        """
        self.set_attributes()
        if self.has_object:
            try:
                Questionnaire.lock_questionnaire(
                    self.object.code, self.request.user
                )
            except QuestionnaireLockedException:
                return HttpResponseRedirect(self.object.get_absolute_url())
        return self.render_to_response(context=self.get_context_data())

    def post(self, request, *args, **kwargs):
        """
        Validate and save the data. If valid, a redirect to the .get() view is returned (Post-Redirect-Get)

        Returns: HttpResponse

        """
        self.set_attributes()
        original_locale, show_translation = self.get_locale_info()
        return self.save(self.subcategories, original_locale)

    def get_success_url(self):
        url = super().get_success_url()
        return '{}#{}'.format(url, self.kwargs['step'])

    def form_valid(self, data):
        """
        Handle special case if the user clicks on 'save and go to next section'

        """
        response = super().form_valid(data)

        if self.request.POST.get('goto-next-section', '') == 'true':
            next_step = self.get_success_url_next_section(self.object.code, self.kwargs['step'])
            if next_step:
                return next_step

        return response

    def get_locale_info(self):
        """
        Get the original locale of the current object.

        Returns: tuple (original_locale, show_translation)
        """
        original_locale = None
        if self.has_object:
            original_locale = self.object.original_locale

        show_translation = (original_locale is not None and get_language() != original_locale)
        return original_locale, show_translation

    def get_subcategories(self):
        """
        Returns: tuple (category_config, subcategories)
        """
        original_locale, show_translation = self.get_locale_info()

        initial_data = get_questionnaire_data_for_translation_form(
            self.object.data if self.has_object else {}, get_language(), original_locale
        )
        initial_links = get_link_data(self.questionnaire_links)

        # Add inherited data if available.
        if self.has_object:
            inherited_data = self.get_inherited_data(
                original_locale=original_locale)
            initial_data.update(inherited_data)

        category_config, subcategories = self.category.get_form(
            post_data=self.request.POST or None,
            initial_data=initial_data, show_translation=show_translation,
            edit_mode=self.edit_mode,
            edited_questiongroups=[], initial_links=initial_links,
        )
        return category_config, subcategories

    def get_toc_content(self):
        toc_content = []
        for subcategory_config, __ in self.subcategories:
            toc_content.append((
                subcategory_config.get('keyword'), subcategory_config.get('label'),
                subcategory_config.get('numbering')
            ))
        return toc_content

    def get_context_data(self, **kwargs):
        """
        Provide all info required to display a single step of the form.

        Returns: dict
        """
        ctx = super().get_context_data(**kwargs)

        view_url = ''
        if self.has_object:
            view_url = reverse('{}:questionnaire_view_step'.format(self.url_namespace),
                               args=[self.identifier, self.kwargs['step']])

        # questionnaire is locked one minute before the lock time is over. time
        # is expressed in milliseconds, as required for setInterval
        lock_interval = (settings.QUESTIONNAIRE_LOCK_TIME - 1) * 60 * 1000

        ctx.update({
            'subcategories': self.subcategories,
            'config': self.category_config,
            'content_subcategories_count': len([c for c in self.subcategories if c[1] != []]),
            'title': _('QCAT Form'),
            'overview_url': self.get_edit_url(self.kwargs['step']),
            'valid': not self.form_has_errors,
            'configuration_name': self.category_config.get('configuration', self.url_namespace),
            'edit_mode': self.edit_mode,
            'view_url': view_url,
            'toc_content': self.get_toc_content(),
            'lock_interval': lock_interval
        })
        return ctx


def generic_questionnaire_list_no_config(
        request, user=None, moderation_mode=None):
    """
    A generic view to show a list of Questionnaires. Similar to
    :func:`generic_questionnaire_list` but with the following
    differences:

    * No configuration is used, meaning that questionnaires from all
      configurations are queried.

    * No (attribute) filter configuration is created and provided.

    * Special status filters are used: In moderation mode
      (``moderation=True``), only pending versions are returned. Users
      see their own versions (all statuses). Else the default status
      filter is used.

    * Always return the template values as a dictionary.

    Args:
        ``request`` (django.http.HttpRequest): The request object.

    Kwargs:
        ``user`` (``accounts.models.User``): If provided, show only
        Questionnaires in which the user is a member of.

        ``moderation`` (bool): If ``True``, always only show ``pending``
         Questionnaires if the current user has moderation
        permission.

    Returns:
        ``dict``. A dictionary with template values to be used in a list
        template.
    """
    limit = get_limit_parameter(request)
    page = get_page_parameter(request)
    is_current_user = request.user is not None and request.user == user

    # Determine the status filter
    if moderation_mode is not None:
        # Moderators always have a special moderation status filter
        status_filter = get_query_status_filter(
            request, moderation_mode=moderation_mode)
    elif is_current_user is True:
        # The current user has no status filter (sees all statuses)
        status_filter = Q()
    else:
        # Else use the default status filter (will be applied in
        # :func:`query_questionnaires`)
        status_filter = None

    questionnaire_objects = query_questionnaires(
        request, 'all', only_current=False,
        limit=None, user=user, status_filter=status_filter)

    questionnaires, paginator = get_paginator(
        questionnaire_objects, page, limit)

    status_filter = get_query_status_filter(request)
    list_values = get_list_values(
        configuration_code='wocat',
        questionnaire_objects=questionnaires, status_filter=status_filter)

    template_values = {
        'list_values': list_values,
        'is_current_user': is_current_user,
        'list_user': user,
        'is_moderation': moderation_mode,
    }

    # Add the pagination parameters
    pagination_params = get_pagination_parameters(
        request, paginator, questionnaires)
    template_values.update(pagination_params)

    return template_values


def generic_questionnaire_list(
        request, configuration_code, template=None, filter_url='', limit=None,
        only_current=False):
    """
    A generic view to show a list of Questionnaires.

    Args:
        ``request`` (django.http.HttpRequest): The request object.

        ``configuration_code`` (str): The code of the questionnaire
        configuration.

    Kwargs:
        ``template`` (str): The path of the template to be rendered for
        the list.

        ``filter_url`` (str): The URL of the view used to render the
        list partially. Used by AJAX requests to update the list.

        ``limit`` (int): The limit of results the list will return.

        ``only_current`` (bool): A boolean indicating whether to include
        only questionnaires from the current configuration. Passed to
        :func:`questionnaire.utils.query_questionnaires`

    Returns:
        ``HttpResponse``. A rendered Http Response.
    """
    configuration_codes = get_configuration_index_filter(configuration_code)
    configurations = [get_configuration(code) for code in configuration_codes]


    # Get the filters and prepare them to be passed to the search.
    active_filters = get_active_filters(configurations, request.GET)
    query_string = ''
    filter_params = []
    for active_filter in active_filters:
        filter_type = active_filter.get('type')
        if filter_type in ['_search']:
            query_string = active_filter.get('value', '')
        elif filter_type in [
                'checkbox', 'image_checkbox', '_date', '_flag', 'select_type',
                'select_model', 'radio', 'bool']:
            filter_params.append(
                (active_filter.get('questiongroup'),
                 active_filter.get('key'), active_filter.get('value'), None,
                 active_filter.get('type')))
        else:
            raise NotImplementedError(
                'Type "{}" is not valid for filters'.format(filter_type))

    if limit is None:
        limit = get_limit_parameter(request)
    page = get_page_parameter(request)
    offset = page * limit - limit

    search_configuration_codes = get_configuration_index_filter(
        configuration_code, only_current=only_current,
        query_param_filter=tuple(request.GET.getlist('type')))

    search = advanced_search(
        filter_params=filter_params, query_string=query_string,
        configuration_codes=search_configuration_codes, limit=limit,
        offset=offset)

    es_hits = search.get('hits', {})
    es_pagination = ESPagination(
        es_hits.get('hits', []), es_hits.get('total', 0))

    questionnaires, paginator = get_paginator(es_pagination, page, limit)

    list_values = get_list_values(
        configuration_code=configuration_code, es_hits=questionnaires)

    # Add the configuration of the filter
    filter_configuration = get_filter_configuration(configuration_code)

    template_values = {
        'list_values': list_values,
        'filter_configuration': filter_configuration,
        'active_filters': active_filters,
        'filter_url': filter_url,
    }

    # Add the pagination parameters
    pagination_params = get_pagination_parameters(
        request, paginator, questionnaires)
    template_values.update(pagination_params)

    if template is None:
        return template_values

    return render(request, template, template_values)


@login_required
@require_POST
@force_login_check
def generic_file_upload(request):
    """
    A view to handle file uploads. Can only be called with POST requests
    and returns a JSON.

    Args:
        request (django.http.HttpRequest): The request object. Only
        request method ``POST`` is accepted and the following parameters
        are valid:

            ``request.FILES`` (mandatory): The uploaded file.

    Returns:
        ``JsonResponse``. A JSON containing the following entries::

          # Successful requests
          {
            "success": true,
            "uid": "UID",          # The UID of the generated file
            "url": "URL"           # The URL of the uploaded file
            "interchange": "XYZ"   # The interchange value with all the
                                   # thumbnails.
          }

          # Error requests (status_code: 400)
          {
            "success": false,
            "msg": "ERROR MESSAGE"
          }
    """
    ret = {
        'success': False,
    }

    files = request.FILES.getlist('file')
    if len(files) != 1:
        ret['msg'] = _('No or multiple files provided.')
        return JsonResponse(ret, status=400)
    file = files[0]

    try:
        file_object = File.handle_upload(file)
    except Exception as e:
        ret['msg'] = str(e)
        return JsonResponse(ret, status=400)

    file_data = File.get_data(file_object=file_object)
    ret = {
        'success': True,
        'uid': file_data.get('uid'),
        'interchange': file_data.get('interchange'),
        'url': file_data.get('url'),
    }
    return JsonResponse(ret)


def generic_file_serve(request, action, uid):
    """
    A view to handle display or download of uploaded files. This
    function should only be used if you don't know the name of the
    thumbnail on the client side as this view has to read the file
    before serving it. On server side, if you want the URL for a
    thumbnail, use the function
    :func:`questionnaire.upload.get_url_by_identifier`.

    Args:
        request (django.http.HttpRequest): The request object.

        action (str): The action to perform with the file. Available
        options are ``display``, ``download`` and ``interchange``.

        uid (str): The UUID of the file object.

    GET Parameters:
        ``format`` (str): The name of the thumbnail format for images.

    Returns:
        ``HttpResponse``. A Http Response with the file if found, 404 if
        not found. If the ``action=interchange`` is set, a string with
        the interchange data is returned.
    """
    if action not in ['display', 'download', 'interchange']:
        raise Http404()

    file_object = get_object_or_404(File, uuid=uid)
    file_data = File.get_data(file_object=file_object)

    if action == 'interchange':
        return HttpResponse(file_data.get('interchange'))

    thumbnail = request.GET.get('format')
    try:
        file, filename = retrieve_file(file_object, thumbnail=thumbnail)
    except:
        raise Http404()

    content_type = file_data.get('content_type')
    if thumbnail is not None:
        content_type = UPLOAD_THUMBNAIL_CONTENT_TYPE

    response = HttpResponse(file, content_type=content_type)
    if action == 'download':
        response['Content-Disposition'] = 'attachment; filename={}'.format(
            filename)
        response['Content-Length'] = file_data.get('size')

    return response


class QuestionnaireModuleMixin(LoginRequiredMixin):
    """
    Get available modules and check for already existing modules.
    """
    request = None
    questionnaire_object = None
    questionnaire_configuration = None
    available_modules = []
    existing_modules = []

    def get_questionnaire_object(self):
        try:
            # The form variable is named similar to the link-creation
            # action in the questionnaire form.
            questionnaire_id = int(self.request.POST.get('link_id'))
        except TypeError:
            return None
        try:
            return Questionnaire.objects.get(pk=questionnaire_id)
        except Questionnaire.DoesNotExist:
            return None

    def get_questionnaire_configuration(self):
        configuration_code = self.request.POST.get('configuration')
        return get_configuration(configuration_code=configuration_code)

    def get_available_modules(self):
        return self.questionnaire_configuration.get_modules()

    def get_existing_modules(self):
        existing_modules = []
        for link in self.questionnaire_object.links.all():
            link_configuration = link.configurations.first()
            if link_configuration.code in self.available_modules:
                existing_modules.append(link_configuration.code)
        return existing_modules


class QuestionnaireAddModule(QuestionnaireModuleMixin, View):

    http_method_names = ['post']
    url_namespace = None

    def post(self, request, *args, **kwargs):

        error_redirect = '{}:add_module'.format(self.url_namespace)

        self.questionnaire_object = self.get_questionnaire_object()
        if self.questionnaire_object is None:
            messages.error(
                self.request,
                'Module cannot be added - Questionnaire not found.')
            return redirect(error_redirect)

        self.questionnaire_configuration = self.get_questionnaire_configuration()
        self.available_modules = self.get_available_modules()
        self.existing_modules = self.get_existing_modules()

        module_code = request.POST.get('module')
        if module_code not in self.available_modules:
            messages.error(
                self.request, 'Module is not valid for this questionnaire.')
            return redirect(error_redirect)

        if module_code in self.existing_modules:
            messages.error(
                self.request, 'Module exists already for this questionnaire.')
            return redirect(error_redirect)

        # Create a new questionnaire
        module_data = {}
        new_module = Questionnaire.create_new(
            module_code, module_data, request.user)
        new_module.add_link(self.questionnaire_object)

        success_redirect = reverse(
            '{}:questionnaire_edit'.format(module_code),
            kwargs={'identifier': new_module.code})
        return redirect(success_redirect)


class QuestionnaireCheckModulesView(
    QuestionnaireModuleMixin, TemplateResponseMixin, View):

    http_method_names = ['post']
    template_name = 'questionnaire/partial/select_modules.html'

    def post(self, request, *args, **kwargs):

        self.questionnaire_object = self.get_questionnaire_object()
        if self.questionnaire_object is None:
            return self.render_to_response(
                context={
                    'module_error': 'No modules found for this questionnaire.'})

        self.questionnaire_configuration = self.get_questionnaire_configuration()
        self.available_modules = self.get_available_modules()
        self.existing_modules = self.get_existing_modules()

        context = {
            'modules': [(module, module in self.existing_modules) for module
                        in self.available_modules],
        }

        return self.render_to_response(context=context)


class QuestionnaireLockView(LoginRequiredMixin, View):
    """
    Lock the questionnaire for the current user.
    """

    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        Lock.objects.create(
            questionnaire_code=self.kwargs['identifier'],
            user=self.request.user
        )
        return HttpResponse(status=200)
