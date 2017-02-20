from django.contrib import admin

from .models import Lock


@admin.register(Lock)
class LockAdmin(admin.ModelAdmin):

    def questionnaire_code(self):
        return self.questionnaire.code

    list_display = ['id', questionnaire_code, 'user', 'start', 'is_finished']
