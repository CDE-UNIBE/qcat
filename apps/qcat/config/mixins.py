from configurations import values


class DevMixin:
    DEBUG = values.BooleanValue(True)
    TEMPLATE_DEBUG = values.BooleanValue(True)
    CACHES = values.CacheURLValue('dummy://')
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    THUMBNAIL_DEBUG = True


class DebugToolbarMixin:
    """
    Not used by default, as it slows down request massively. Use this when
    debugging questionnaires.
    """
    @property
    def INSTALLED_APPS(self):
        return super().INSTALLED_APPS + (
            'debug_toolbar',
        )


class ProdMixin:
    DEBUG = values.BooleanValue(False)
    TEMPLATE_DEBUG = values.BooleanValue(False)

    # Image postprocessors for uploaded images; optimize images.
    THUMBNAIL_OPTIMIZE_COMMAND = {
        'png': '/usr/bin/optipng {filename}',
        'gif': '/usr/bin/optipng {filename}',
        'jpeg': '/usr/bin/jpegoptim {filename}'
    }


class LogMixin:
    """
    Very basic logger - everything with 'warn' or above is written to a file.
    """
    @property
    def LOGGING(self):
        return {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'verbose': {
                    'format': '%(levelname)s %(asctime)s %(module)s %(message)s'
                },
            },
            'handlers': {
                'file': {
                    'level': 'DEBUG',
                    'class': 'logging.handlers.TimedRotatingFileHandler',
                    'when': 'midnight',
                    'backupCount': 5,
                    'filename': '{}/logs/django.log'.format(super().BASE_DIR),
                    'formatter': 'verbose'
                },
            },
            'loggers': {
                '': {
                    'handlers': ['file'],
                    'propagate': True,
                    'level': 'WARNING',
                },
            },
        }


class SecurityMixin:
    # Security settings, as recommended from manage.py check --deploy
    CSRF_COOKIE_SECURE = True
    X_FRAME_OPTIONS = 'DENY'
    # Set the max-age to 12 months
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_HTTPONLY = True


class CompressMixin:
    """Settings for the django-compressor"""
    COMPRESS_ENABLED = True
    # maybe: use different (faster) filters for css and js.


class OpBeatMixin:
    """
    Configure the settings required for opbeat.
    """
    @property
    def INSTALLED_APPS(self):
        return super().INSTALLED_APPS + (
            'opbeat.contrib.django',
        )

    @property
    def OPBEAT(self):
        return {
            'ORGANIZATION_ID': super().OPBEAT_ORGANIZATION_ID,
            'APP_ID': super().OPBEAT_APP_ID,
            'SECRET_TOKEN': super().OPBEAT_SECRET_TOKEN,
        }

    @property
    def MIDDLEWARE_CLASSES(self):
        return super().MIDDLEWARE_CLASSES + (
            'opbeat.contrib.django.middleware.OpbeatAPMMiddleware',
        )


class AuthenticationFeatureSwitch:
    """
    The new authentication is a feature switch, not just a new backend.
    """
    USE_NEW_WOCAT_AUTHENTICATION = values.BooleanValue(
        environ_prefix='', default=False
    )
    CAS_SERVER_URL = values.Value(environ_prefix='', default='')

    @property
    def AUTHENTICATION_BACKENDS(self):
        if self.USE_NEW_WOCAT_AUTHENTICATION:
            return ('django_cas_ng.backends.CASBackend', )
        else:
            return super().AUTHENTICATION_BACKENDS

    @property
    def MIDDLEWARE_CLASSES(self):
        # We probably need a new middleware.
        middlewares = super().MIDDLEWARE_CLASSES
        old_middleware = 'accounts.middleware.WocatAuthenticationMiddleware'
        if old_middleware in middlewares:
            middlewares = list(middlewares)
            middlewares.remove(old_middleware)
            middlewares = tuple(middlewares)
        return middlewares
