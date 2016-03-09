from django.conf import settings


def warn_header(request):
    """
    Put the text from the env var into the template.
    """
    return {'WARN_HEADER': settings.WARN_HEADER}
