from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.utils.translation import ugettext as _

from accounts.decorators import force_login_check
from questionnaire.views import generic_questionnaire_list, \
    generic_questionnaire_details, generic_questionnaire_view_step


@login_required
@force_login_check
def questionnaire_view_step(request, identifier, step):
    """
    View rendering the form of a single step of a new Watershed
    questionnaire in read-only mode.
    """
    return generic_questionnaire_view_step(
        request, identifier, step, 'watershed',
        page_title=_('Watershed'))


def questionnaire_details(request, identifier):
    """
    View to show the details of an existing Watershed questionnaire.

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
        request, identifier, 'watershed', 'watershed')


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
    list_values = generic_questionnaire_list(
        request, 'watershed', template=None)

    list_ = render_to_string('watershed/questionnaire/partial/list.html', {
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
    View to show a list with Watershed questionnaires.

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
        request, 'watershed',
        template='watershed/questionnaire/list.html',
        filter_url=reverse('watershed:questionnaire_list_partial'))