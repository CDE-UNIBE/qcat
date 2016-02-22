from django import template
from questionnaire.models import Questionnaire

register = template.Library()


@register.assignment_tag
def call_model_method(method, obj, user):
    """
    Call a method on the Questionnaire model with given user and return its
    result.

    Args:
        method: string (method to call)
        obj: questionnaire.models.Questionnaire
        user: accounts.User

    Returns:
        string: result of the called function

    """
    if isinstance(obj, Questionnaire):
        result = getattr(obj, method)(user)
        return result if not isinstance(result, tuple) else result[1]
    return ''
