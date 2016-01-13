from os.path import join, dirname
from django.contrib.messages import constants as messages
from django.utils.translation import ugettext_lazy as _
from configurations import Configuration, values


class BaseSettings(Configuration):
    """
    Django settings for qcat project.

    For more information on this file, see
    https://docs.djangoproject.com/en/dev/topics/settings/

    For the full list of settings and their values, see
    https://docs.djangoproject.com/en/dev/ref/settings/
    """

    # Build paths inside the project like this: os.path.join(BASE_DIR, ...)
    BASE_DIR = join(dirname(dirname(dirname(dirname(__file__)))))

    # Quick-start development settings - unsuitable for production
    # See https://docs.djangoproject.com/en/dev/howto/deployment/checklist/

    # Application definition
    INSTALLED_APPS = (
        'grappelli.dashboard',
        'grappelli',
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.staticfiles',
        'django_nose',
        'floppyforms',
        'django_extensions',
        'imagekit',
        'rest_framework',
        'django_filters',
        'maintenancemode',
        'wkhtmltopdf',
        # Custom apps
        'questionnaire',
        'accounts',
        'api',
        'configuration',
        'wocat',
        'technologies',
        'approaches',
        'unccd',
        'search',
        'sample',
        'samplemulti',
    )

    MIDDLEWARE_CLASSES = (
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.security.SecurityMiddleware',
        'django.middleware.locale.LocaleMiddleware',
        'django.middleware.common.CommonMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
        'accounts.authentication.WocatAuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
        'django.middleware.clickjacking.XFrameOptionsMiddleware',
        'maintenancemode.middleware.MaintenanceModeMiddleware',
    )

    ROOT_URLCONF = 'qcat.urls'

    WSGI_APPLICATION = 'qcat.wsgi.application'

    # Internationalization
    # https://docs.djangoproject.com/en/dev/topics/i18n/
    LANGUAGE_CODE = 'en'

    LOCALE_PATHS = (
        join(BASE_DIR, '../qcat/locale'),
    )

    # The first language is the default language.
    LANGUAGES = (
        ('en', _('English')),
        ('es', _('Spanish')),
        ('fr', _('French')),
    )

    TIME_ZONE = 'Europe/Zurich'
    USE_I18N = True
    USE_L10N = True
    USE_TZ = True

    # Static files (CSS, JavaScript, Images)
    # https://docs.djangoproject.com/en/dev/howto/static-files/
    STATIC_URL = '/static/'
    STATIC_ROOT = join(BASE_DIR, '..', 'static')
    STATICFILES_DIRS = (
        join(BASE_DIR, 'static'),
    )

    MEDIA_URL = '/upload/'
    MEDIA_ROOT = join(BASE_DIR, '..', 'upload')

    UPLOAD_VALID_FILES = {
        'image': (
            ('image/jpeg', 'jpg'),
            ('image/png', 'png'),
            ('image/gif', 'gif'),
        ),
        'document': (
            ('application/pdf', 'pdf'),
        )
    }
    UPLOAD_MAX_FILE_SIZE = 3145728  # 3 MB
    UPLOAD_IMAGE_THUMBNAIL_FORMATS = (
        ('default', (640, 480)),
        ('small', (1024, 768)),
        ('medium', (1440, 1080)),
        # 'large' is the original uploaded image.
    )

    TEMPLATE_DIRS = (
        join(BASE_DIR, 'templates'),
    )

    TEMPLATE_CONTEXT_PROCESSORS = (
        "django.contrib.auth.context_processors.auth",
        "django.core.context_processors.debug",
        "django.core.context_processors.i18n",
        "django.core.context_processors.media",
        "django.core.context_processors.static",
        "django.core.context_processors.tz",
        "django.contrib.messages.context_processors.messages",
        'django.core.context_processors.request',
    )

    AUTH_USER_MODEL = 'accounts.User'
    AUTHENTICATION_BACKENDS = (
        'accounts.authentication.WocatAuthenticationBackend',
    )
    LOGIN_URL = 'login'

    # TODO: Try if tests can be run with --with-fixture-bundling
    TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
    NOSE_ARGS = [
        '--cover-html', '--cover-html-dir=coverage_html', '--cover-erase',
        '--cover-package=accounts,configuration,qcat,questionnaire,unccd',
        '--nologcapture']

    GRAPPELLI_ADMIN_TITLE = 'QCAT Administration'
    GRAPPELLI_INDEX_DASHBOARD = 'qcat.dashboard.CustomIndexDashboard'

    # Elasticsearch settings
    ES_HOST = values.Value(default='localhost', environ_prefix='')
    ES_PORT = values.IntegerValue(default=9200, environ_prefix='')
    ES_INDEX_PREFIX = values.Value(default='qcat_', environ_prefix='')

    # For each language (as set in the setting ``LANGUAGES``), a language
    # analyzer can be specified. This helps to analyze the text in the
    # corresponding language for better search results.
    # https://www.elastic.co/guide/en/elasticsearch/reference/1.6/analysis-lang-analyzer.html  # noqa
    ES_ANALYZERS = (
        ('en', 'english'),
        ('es', 'spanish'),
    )

    MESSAGE_TAGS = {
        messages.INFO: 'secondary',
    }

    # Allow various formats to communicate with the API.
    REST_FRAMEWORK = {
        'DEFAULT_PARSER_CLASSES': (
            'rest_framework.parsers.JSONParser',
            'rest_framework_xml.parsers.XMLParser',
        ),
        'DEFAULT_RENDERER_CLASSES': (
            'rest_framework.renderers.BrowsableAPIRenderer',
            'rest_framework.renderers.JSONRenderer',
            'rest_framework_xml.renderers.XMLRenderer',
            'rest_framework_csv.renderers.CSVRenderer',
        ),
    }

    DATABASES = values.DatabaseURLValue()

    # SECURITY WARNING: don't run with debug turned on in production!
    DEBUG = values.BooleanValue(default=False)

    TEMPLATE_DEBUG = values.BooleanValue(default=False)

    ALLOWED_HOSTS = values.ListValue(default=['localhost', '127.0.0.1'])

    SECRET_KEY = values.SecretValue()

    # The base URL of the Typo3 REST API used for authentication
    AUTH_API_URL = values.Value(environ_prefix='',
                                default='https://dev.wocat.net/rest/')

    # The username used for API login
    AUTH_API_USER = values.Value(environ_prefix='')

    # The key used for API login
    AUTH_API_KEY = values.Value(environ_prefix='')

    # The URL of the WOCAT authentication form. Used to handle both login
    # and logout
    AUTH_LOGIN_FORM = values.Value(
        environ_prefix='',
        default='https://dev.wocat.net/en/sitefunctions/login.html'
    )

    # https://raw.githubusercontent.com/SeleniumHQ/selenium/master/py/CHANGES
    # for the latest supported firefox version.
    TESTING_FIREFOX_PATH = values.Value(environ_prefix='')

    USE_CACHING = values.BooleanValue(default=True)
    CACHES = values.CacheURLValue(default='locmem://')

    MAINTENANCE_MODE = values.BooleanValue(environ_prefix='', default=False)

    WKHTMLTOPDF_CMD = values.Value(environ_prefix='')
