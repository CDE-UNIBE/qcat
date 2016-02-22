from configurations import values


class DevMixin:
    DEBUG = values.BooleanValue(True)
    TEMPLATE_DEBUG = values.BooleanValue(True)
    CACHES = values.CacheURLValue('dummy://')
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    WKHTMLTOPDF_CMD_OPTIONS = {
        'quiet': False,
        # 'load-error-handling': 'ignore'
    }


class ProdMixin:
    DEBUG = values.BooleanValue(False)
    TEMPLATE_DEBUG = values.BooleanValue(False)


class SecurityMixin:
    # Security settings, as recommended from manage.py check --deploy
    CSRF_COOKIE_SECURE = True
    X_FRAME_OPTIONS = 'DENY'
    # Set the max-age to 12 months
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    # Turn this on as soon as the site is available with ssl.
    # SECURE_SSL_REDIRECT = True
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
