from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.utils.translation import ugettext as _

from accounts.decorators import force_login_check
from questionnaire.views import (
    generic_questionnaire_details,
    generic_questionnaire_list,
    generic_questionnaire_new_step,
    generic_questionnaire_new,
    generic_questionnaire_view_step,
)


def home(request):
    list_template_values = generic_questionnaire_list(
        request, 'unccd', template=None, only_current=True, limit=3,
        db_query=True)

    return render(request, 'unccd/home.html', {
        'list_values': list_template_values.get('list_values', []),
        'filter_configuration': list_template_values.get(
            'filter_configuration', {}),
    })


@login_required
@force_login_check
def unccd_data_import(request):
    """
    Call the script for the UNCCD import. This assumes there is a module
    "unccd.data_import" with a function "data_import".

    Redirects to the administration interface to display a success or
    error message.
    """
    if request.user.is_superuser is not True:
        raise PermissionDenied()

    redirect_route = 'search:admin'

    try:
        from .data_import import data_import
    except ImportError as e:
        messages.error(
            request, 'No valid import function found. Make sure there is a '
            'function "data_import" in module "unccd.data_import". The error '
            'message was: {}'.format(e))
        return redirect(redirect_route)

    success, objects = data_import()

    if success is True:
        messages.success(
            request, 'The data was parsed correctly. {} questionnaires were '
            'inserted.'.format(len(objects)))
    else:
        messages.error(
            request, 'The following error(s) occured: {}'.format(objects))

    return redirect(redirect_route)


@login_required
@force_login_check
def questionnaire_view_step(request, identifier, step):
    """
    View rendering the form of a single step of a new UNCCD
    questionnaire in read-only mode.
    """
    return generic_questionnaire_view_step(
        request, identifier, step, 'unccd',
        page_title=_('UNCCD'))


@login_required
@force_login_check
def questionnaire_new_step(request, identifier, step):
    """
    View to show the form of a single step of a new UNCCD questionnaire.
    Also handles the form submit of the step along with its validation
    and redirect.

    .. seealso::
        The actual rendering of the form and the form validation is
        handled by the generic questionnaire function
        :func:`questionnaire.views.questionnaire_new_step`.

    Args:
        ``request`` (django.http.HttpRequest): The request object.

        ``identifier`` (str): The identifier of the Questionnaire
        object.

        ``step`` (str): The code of the questionnaire category.

    Returns:
        ``HttpResponse``. A rendered Http Response.
    """
    return generic_questionnaire_new_step(
        request, step, 'unccd', 'unccd', page_title=_('UNCCD Form'),
        identifier=identifier)


@login_required
@force_login_check
def questionnaire_new(request, identifier=None):
    """
    View to show the overview of a new or edited UNCCD questionnaire.
    Also handles the form submit of the entire questionnaire.

    .. seealso::
        The actual rendering of the form and the form validation is
        handled by the generic questionnaire function
        :func:`questionnaire.views.questionnaire_new`.

    Args:
        ``request`` (django.http.HttpRequest): The request object.

    Kwargs:
        ``identifier`` (str): The identifier of the Questionnaire
        object.

    Returns:
        ``HttpResponse``. A rendered Http Response.
    """
    return generic_questionnaire_new(
        request, 'unccd', 'unccd/questionnaire/details.html', 'unccd',
        identifier=identifier)


def questionnaire_details(request, identifier):
    """
    View to show the details of an existing UNCCD questionnaire.

    .. seealso::
        The actual rendering of the details is handled by the generic
        questionnaire function
        :func:`questionnaire.views.questionnaire_details`

    Args:
        ``request`` (django.http.HttpResponse): The request object.

        ``identifier`` (str): The identifier of the Questionnaire
        object.

    Returns:
        ``HttpResponse``. A rendered Http Response.
    """
    return generic_questionnaire_details(
        request, identifier, 'unccd', 'unccd',
        'unccd/questionnaire/details.html')


def questionnaire_list_partial(request):
    """
    View to render the questionnaire list only partially. Returns a JSON
    response with parts of the template. To be used when uploading the
    list through AJAX requests.

    Args:
        ``request`` (django.http.HttpResponse): The request object.

    Returns:
        ``JsonResponse``. A JSON response with the following entries:

        - ``success`` (bool): A boolean indicating whether query was
          performed successfully or not.

        - ``list`` (string): The rendered list template.

        - ``active_filters`` (string): The rendered active filters
          template.
    """
    list_values = generic_questionnaire_list(request, 'unccd', template=None)

    list_ = render_to_string('unccd/questionnaire/partial/list.html', {
        'list_values': list_values['list_values']})
    active_filters = render_to_string('active_filters.html', {
        'active_filters': list_values['active_filters']})
    pagination = render_to_string('pagination.html', list_values)

    ret = {
        'success': True,
        'list': list_,
        'active_filters': active_filters,
        'pagination': pagination,
        'count': list_values['count'],
    }

    return JsonResponse(ret)


def questionnaire_list(request):
    """
    View to show a list with UNCCD questionnaires.

    .. seealso::
        The actual rendering of the list is handled by the generic
        questionnaire function
        :func:`questionnaire.views.questionnaire_list`

    Args:
        ``request`` (django.http.HttpResponse): The request object.

    Returns:
        ``HttpResponse``. A rendered Http Response.
    """
    return generic_questionnaire_list(
        request, 'unccd', template='unccd/questionnaire/list.html',
        filter_url=reverse('unccd:questionnaire_list_partial'))
