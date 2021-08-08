import functools
import itertools
import logging
import operator

from django.core import signing
from django.core.mail import EmailMultiAlternatives
from django.urls import reverse, reverse_lazy
from django.db import models, transaction
from django.db.models import F, Q
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _, get_language, activate
from django.utils.functional import cached_property

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
        help_text='Person triggering the log',
        on_delete=models.SET_DEFAULT
    )
    subscribers = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name='subscribers',
        help_text='All people that are members of the questionnaire'
    )
    questionnaire = models.ForeignKey(Questionnaire,on_delete=models.SET_DEFAULT)
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
    def notification_subject(self) -> str:
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

    @cached_property
    def is_rejected(self) -> bool:
        if not hasattr(self, 'statusupdate'):
            return False
        return self.statusupdate.is_rejected

    def get_notification_html(self, user: User) -> str:
        """
        The text with links to questionnaire and catalyst, according to the
        type of the action. Use the integer as template name, as this value is
        fixed (opposed to the verbose name).
        """
        return render_to_string(
            template_name='notifications/notification/{}.html'.format(self.action),
            context={
                'log': self,
                'user': user,
                'base_url': settings.BASE_URL,
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

    def get_assigned_users(self):
        """
        Get users linked (assigned) to the questionnaire who will be notified.
        """
        if self.action in [
            settings.NOTIFICATIONS_ADD_MEMBER,
            settings.NOTIFICATIONS_REMOVE_MEMBER,
        ]:
            # When adding or removing member, do not notify any assigned users.
            return []
        elif self.is_rejected:
            if self.statusupdate.previous_status == settings.QUESTIONNAIRE_SUBMITTED:
                # If rejected from submitted, notify compiler and assigned editors
                return self.questionnaire.get_users_by_roles([
                    'compiler',
                    'editor',
                ])
            if self.statusupdate.previous_status == settings.QUESTIONNAIRE_REVIEWED:
                # If rejected from reviewed, notify compiler, assigned editors
                # and assigned reviewers.
                return self.questionnaire.get_users_by_roles([
                    'compiler',
                    'editor',
                    'reviewer',
                ])
        elif self.action == settings.NOTIFICATIONS_CHANGE_STATUS:
            if self.questionnaire.status == settings.QUESTIONNAIRE_SUBMITTED:
                # If submitted, notify assigned reviewers.
                # return self.questionnaire.get_users_by_role('reviewer')
                return self.questionnaire.get_users_by_roles([
                    'reviewer',
                ])
            if self.questionnaire.status == settings.QUESTIONNAIRE_REVIEWED:
                # If reviewed, notify compiler, assigned editors and assigned
                # publishers.
                return self.questionnaire.get_users_by_roles([
                    'compiler',
                    'editor',
                    'publisher',
                ])
            if self.questionnaire.status == settings.QUESTIONNAIRE_PUBLIC:
                # If published, notify compiler, assigned editors and assigned
                # reviewers.
                return self.questionnaire.get_users_by_roles([
                    'compiler',
                    'editor',
                    'reviewer',
                ])
        return self.subscribers.all()

    @cached_property
    def recipients(self):
        return set(itertools.chain(
            self.get_assigned_users(),
            self.get_reviewers(),
            self.get_affected(),
            self.get_rejected_users(),
        ))

    def get_rejected_users(self):
        if self.is_change_log and self.is_rejected:
            return set(itertools.chain(
                self.questionnaire.get_users_by_role(settings.QUESTIONNAIRE_COMPILER),
                self.questionnaire.get_users_by_role(settings.QUESTIONNAIRE_EDITOR)
            ))
        return []

    def get_reviewers(self):
        """
        Get the reviewers which have to be notified by mail. As discussed on
        October 25 2018, this is always the wocat mailbox user who will be
        notified if a questionnaire changes its status or if it was deleted.
        """
        check_properties = self.is_change_log or self.action == settings.NOTIFICATIONS_DELETE
        if check_properties:
            wocat_user = self.questionnaire.get_wocat_mailbox_user()
            if wocat_user:
                return [wocat_user]
        return []

    def get_affected(self):
        return [self.memberupdate.affected] if hasattr(self, 'memberupdate') else []

    def get_mail_context(self, recipient: User) -> dict:
        # Prepare and return the context used to render both HTML and plain text
        # mails.
        compilers = self.questionnaire.get_users_by_role(
            settings.QUESTIONNAIRE_COMPILER)
        if compilers:
            compiler = compilers[0]
        else:
            compiler = None

        message = None
        if hasattr(self, 'statusupdate'):
            message = self.statusupdate.message
        if hasattr(self, 'informationupdate'):
            message = self.informationupdate.info

        role = None
        if hasattr(self, 'memberupdate'):
            role = self.memberupdate.role

        return {
            'recipient_name': recipient.get_display_name(),
            'recipient_url': f'{settings.BASE_URL}{recipient.get_absolute_url()}',
            'subscription_url': '{base_url}{url}'.format(
                base_url=settings.BASE_URL,
                url=recipient.mailpreferences.get_signed_url()
            ),
            'questionnaire': self.questionnaire,
            'questionnaire_url': f'{settings.BASE_URL}{self.questionnaire.get_absolute_url()}',
            'questionnaire_name': self.get_questionnaire_name_mail(),
            'compiler': compiler,
            'message': message,
            'role': role,
            'catalyst': self.catalyst,
            'base_url': settings.BASE_URL,
        }

    def get_mail_data(self, recipient: User) -> tuple:
        # Return a tuple with [0] context (with key "content" containing the
        # dynamic parts of the mail) and [1] subject for the mail.
        context = self.get_mail_context(recipient)

        # Decide which subject and template to use for the mail. Not very nice,
        # but it works ...
        mail_keyword = None
        if self.is_rejected:
            if self.statusupdate.previous_status == settings.QUESTIONNAIRE_SUBMITTED:
                # Rejected from submitted
                mail_keyword = 'rejected_submitted'
            elif self.statusupdate.previous_status == settings.QUESTIONNAIRE_REVIEWED:
                # Rejected from reviewed
                mail_keyword = 'rejected_reviewed'
        elif self.action == settings.NOTIFICATIONS_CHANGE_STATUS:
            if self.questionnaire.status == settings.QUESTIONNAIRE_SUBMITTED:
                # Submitted a draft questionnaire
                mail_keyword = 'submitted'
            elif self.questionnaire.status == settings.QUESTIONNAIRE_REVIEWED:
                # Reviewed a submitted questionnaire
                mail_keyword = 'reviewed'
            elif self.questionnaire.status == settings.QUESTIONNAIRE_PUBLIC:
                # Published a reviewed questionnaire
                mail_keyword = 'published'
        elif self.action == settings.NOTIFICATIONS_DELETE:
            mail_keyword = 'deleted'
        elif self.action == settings.NOTIFICATIONS_ADD_MEMBER:
            if self.memberupdate.role == 'compiler':
                # Added a new compiler.
                mail_keyword = 'compiler_added'
                # Do not mention the compiler in this mail, as the compiler has
                # just changed.
                context.update({'compiler': None})
            elif self.memberupdate.role == 'editor':
                # Added a new editor
                mail_keyword = 'editor_added'
            elif self.memberupdate.role == 'reviewer':
                # Added a new reviewer
                mail_keyword = 'reviewer_added'
            elif self.memberupdate.role == 'publisher':
                # Added a new publisher
                mail_keyword = 'publisher_added'
        elif self.action == settings.NOTIFICATIONS_REMOVE_MEMBER:
            if self.memberupdate.role == 'compiler':
                # Removed a compiler
                mail_keyword = 'compiler_removed'
                # Do not mention the compiler in this mail, as the compiler has
                # just changed.
                context.update({'compiler': None})
            elif self.memberupdate.role == 'editor':
                # Removed an editor
                mail_keyword = 'editor_removed'
            elif self.memberupdate.role == 'reviewer':
                # Removed a reviewer
                mail_keyword = 'reviewer_removed'
            elif self.memberupdate.role == 'publisher':
                # Removed a publisher
                mail_keyword = 'publisher_removed'
        elif self.action == settings.NOTIFICATIONS_FINISH_EDITING:
            # Editor has finished editing
            mail_keyword = 'edited'

        if mail_keyword:
            content = render_to_string(
                f'notifications/mail/partial/{mail_keyword}.html',
                context=context
            )
            subject = settings.NOTIFICATIONS_MAIL_SUBJECTS[mail_keyword]
        else:
            content = ''
            subject = ''

        context.update({
            'title': f'{self.get_questionnaire_name_mail()}: {subject}',
            'content': content,
        })

        return context, f'[WOCAT] {self.questionnaire.get_name()}: {subject}'

    def compile_message_to(self, recipient: User) -> EmailMultiAlternatives:
        context, subject = self.get_mail_data(recipient=recipient)
        message = EmailMultiAlternatives(
            subject=subject,
            body=self.get_mail_template('plain_text.txt', context=context),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient.email],
            headers={'qcat_log': self.id}
        )
        message.attach_alternative(
            content=self.get_mail_template('html_text.html', context=context),
            mimetype='text/html'
        )
        return message

    @staticmethod
    def get_mail_template(template_name: str, context: dict) -> str:
        return render_to_string(
            'notifications/mail/{}'.format(template_name),
            context=context
        )

    @property
    def is_publish_notification(self):
        return self.action == settings.NOTIFICATIONS_CHANGE_STATUS and \
               self.statusupdate.status == settings.QUESTIONNAIRE_PUBLIC

    def get_questionnaire_name_mail(self):
        return f'«{self.questionnaire.get_name()}» ({self.questionnaire.code})'


class StatusUpdate(models.Model):
    """
    Store the status of the questionnaire in the moment that the log is created
    for all changes regarding the publication cycle.

    """
    log = models.OneToOneField(Log,on_delete=models.SET_DEFAULT)
    status = models.PositiveIntegerField(
        choices=STATUSES, null=True, blank=True
    )
    is_rejected = models.BooleanField(default=False)
    message = models.TextField()
    previous_status = models.PositiveIntegerField(
        choices=STATUSES, null=True, blank=True)


class InformationUpdate(models.Model):
    """
    Store a text containing some information (right now only editors that have
    finished working on a questionnaire).
    """
    log = models.OneToOneField(Log,on_delete=models.SET_DEFAULT)
    info = models.TextField()


class MemberUpdate(models.Model):
    """
    Invited or removed members.
    """
    log = models.OneToOneField(Log,on_delete=models.SET_DEFAULT)
    affected = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_DEFAULT)
    role = models.CharField(max_length=50)


class ContentUpdate(models.Model):
    """
    Store the previous questionnaires data.
    This used to be the basis for a 'comparison of case versions', but the diff / full data
    is not stored anymore, as this feature is not on the radar anymore and the sysadmin
    complained about the large, unused fields.
    """
    log = models.OneToOneField(Log,on_delete=models.SET_DEFAULT)


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
    user = models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.SET_DEFAULT)
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
