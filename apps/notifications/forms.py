import re

import floppyforms.__future__ as forms

from .conf import settings
from .models import MailPreferences

actions_dict = dict(settings.NOTIFICATIONS_ACTIONS)


class MailPreferencesUpdateForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        """
        Reduce available options for non staff members, as they are not easy
        to understand.
        """
        super().__init__(*args, **kwargs)
        if not kwargs['instance'].user.is_staff:
            self.fields['subscription'].choices = [
                settings.NOTIFICATIONS_EMAIL_SUBSCRIPTIONS[0],
                settings.NOTIFICATIONS_EMAIL_SUBSCRIPTIONS[2]
            ]
            self.fields['wanted_actions'].widget = forms.HiddenInput()

    class Meta:
        model = MailPreferences
        fields = ('subscription', 'wanted_actions', 'language', )
        widgets = {
            'wanted_actions': forms.CheckboxSelectMultiple(choices=(
                (status, actions_dict[status]) for status in settings.NOTIFICATIONS_EMAIL_PREFERENCES)
            )
        }

    def clean_wanted_actions(self):
        integers = re.findall('\d+', self.cleaned_data['wanted_actions'])
        return ','.join(integers)
