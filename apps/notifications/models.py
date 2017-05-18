import contextlib
import functools
import itertools
import logging
import operator

from django.core import signing
from django.core.mail import EmailMultiAlternatives
from django.core.urlresolvers import reverse, reverse_lazy
from django.db import models, transaction
from django.db.models import F, Q
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _, get_language, activate
from django.utils.functional import cached_property

from django_pgjson.fields import JsonBField
from accounts.models import User
from questionnaire.models import Questionnaire, QuestionnaireMembership, STATUSES

from .conf import settings
from .validators import clean_wanted_actions

logger = logging.getLogger(__name__)


class ActionContextQuerySet(models.QuerySet):
    """
    Filters actions according to context. E.g. get actions for my profile
    notifications, get actions for emails.
    """
    def get_questionnaires_for_permissions(self, user) -> list:
        """
        Create filters for questionnaire statuses according to permissions.
        """
        filters = []
        user_permissions = user.get_all_permissions()
        for permission, status in settings.NOTIFICATIONS_QUESTIONNAIRE_STATUS_PERMISSIONS.items():
            if permission in user_permissions:
                filters.append(
                    Q(statusupdate__status=status, action=settings.NOTIFICATIONS_CHANGE_STATUS)
                )
        questionnaire_memberships = QuestionnaireMembership.objects.filter(
            user=user
        )
        for membership in questionnaire_memberships:
            permissions = settings.NOTIFICATIONS_QUESTIONNAIRE_MEMBERSHIP_PERMISSIONS.get(membership.role)
            if permissions:
                filters.append(
                    Q(statusupdate__status__in=permissions,
                      questionnaire=membership.questionnaire)
                )
        return filters

    def user_log_list(self, user: User):
        """
        Fetch all logs where given user is
        - either catalyst or subscriber of the log (set the moment the log was
          created)
        - permitted to see the log as defined by the role.
        - permitted to see the log as defined by the questionnaire membership
        - the action is either a defined 'list' action, or the current user
          is compiler / editor in which case content edits are listed also
        - notifications that are sent to the current user
        """
        # construct filters depending on the users permissions.
        status_filters = self.get_questionnaires_for_permissions(user)
        # extend basic filters according to catalyst / subscriber
        status_filters.extend(
            [Q(subscribers=user), Q(catalyst=user)]
        )

        return self.not_deleted_logs(
            user=user
        ).filter(
            Q(action__in=settings.NOTIFICATIONS_USER_PROFILE_ACTIONS) |
            Q(action=settings.NOTIFICATIONS_EDIT_CONTENT,
              questionnaire__questionnairemembership__user=user,
              questionnaire__questionnairemembership__role__in=[
                  settings.QUESTIONNAIRE_COMPILER,
                  settings.QUESTIONNAIRE_EDITOR
              ]
            ) |
            Q(action=settings.NOTIFICATIONS_FINISH_EDITING, subscribers=user)
        ).filter(
            functools.reduce(operator.or_, status_filters)
        ).distinct()

    def user_pending_list(self, user: User):
        """
        Get logs that the user has to work on. Defined by:
        - the questionnaire still has the same status as when the log was
          created (=no one else gave the 'ok' for the
          next step)
        - user has the permissions to 'ok' the questionnaire for the next
          review step
        - notification is not marked as read
        - if a questionnaire was rejected once, two logs for the same status
          exist. Return only the more current log

        Only distinct questionnaires are expected. However, this doesnt play
        nice with order_by.

        """
        status_filters = self.get_questionnaires_for_permissions(user)
        if not status_filters:
            return self.none()

        logs = self.not_deleted_logs(
            user=user
        ).filter(
            action=settings.NOTIFICATIONS_CHANGE_STATUS,
            statusupdate__status=F('questionnaire__status')
        ).filter(
            functools.reduce(operator.or_, status_filters)
        ).only(
            'id', 'questionnaire_id'
        )

        read_logs = self.read_logs(user=user, log__statusupdate__isnull=False)
        if read_logs.exists():
            # If a log is marked as read, exclude all previous logs for the
            # same questionnaire and the same status from the 'pending'
            # elements.
            logs = logs.exclude(
                functools.reduce(
                    operator.or_,
                    list(self._exclude_previous_logs(read_logs=read_logs))
                )
            ).exclude(
                id__in=read_logs.values_list('id', flat=True)
            )

        return self.filter(
            id__in=[log.id for log in self._unique_questionnaire(logs)]
        )

    def _exclude_previous_logs(self, read_logs):
        """
        Helper to exclude logs that are not read, but are also not pending.
        """
        for read_log in read_logs:
            yield Q(created__lte=read_log.log.created,
                questionnaire_id=read_log.log.questionnaire_id,
                questionnaire__status=read_log.log.statusupdate.status
            )

    def _unique_questionnaire(self, logs):
        """
        Pseudo 'unique' for questionnaire_id for given logs. Required to get
        the first (regarding time) log for each questionnaire.
        """
        questionnaire_ids = []
        for log in logs:
            if log.questionnaire_id not in questionnaire_ids:
                questionnaire_ids.append(log.questionnaire_id)
                yield log

    def user_log_count(self, user: User) -> int:
        """
        Count all unread logs that the user has to work on.
        """
        return self.user_log_list(
            user=user
        ).only(
            'id'
        ).count()

    def not_deleted_logs(self, user: User):
        return self.exclude(
            readlog__log_id=F('id'),
            readlog__user=user,
            readlog__is_deleted=True
        )

    def only_unread_logs(self, user: User):
        """
        Filter out read logs.
        """
        return self.not_deleted_logs(
            user=user
        ).exclude(
            Q(readlog__is_read=True, readlog__user=user)
        )

    def read_logs(self, user: User, **filters):
        """
        Return a list with all log_ids that are read for given user.
        """
        return ReadLog.objects.only(
            'log__id'
        ).filter(
            user=user, is_read=True, **filters
        )

    def read_id_list(self, user: User, **filters) -> list:
        return self.read_logs(
            user=user, **filters
        ).values_list(
            'log__id', flat=True
        )

    def has_permissions_for_questionnaire(self, user: User, questionnaire_code: str) -> bool:
        """
        Check if given user is allowed to see all logs for the questionnaire.
        This is intentionally rather permissive, only a basic 'loose' connection
        to the questionnaire is required.
        """
        if not user or not user.is_authenticated() or not questionnaire_code:
            return False

        has_global_permissions = self.get_questionnaires_for_permissions(user)
        has_logs = Log.objects.filter(
            questionnaire__code=questionnaire_code
        ).filter(
            Q(catalyst=user) |
            Q(subscribers__in=[user]) |
            Q(questionnaire__questionnairemembership__user__in=[user])
        ).exists()
        return has_global_permissions or has_logs

    def get_url_for_questionnaire(self, user: User, questionnaire_code: str) -> str:
        """
        Returns the url with a filter to list logs from the requested
        questionnaire only. Or an empty string.
        """
        if self.has_permissions_for_questionnaire(user, questionnaire_code):
            return '{url}?questionnaire={questionnaire}'.format(
                url=reverse('notification_list'),
                questionnaire=questionnaire_code
            )
        else:
            return ''

    def mark_all_read(self, user: User) -> None:
        """
        Mark all notifications as read in bulk. To prevent edge cases with
        previously existing logs, all logs are removed before the bulk insert.
        """
        self.delete_all_read_logs(user=user)
        log_ids = self.user_log_list(user=user).values_list('id', flat=True)
        ReadLog.objects.bulk_create(
            [ReadLog(user=user, log_id=log, is_read=True) for log in log_ids]
        )

    @staticmethod
    def delete_all_read_logs(user: User):
        ReadLog.objects.filter(user=user, is_deleted=False).delete()


class Log(models.Model):
    """
    Represent a change of the questionnaire. This may be an update of the
    content or a change in the status. New logs should be created only by the
    receivers only.

    If the triggering action is a status change, a StatusUpdate is created.
    If the triggering action is a content change, a ContentUpdate is created.
    If the triggering action is a membership change, a MemberUpdate is created.

    These models are structured in this way that:
    - emails can be sent easily (sender, receivers, subject, message are
      available)
    - all logs for a questionnaire can be found easily
      (Log.objects.filter(questionnaire__code='foo')
    - all logs for a user can be found easily

    Dividing StatusUpdate, MemberUpdate and ContentUpdate is a heuristic choice
    in order to prevent many empty cells on the db. It is expected that more
    ContentUpdates are created.

    """
    created = models.DateTimeField(auto_now_add=True)
    catalyst = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='catalyst',
        help_text='Person triggering the log'
    )
    subscribers = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name='subscribers',
        help_text='All people that are members of the questionnaire'
    )
    questionnaire = models.ForeignKey(Questionnaire)
    action = models.PositiveIntegerField(choices=settings.NOTIFICATIONS_ACTIONS)
    was_processed = models.BooleanField(default=False)

    objects = models.Manager()
    actions = ActionContextQuerySet.as_manager()

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return '{questionnaire}: {action}'.format(
            questionnaire=self.questionnaire.get_name(),
            action=self.get_action_display()
        )

    @cached_property
    def subject(self) -> str:
        """
        Fetch the subject from the related model depending on the action.
        """
        if self.action == settings.NOTIFICATIONS_CREATE:
            action_display = _('was created')
        if self.action == settings.NOTIFICATIONS_DELETE:
            action_display = _('was deleted')
        if self.action == settings.NOTIFICATIONS_CHANGE_STATUS:
            action_display = _('has a new status: {}'.format(
                self.statusupdate.get_status_display())
            )
        if self.action == settings.NOTIFICATIONS_ADD_MEMBER:
            action_display = _('has a new member: {}'.format(
                self.memberupdate.affected.get_display_name()
            ))
        if self.action == settings.NOTIFICATIONS_REMOVE_MEMBER:
            action_display = _('removed a member: {}'.format(
                self.memberupdate.affected.get_display_name()
            ))
        if self.action == settings.NOTIFICATIONS_EDIT_CONTENT:
            action_display = _('was edited by: {}'.format(
                self.catalyst.get_display_name()
            ))
        if self.action == settings.NOTIFICATIONS_FINISH_EDITING:
            action_display = _('{compiler} is finished editing'.format(
                compiler=self.catalyst.get_display_name()
            ))

        return '{questionnaire} {action}'.format(
            questionnaire=self.questionnaire.code,
            action=action_display
        )

    @cached_property
    def mail_subject(self):
        return '[WOCAT] {}'.format(self.subject)

    @cached_property
    def is_content_update(self) -> bool:
        return self.action is settings.NOTIFICATIONS_EDIT_CONTENT

    @cached_property
    def is_change_log(self) -> bool:
        return self.action is settings.NOTIFICATIONS_CHANGE_STATUS

    @cached_property
    def has_no_update(self) -> bool:
        return self.questionnaire.status == self.statusupdate.status

    @cached_property
    def is_workflow_status(self) -> bool:
        return self.statusupdate.status in settings.QUESTIONNAIRE_WORKFLOW_STEPS

    def get_html(self, user: User, is_mail_context=False) -> str:
        """
        The text with links to questionnaire and catalyst, according to the
        type of the action. Use the integer as template name, as this value is
        fixed (opposed to the verbose name).
        """
        return render_to_string(
            template_name='notifications/subject/{}.html'.format(self.action),
            context={
                'log': self,
                'user': user,
                'base_url': settings.BASE_URL,
                'is_mail_context': is_mail_context
            })

    def action_icon(self) -> str:
        """
        Icon-string for action.
        """
        if self.action == settings.NOTIFICATIONS_CHANGE_STATUS:
            direction = 'reject' if self.statusupdate.is_rejected else 'approve'
            key = 'status-{}'.format(direction)
        else:
            key = self.action
        return settings.NOTIFICATIONS_ACTION_ICON.get(key)

    def send_mails(self) -> None:
        """
        Send mails to all recipients, but not compiler and mark log as sent.
        The log is fetched from the db again, as select_for_update must be in
        the same method where the sending of the mail happens to prevent double
        execution.
        """
        with transaction.atomic():
            log = Log.objects.select_for_update(nowait=True).get(id=self.id)
            if not log.was_processed:
                original_locale = get_language()
                for recipient in log.recipients:
                    if recipient.mailpreferences.do_send_mail(log):
                        activate(recipient.mailpreferences.language)
                        message = log.compile_message_to(recipient=recipient)
                        message.send()

                log.was_processed = True
                log.save(update_fields=['was_processed'])
                activate(original_locale)

    @cached_property
    def recipients(self):
        return set(itertools.chain(
            self.subscribers.all(),
            self.get_reviewers(),
            self.get_affected()
        ))

    def get_reviewers(self):
        check_properties = self.is_change_log and self.has_no_update and self.is_workflow_status
        if check_properties:
            return self.questionnaire.get_users_for_next_publish_step()
        return []

    def get_affected(self):
        return [self.memberupdate.affected] if hasattr(self, 'memberupdate') else []

    def compile_message_to(self, recipient: User) -> EmailMultiAlternatives:
        message = EmailMultiAlternatives(
            subject=self.mail_subject,
            body=self.get_mail_template('plain_text.txt', recipient=recipient),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient.email],
            headers={'qcat_log': self.id}
        )
        message.attach_alternative(
            content=self.get_mail_template('html_text.html', recipient=recipient),
            mimetype='text/html'
        )
        return message

    def get_mail_template(self, template_name: str, recipient: User) -> str:
        return render_to_string(
            'notifications/mail/{}'.format(template_name),
            context=self.get_mail_context(recipient)
        )

    def get_mail_context(self, recipient: User) -> dict:
        context = {
            'title': '«{questionnaire}» was updated'.format(
                questionnaire=self.questionnaire.get_name()
            ),
            'name': recipient.get_display_name(),
            'content': self.get_html(recipient, is_mail_context=True),
            'subscription_url': '{base_url}{url}'.format(
                base_url=settings.BASE_URL,
                url=recipient.mailpreferences.get_signed_url()
            ),
            'questionnaire_url': '{base_url}{url}'.format(
                base_url=settings.BASE_URL,
                url=self.questionnaire.get_absolute_url()
            ),
            'base_url': settings.BASE_URL
        }
        if self.is_publish_notification:
            context['content'] += render_to_string(
                'notifications/mail/publish_addendum.html'
            )
        return context

    @property
    def is_publish_notification(self):
        return self.action == settings.NOTIFICATIONS_CHANGE_STATUS and \
               self.statusupdate.status == settings.QUESTIONNAIRE_PUBLIC


class StatusUpdate(models.Model):
    """
    Store the status of the questionnaire in the moment that the log is created
    for all changes regarding the publication cycle.

    """
    log = models.OneToOneField(Log)
    status = models.PositiveIntegerField(
        choices=STATUSES, null=True, blank=True
    )
    is_rejected = models.BooleanField(default=False)
    message = models.TextField()


class InformationUpdate(models.Model):
    """
    Store a text containing some information (right now only editors that have
    finished working on a questionnaire).
    """
    log = models.OneToOneField(Log)
    info = models.TextField()


class MemberUpdate(models.Model):
    """
    Invited or removed members.
    """
    log = models.OneToOneField(Log)
    affected = models.ForeignKey(settings.AUTH_USER_MODEL)
    role = models.CharField(max_length=50)


class ContentUpdate(models.Model):
    """
    Store the previous questionnaires data.
    """
    log = models.OneToOneField(Log)
    data = JsonBField()

    def difference(self) -> dict:
        """
        If the selected package provides consistent results, we may store the
        diff only. Until then, store the whole data and calculate the diff when
        required.
        """
        with contextlib.suppress(Log.DoesNotExist):
            previous = self.log.get_previous_by_created(
                contentupdate__isnull=False
            )
            # calculate diff here.
            return self.data
        return {}


class ReadLog(models.Model):
    """
    Store the 'is_done' state for each user. This is more or less equivalent to
    the 'read' state in any email program. This can't be handled in the
    'through' model of the subscriber, as the status must also be stored for
    the catalyst.
    """
    log = models.ForeignKey(Log, on_delete=models.PROTECT)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    is_read = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        # only one read status per user and log, preventing a race condition.
        unique_together = ['log', 'user']


class MailPreferences(models.Model):
    """
    User preferences for receiving email notifications.
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL)
    subscription = models.CharField(
        max_length=10, choices=settings.NOTIFICATIONS_EMAIL_SUBSCRIPTIONS, default='all'
    )
    wanted_actions = models.CharField(
        max_length=255,  blank=True, validators=[clean_wanted_actions],
        verbose_name=_('Subscribed for following changes in the review status')
    )
    language = models.CharField(
        max_length=2, choices=settings.LANGUAGES, default=settings.LANGUAGES[0][0]
    )
    has_changed_language = models.BooleanField(default=False)

    def get_defaults(self) -> tuple:
        """
        Staff users requested a more restrictive set of defaults to reduce
        amount of mails received.
        """
        is_special_user = self.user.groups.exists() or self.user.is_staff
        if is_special_user:
            subscription = settings.NOTIFICATIONS_TODO_MAILS
            wanted_actions = str(settings.NOTIFICATIONS_CHANGE_STATUS)
        else:
            subscription = settings.NOTIFICATIONS_ALL_MAILS
            wanted_actions = ','.join([str(pref) for pref in settings.NOTIFICATIONS_EMAIL_PREFERENCES])

        return subscription, wanted_actions

    def do_send_mail(self, log: Log) -> bool:
        return all([
            self.is_allowed_send_mails,
            self.is_wanted_action(log.action),
            self.is_todo_log(log)
        ])

    def set_defaults(self):
        self.subscription, self.wanted_actions = self.get_defaults()
        self.save()

    @property
    def is_allowed_send_mails(self):
        is_subscriber = self.subscription != settings.NOTIFICATIONS_NO_MAILS
        is_staff_only = not settings.DO_SEND_STAFF_ONLY or self.user.is_staff
        return settings.DO_SEND_EMAILS and is_subscriber and is_staff_only

    def is_wanted_action(self, action: int) -> bool:
        return str(action) in self.wanted_actions.split(',')

    def is_todo_log(self, log: Log):
        """
        Implemented like this to make sure to reuse code. Could be better
        performance-wise, but doesn't really matter as long as mails are sent
        within a management command.
        """
        return self.subscription != settings.NOTIFICATIONS_TODO_MAILS or \
               log.is_change_log and log in Log.actions.user_pending_list(user=self.user)

    def get_signed_url(self):
        return reverse_lazy('signed_notification_preferences', kwargs={
            'token': signing.Signer(salt=settings.NOTIFICATIONS_SALT).sign(self.id)
        })
