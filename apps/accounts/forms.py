# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.forms import AuthenticationForm
import floppyforms as forms


class WocatAuthenticationForm(forms.Form, AuthenticationForm):
    """
    Use floppyforms
    """
    username = forms.CharField(
        max_length=255, label=_(u"E-mail address"),
        widget=forms.TextInput(attrs={'tabindex': 1, 'autofocus': True}))
    password = forms.CharField(
        label=_("Password"), widget=forms.PasswordInput(attrs={'tabindex': 2}))
