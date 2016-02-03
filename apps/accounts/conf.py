from django.conf import settings  # noqa
from appconf import AppConf


class AccountConf(AppConf):
    """
    Custom settings for the account module. Mainly settings required for
    the login on the remote system.
    """
    PID = 3
    LOGIN_TYPE = 'login'
    LOGIN_SUCCESS_URL = 'home'
    ENFORCE_LOGIN_TIMEOUT = 300  # 5 Minutes
    ENFORCE_LOGIN_COOKIE_NAME = 'login_expiry'
    ENFORCE_LOGIN_SALT = settings.AUTH_API_USER
    ENFORCE_LOGIN_NAME = 'force_login_check'
