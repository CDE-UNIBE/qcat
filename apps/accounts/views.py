from django.contrib import messages
from django.contrib.auth import (
    logout as django_logout,
    login as django_login,
)
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.http import Http404
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, resolve_url
from django.utils.decorators import method_decorator
from django.utils.http import is_safe_url
from django.utils.timezone import now
from django.utils.translation import ugettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_POST
from django.views.generic import DetailView
from django.views.generic import FormView

from braces.views import LoginRequiredMixin
from configuration.configuration import QuestionnaireConfiguration
from django.views.generic import ListView
from questionnaire.models import STATUSES
from questionnaire.utils import query_questionnaires, get_list_values
from .client import typo3_client
from .conf import settings
from .forms import WocatAuthenticationForm
from .models import User


class LoginView(FormView):
    """
    This view handles the login form and authenticates users.
    """
    form_class = WocatAuthenticationForm
    template_name = 'login.html'
    success_url = settings.ACCOUNTS_LOGIN_SUCCESS_URL

    @method_decorator(never_cache)
    @method_decorator(sensitive_post_parameters('password'))
    def dispatch(self, *args, **kwargs):
        if hasattr(self.request, 'user') and \
                self.request.user.is_authenticated():
            return redirect(self.get_success_url())
        return super(LoginView, self).dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        # Add next_url to context to show notification in login form.
        context = super().get_context_data(**kwargs)
        context.update({
            'next_url': self.request.GET.get('next'),
        })
        return context

    def form_valid(self, form):
        # Put the user on the request, and add a welcome message.
        user = form.get_user()
        django_login(self.request, user)
        messages.info(self.request, _('Welcome {}').format(user.firstname))

        # Get the response, add a cookie and return it.
        response = HttpResponseRedirect(self.get_success_url())
        # We really should set a signed cookie - but the same cookie is used
        # on wocat.net.
        response.set_cookie(
            key=settings.AUTH_COOKIE_NAME,
            value=user.typo3_session_id
        )
        response.set_signed_cookie(
            key=settings.ACCOUNTS_ENFORCE_LOGIN_COOKIE_NAME,
            value=now(),
            salt=settings.ACCOUNTS_ENFORCE_LOGIN_SALT
        )
        return response

    def get_success_url(self):
        # Explicitly passed ?next= url takes precedence.
        redirect_to = self.request.GET.get('next') or reverse(self.success_url)
        # Redirect UNCCD focal points to the list filtered with Questionnaires
        # from their country. Only if no "next" is set.
        if self.request.GET.get('next') is None:
            unccd_countries = self.request.user.get_unccd_countries()
            if unccd_countries:
                country_keyword = unccd_countries[0].keyword
                redirect_to = '{}?{}'.format(
                    reverse('wocat:questionnaire_list'),
                    QuestionnaireConfiguration.get_country_filter(
                        country_keyword)
                )
        # Prevent redirecting to other/invalid hosts - i.e. prevent xsrf
        if not is_safe_url(url=redirect_to, host=self.request.get_host()):
            redirect_to = resolve_url(settings.LOGIN_REDIRECT_URL)
        return redirect_to


class ProfileView(LoginRequiredMixin, DetailView):
    """
    Display the users questionnaires (and in future: notifications).

    Questionnaires are loaded from the template (asynchronously).
    """
    template_name = 'questionnaires.html'

    def get_object(self, queryset=None):
        return self.request.user

    def get_questionnaires(self):
        """
        Fetch questionnaires for current user.
        """
        return query_questionnaires(
            request=self.request, configuration_code='all', only_current=False,
            limit=None
        )

    def get_status_list(self) -> list:
        """
        Fetch all (distinct) statuses that at least one questionnaire of the
        current user has.
        """
        questionnaires = self.get_questionnaires()
        statuses = questionnaires.order_by(
            'status'
        ).distinct(
            'status'
        ).values_list(
            'status', flat=True
        )
        status_choices = dict(STATUSES)  # cast to dict for easier access.
        return {status: _(status_choices[status]) for status in statuses}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['statuses'] = self.get_status_list()
        return context


class UserDetailView(DetailView):
    """
    Show some information about the requested user:
    - information (name)
    - focal point countries
    - public questionnaires

    """
    context_object_name = 'detail_user'
    model = User
    template_name = 'details.html'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset=queryset)
        # Update the user details
        user_info = typo3_client.get_user_information(obj.id)
        typo3_client.update_user(obj, user_info)
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        unccd_countries_list = []
        unccd_countries = self.object.get_unccd_countries()
        for country in unccd_countries:
            unccd_countries_list.append((
                country,
                '{}?{}'.format(
                    reverse('wocat:questionnaire_list'),
                    QuestionnaireConfiguration.get_country_filter(
                        country.keyword))
            ))
        context['unccd_countries'] = unccd_countries_list
        return context


class QuestionnaireListMixin(ListView):
    """
    Mixin for paginated questionnaires.
    """
    template_name = 'questionnaire_status_list.html'
    paginate_by = 3

    @property
    def status(self):
        raise NotImplementedError

    def get_filter_user(self):
        raise NotImplementedError

    def get_queryset(self):
        """
        Fetch all questionnaires from the current user with the requested
        status.
        """
        return query_questionnaires(
            request=self.request, configuration_code='all', only_current=False,
            limit=None, **self.get_filter_user()
        ).filter(
            status=self.status
        )

    def get_context_data(self, **kwargs) -> dict:
        """
        Provide context data in qcats default way. Pagination happens in the
        parents get_context_data method.
        """
        context = super().get_context_data(**kwargs)
        context['list_values'] = get_list_values(
            questionnaire_objects=context['object_list'], status_filter=Q()
        )
        return context


class PublicQuestionnaireListView(QuestionnaireListMixin):
    """
    Get public questionnaires the user defined in the url.
    """
    @property
    def status(self):
        return settings.QUESTIONNAIRE_PUBLIC

    def get_filter_user(self):
        user = get_object_or_404(User, id=self.kwargs['user_id'])
        return {'user': user}


class QuestionnaireStatusListView(LoginRequiredMixin, QuestionnaireListMixin):
    """
    Display all questionnaires for the requested status. Results are paginated,
    the paginator shows a specified (paginator_quicklink_range) number of pages
    before and after the current page.
    """

    @property
    def status(self):
        """
        Validate status from request.
        """
        try:
            status = int(self.request.GET.get('status'))
        except (TypeError, ValueError):
            raise Http404()

        if status not in dict(STATUSES).keys():
            raise Http404()

        return status

    def get_filter_user(self):
        """
        If no user is set, questionnaires are fetched according to permissions.
        This is the specified behaviour for all statuses (except 'public'), as
        questionnaires that require some kind of action should be listed.

        For published questionnaires, only the questionnaires that the user has
        worked on must be shown - so the user, not the permissions (roles) are
        important.
        """
        return {'user': self.request.user if self.status is settings.QUESTIONNAIRE_PUBLIC else None}  # noqa


def logout(request):
    """
    Log the user out. The actual logout is handled by the authentication
    backend as specified in the settings (``settings.AUTH_LOGIN_FORM``).

    Args:
        ``request`` (django.http.HttpRequest): The request object.

    Returns:
        ``HttpResponse``. A rendered Http Response.
    """
    url = reverse('home')

    django_logout(request)

    ses_id = request.COOKIES.get(settings.AUTH_COOKIE_NAME)
    if ses_id is not None:
        response = HttpResponseRedirect(
            typo3_client.get_logout_url(request.build_absolute_uri(url))
        )
        # The cookie is not always removed on wocat.net
        response.delete_cookie(settings.AUTH_COOKIE_NAME)
    else:
        response = HttpResponseRedirect(url)

    response.delete_cookie(settings.ACCOUNTS_ENFORCE_LOGIN_COOKIE_NAME)
    return response


def user_search(request):
    """
    JSON view to search for users. The search is handled by the
    authentication backend as specified in the settings
    (``settings.AUTH_LOGIN_FORM``).

    Args:
        ``request`` (django.http.HttpRequest): The request object with
        optional GET parameter ``name``.

    Returns:
        ``JsonResponse``. A rendered JSON response.
    """
    search = typo3_client.search_users(name=request.GET.get('name', ''))
    if not search:
        search = {
            'success': False,
            'message': 'Error: The user database cannot be queried right now.'
        }

    return JsonResponse(search)


@require_POST
@login_required
def user_update(request):
    """
    JSON view to create or update a user. The user is queried through
    the authentication backend as specified in the settings
    (``settings.AUTH_LOGIN_FORM``).

    Args:
        ``request`` (django.http.HttpRequest): The request object with
        POST parameter ``uid`` (the user ID).

    Returns:
        ``JsonResponse``. A rendered JSON response.
    """
    ret = {
        'success': False,
    }

    user_uid = request.POST.get('uid')
    if user_uid is None:
        ret['message'] = 'No user ID (uid) provided.'
        return JsonResponse(ret)

    # Try to find the user in the authentication DB
    user_info = typo3_client.get_user_information(user_uid)
    if not user_info:
        ret['message'] = 'No user with ID {} found in the authentication '
        'database.'.format(user_uid)
        return JsonResponse(ret)

    # Update (or insert) the user details in the local database
    user, created = User.objects.get_or_create(pk=user_uid)
    typo3_client.update_user(user, user_info)

    ret = {
        'name': user.get_display_name(),
        'success': True,
    }
    return JsonResponse(ret)
