from accounts.models import User
from questionnaire.models import Questionnaire

from .models import Log, StatusUpdate, ContentUpdate, MemberUpdate, \
    InformationUpdate


class CreateLog:
    """
    Create a new log an set the required instance variables for status and content updates.
    """
    def __init__(self, action: int, sender: User, questionnaire: Questionnaire, **kwargs):
        self.questionnaire = questionnaire
        self.log = self.create_log(sender, action)
        self.add_members(sender=sender)

    def create_log(self, sender: User, action: int) -> Log:
        return Log.objects.create(
            catalyst=sender,
            action=action,
            questionnaire=self.questionnaire
        )

    def add_members(self, sender: User):
        # Add current members as receivers.
        members = self.questionnaire.questionnairemembership_set.exclude(
            user=sender
        ).values_list(
            'user_id', flat=True
        )
        self.log.subscribers.add(*members)


class ContentLog(CreateLog):
    """
    Helper to create logs for changed questionnaire data.
    """
    def create(self):
        ContentUpdate.objects.create(
            log=self.log,
            data=self.questionnaire.data
        )


class StatusLog(CreateLog):
    """
    Helper to create logs for changed review cycle status.
    """
    def create(self, is_rejected: bool, message: str):
        StatusUpdate.objects.create(
            log=self.log,
            status=self.questionnaire.status,
            is_rejected=is_rejected,
            message=message
        )


class MemberLog(CreateLog):
    """
    Helper to create logs for changed questionnaire membership.
    """
    def create(self, affected: User, role: str):
        MemberUpdate.objects.create(
            log=self.log,
            affected=affected,
            role=role
        )


class InformationLog(CreateLog):
    """
    Helper to create logs for info messages.
    """

    def __init__(self, action: int, sender: User, questionnaire: Questionnaire,
                 receiver: User, *args, **kwargs):
        self.questionnaire = questionnaire
        self.log = self.create_log(sender=sender, action=action)
        self.add_receiver(receiver)

    def add_receiver(self, receiver):
        self.log.subscribers.add(receiver)

    def create(self, info: str):
        InformationUpdate.objects.create(
            log=self.log,
            info=info
        )
