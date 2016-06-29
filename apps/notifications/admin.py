from django.contrib import admin

from .models import Message


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'action', 'created']
    list_filter = ['questionnaire']
