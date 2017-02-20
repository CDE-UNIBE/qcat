from django.contrib import admin

from .models import Log


@admin.register(Log)
class MessageAdmin(admin.ModelAdmin):
    date_hierarchy = 'created'
    list_display = ['id', '__str__', 'action', 'catalyst', 'created', 'subject']
    list_display_links = ['id', '__str__']
    list_filter = ['created', 'action', 'questionnaire']
