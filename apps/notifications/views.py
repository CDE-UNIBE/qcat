import contextlib
import logging

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.core import signing
from django.core.urlresolvers import reverse_lazy
from django.db import IntegrityError
from django.http import Http404
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from django.views.generic import ListView, TemplateView, View

from braces.views import LoginRequiredMixin
from django.views.generic import UpdateView

from accounts.models import User
from questionnaire.models import Questionnaire
from questionnaire.utils import query_questionnaire
from questionnaire.view_utils import get_pagination_parameters

from .forms import MailPreferencesUpdateForm
from .utils import InformationLog
from .models import Log, ReadLog, MailPreferences

logger = logging.getLogger(__name__)


class LogListTemplateView(LoginRequiredMixin, TemplateView):
    template_name = 'notifications/log_list.html'


class LogListView(LoginRequiredMixin, ListView):
    """
    Display logs for the current user.

    This view accepts following parameters as get-querystrings:
    - page (default django pagination)
    - is_teaser: smaller pagination size
    - is_pending: only logs that are 'to do' for the user

    """
    template_name = 'notifications/partial/list.html'

    def add_user_aware_data(self, logs):
        """
        Provide all info required for the template, so as little logic as
        possible is required within the template.
        """
        # All logs with the status 'read' for the logs on display.
        readlog_list = Log.actions.read_id_list(
            user=self.request.user,
            log_id__in=list(logs.values_list('id', flat=True))
        )

        # A list with all logs that are pending for the user
        pending_questionnaires = Log.actions.user_pending_list(
            user=self.request.user
        ).values_list(
            'id', flat=True
        )

        for log in logs:
            is_read = log.id in readlog_list
            # if a notification is read, it is assumed that it is resolved.
            is_todo = not is_read and log.id in pending_questionnaires
            next_status_text = settings.NOTIFICATIONS_QUESTIONNAIRE_NEXT_STATUS_TEXT.get(log.questionnaire.status) if is_todo else False
            yield {
                'id': log.id,
                'created': log.created,
                'subject': log.subject,
                'text': log.get_html(user=self.request.user),
                'action_icon': log.action_icon(),
                'is_read': is_read,
                'is_todo': is_todo,
                'edit_url': log.questionnaire.get_edit_url() if is_todo else '',
                'next_status_text': next_status_text
            }

    @property
    def queryset_method(self):
        """
        Get the proper method name according to the GET request.
        """
        return 'user_pending_list' if 'is_pending' in self.request.GET.keys() else 'user_log_list'

    def get_paginate_by(self, queryset) -> int:
        """
        Return the setting variable according to the GET querystring.
        """
        return getattr(settings, 'NOTIFICATIONS_{}_PAGINATE_BY'.format(
            'TEASER' if 'is_teaser' in self.request.GET.keys() else 'LIST'
        ))

    @cached_property
    def requested_questionnaire(self):
        request_questionnaire = self.request.GET.get('questionnaire')
        has_permissions = Log.actions.has_permissions_for_questionnaire(
            user=self.request.user, questionnaire_code=request_questionnaire
        )
        if request_questionnaire and has_permissions:
            return request_questionnaire
        return None

    def get_statuses(self):
        with contextlib.suppress(ValueError):
            query_status = self.request.GET.get('statuses', '').split(',')
            statuses = [int(status) for status in query_status]
            if all([status in dict(settings.NOTIFICATIONS_ACTIONS).keys() for status in statuses]):
                return statuses
        return []

    def get_queryset(self):
        """
        Fetch notifications for the current user. Use the method as defined by
        the instance variable. Filter according to questionnaire if requested.
        """
        qs = getattr(Log.actions, self.queryset_method)(user=self.request.user)

        # apply filter for actions ('status' on the frontend)
        statuses = self.get_statuses()
        if statuses:
            qs = qs.filter(action__in=statuses)

        # apply filter for the questionnaire
        if self.requested_questionnaire:
            qs = qs.filter(questionnaire__code=self.requested_questionnaire)

        # apply filter for read/unread notifications
        if 'is_unread' in self.request.GET.keys():
            qs = qs.only_unread_logs(user=self.request.user)

        return qs

    def get_context_data(self, **kwargs):
        """
        Enrich the paginated queryset with values as required by the template.
        Provide the 'path' with the same querystring as provided, plus 'page='.
        """
        context = super().get_context_data(**kwargs)
        pagination_range = get_pagination_parameters(
            request=self.request,
            paginator=context['paginator'],
            paginated=context['page_obj']
        )
        context['logs'] = self.add_user_aware_data(context['object_list'])
        context['statuses'] = dict(settings.NOTIFICATIONS_ACTIONS)
        context.update(pagination_range)
        return context


class ReadLogUpdateView(LoginRequiredMixin, View):
    """
    Update the 'is_read' flag for a log.
    """
    http_method_names = ['post']

    def validate_data(self, **kwargs) -> bool:
        """
        Validate required keys and user from the request.
        """
        # lambda is a workaround to access the 'kwargs.keys()' scope.
        if not all((lambda keys=kwargs.keys():
                    [key in keys for key in ['checked', 'log', 'user']])()):
            return False
        try:
            user_id = int(kwargs['user'])
        except ValueError:
            return False
        if user_id != self.request.user.id:
            return False
        return True

    def post(self, request, *args, **kwargs):
        """
        Validate post data and create/update the readlog.
        """
        data = request.POST.dict()
        is_valid = self.validate_data(**data)
        if is_valid:
            ReadLog.objects.update_or_create(
                user_id=data['user'], log_id=data['log'],
                defaults={
                    'is_read': True if data['checked'] == 'true' else False}
            )
            return HttpResponse(status=200)
        else:
            logging.error('Invalid attempt to update a ReadLog '
                          '(data: {})'.format(data))
            raise Http404()


class LogCountView(LoginRequiredMixin, View):
    """
    Get the current number of 'pending' notifications for the current user.
    Used to display the indicator with
    number next to the username in the menu.
    """
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        return HttpResponse(
            content=Log.actions.only_unread_logs(
                user=self.request.user
            ).user_log_count(
                user=self.request.user
            )
        )


class LogQuestionnairesListView(LoginRequiredMixin, View):
    """
    Return all questionnaires that have a log for a user. Used to build the
    select menu in the 'questionnaire' filter
    """
    http_method_names = ['get']

    def get_questionnaire_logs(self, user: User) -> list:
        """
        Get all distinct questionnaires that the user has logs for.
        """
        return Log.actions.user_log_list(
            user=user
        ).values_list(
            'questionnaire__code', flat=True
        ).order_by(
            'questionnaire_id'
        ).distinct(
            'questionnaire_id'
        )

    def questionnaire_sort(self, obj):
        """
        Helper for sorting.
        """
        name, code = obj.split('_')
        if code.isdigit():
            code = int(code)
        return name, code

    def get(self, request, *args, **kwargs):
        questionnaires = sorted(
            set(self.get_questionnaire_logs(user=request.user)),
            key=self.questionnaire_sort
        )
        return JsonResponse({'questionnaires': questionnaires})


class LogInformationUpdateCreateView(LoginRequiredMixin, View):
    """
    Create a log indicating that an editor has finished working on a
    questionnaire.
    This could be extended to accept multiple receivers.
    """
    http_method_names = ['post']
    status = 200

    def get_compiler(self, questionnaire: Questionnaire) -> User:
        try:
            return questionnaire.questionnairemembership_set.get(
                role='compiler'
            ).user
        except (IntegrityError, ObjectDoesNotExist):
            self.status = 400

    def get_questionnaire(self, identifier: str) -> Questionnaire:
        questionnaire = query_questionnaire(
            request=self.request, identifier=identifier
        )
        if not questionnaire.exists():
            raise Http404()
        return questionnaire.first()

    def post(self, request, *args, **kwargs):
        questionnaire = self.get_questionnaire(request.POST['identifier'])
        compiler = self.get_compiler(questionnaire)
        InformationLog(
            action=settings.NOTIFICATIONS_FINISH_EDITING,
            sender=self.request.user,
            questionnaire=questionnaire,
            receiver=compiler
        ).create(
            info=request.POST['message']
        )

        return HttpResponse(
            status=self.status,
            content=_('{compiler} was informed about your progress.'.format(
                compiler=compiler.get_display_name())
            )
        )


class LogAllReadView(LoginRequiredMixin, View):
    """
    Set all logs as read for given user.
    """

    def delete_all_read_logs(self):
        ReadLog.objects.filter(
            user=self.request.user, is_read=True
        ).update(
            is_deleted=True
        )

    def post(self, request, *args, **kwargs):
        if self.request.GET.get('delete', '') == 'true':
            self.delete_all_read_logs()
        else:
            Log.actions.mark_all_read(user=request.user)
        return HttpResponse(status=200)


class LogSubscriptionPreferencesMixin(UpdateView):
    """
    Display and update the users preferences for receiving emails of
    notifications.
    """
    model = MailPreferences
    form_class = MailPreferencesUpdateForm
    template_name = 'notifications/preferences.html'
    success_url = reverse_lazy('notification_preferences')

    def get_object(self, queryset=None):
        return get_object_or_404(self.model, user=self.request.user)

    def get_initial(self):
        initial = super().get_initial()
        initial['wanted_actions'] = self.object.wanted_actions.split(',')
        return initial

    def form_valid(self, form):
        response = super().form_valid(form)
        if 'language' in form.changed_data and not self.object.has_changed_language:
            self.object.has_changed_language = True
            self.object.save()

        messages.add_message(
            request=self.request,
            level=messages.SUCCESS,
            message=_('Successfully saved changes.')
        )
        return response


class LogSubscriptionPreferencesView(LoginRequiredMixin, LogSubscriptionPreferencesMixin):
    """
    Get object from authenticated user.
    """
    pass


class SignedLogSubscriptionPreferencesView(LogSubscriptionPreferencesMixin):
    """
    Get object from signed url. If an authenticated user is available, this
    overrides the object from the url.
    """

    def get_success_url(self):
        if self.request.user.is_authenticated():
            return self.success_url
        return self.object.get_signed_url()

    def get_object(self, queryset=None):
        if self.request.user.is_authenticated():
            # maybe: show message on varying objects? seems to be an edge case.
            return super().get_object(queryset=None)

        try:
            signed_id = signing.Signer(
                salt=settings.NOTIFICATIONS_SALT
            ).unsign(self.kwargs['token'])
        except signing.BadSignature:
            raise Http404

        return get_object_or_404(self.model, id=signed_id)
