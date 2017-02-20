"""
This file was generated with the customdashboard management command and
contains the class for the main dashboard.

To activate your index dashboard add the following to your settings.py::
    GRAPPELLI_INDEX_DASHBOARD = 'qcat.dashboard.CustomIndexDashboard'
"""
from django.core.urlresolvers import reverse
from grappelli.dashboard import modules, Dashboard


class CustomIndexDashboard(Dashboard):
    """
    Custom index dashboard for www.
    """

    def init_with_context(self, context):

        # # append a group for "Administration" & "Applications"
        # self.children.append(modules.Group(
        #     _('Group: Administration & Applications'),
        #     column=1,
        #     collapsible=True,
        #     children = [
        #         modules.AppList(
        #             _('Administration'),
        #             column=1,
        #             collapsible=False,
        #             models=('django.contrib.*',),
        #         ),
        #         modules.AppList(
        #             _('Applications'),
        #             column=1,
        #             css_classes=('collapse closed',),
        #             exclude=('django.contrib.*',),
        #         )
        #     ]
        # ))

        self.children.append(modules.ModelList(
            title='Accounts',
            column=1,
            models=('accounts.*',)
        ))

        self.children.append(modules.ModelList(
            title='API',
            column=1,
            models=('api.*', 'rest_framework.*')
        ))

        self.children.append(modules.ModelList(
            title='Configurations',
            column=1,
            models=('configuration.*',),
            exclude=('configuration.models.Translation',),
        ))

        self.children.append(modules.ModelList(
            title='Notifications',
            column=1,
            models=('notifications.*',),
        ))

        self.children.append(modules.ModelList(
            title='Questionnaires',
            column=1,
            models=('questionnaire.*',)
        ))

        self.children.append(modules.ModelList(
            title='Translations',
            column=1,
            models=('configuration.models.Translation',)
        ))


        # # append an app list module for "Administration"
        # self.children.append(modules.ModelList(
        #     _('ModelList: Administration'),
        #     column=1,
        #     collapsible=False,
        #     models=('django.contrib.*',),
        # ))

        self.children.append(modules.LinkList(
            'QCAT',
            column=2,
            children=[
                {
                    'title': 'QCAT Home',
                    'url': reverse('home'),
                },
            ]
        ))

        # append another link list module for "support".
        self.children.append(modules.LinkList(
            'Support',
            column=2,
            children=[
                {
                    'title': 'QCAT Documentation',
                    'url': 'http://qcat.readthedocs.org/en/latest/',
                    'external': True,
                },
                {
                    'title': 'QCAT Documentation (development version)',
                    'url': 'http://qcat.readthedocs.org/en/develop/',
                    'external': True,
                },
            ]
        ))

        # append a recent actions module
        self.children.append(modules.RecentActions(
            'Recent Actions',
            limit=5,
            collapsible=False,
            column=2,
        ))
