from rest_framework import serializers
from rest_framework.authtoken.serializers import AuthTokenSerializer


class NoteAuthTokenSerializer(AuthTokenSerializer):
    notes = serializers.CharField()
