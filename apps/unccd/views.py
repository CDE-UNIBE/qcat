from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.utils.translation import ugettext as _

from accounts.decorators import force_login_check
from questionnaire.views import (
    generic_questionnaire_list,
    generic_questionnaire_view_step,
)


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
