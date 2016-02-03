from .conf import settings


def force_login_check(view_func):
    """
    Simple decorator to put on views that require a forced check for valid
    credentials (=cookie).

    Args:
        view_func:

    Returns: view_func

    """
    def _wrapped_view_func(request, *args, **kwargs):
        request.session[settings.ACCOUNTS_ENFORCE_LOGIN_NAME] = True
        return view_func(request, *args, **kwargs)
    return _wrapped_view_func
