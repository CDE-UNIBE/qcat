from django.contrib.auth.decorators import login_required

from accounts.decorators import force_login_check
from questionnaire.views import generic_questionnaire_view_step


@login_required
@force_login_check
def questionnaire_view_step(request, identifier, step):
    """
    View rendering the form of a single step of a new SAMPLEMODULE
    questionnaire in read-only mode.
    """
    return generic_questionnaire_view_step(
        request, identifier, step, 'samplemodule',
        page_title='SAMPLEMODULE')
