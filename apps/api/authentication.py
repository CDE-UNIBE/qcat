from rest_framework.authentication import TokenAuthentication

from .models import NoteToken


class NoteTokenAuthentication(TokenAuthentication):
    """Use our custom model for the token auth"""
    model = NoteToken
