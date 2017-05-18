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
        'django.contrib.contenttypes',
        'grappelli.dashboard',
        'grappelli',
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.sitemaps',
        'django.contrib.staticfiles',
        'django.contrib.humanize',
        'compressor',
        'django_nose',
        'django_extensions',
        'django_filters',
        'easy_thumbnails',
        'easy_thumbnails.optimize',
        'floppyforms',
        'imagekit',
        'maintenancemode',
        'rest_framework',
        'rest_framework_swagger',
        'sekizai',
        'wkhtmltopdf',
        # Custom apps
        'accounts',
        'api',
        'approaches',
        'configuration',
        'qcat',
        'questionnaire',
        'notifications',
        'sample',
        'samplemulti',
        'samplemodule',
        'search',
        'summary',
        'technologies',
        'unccd',
        'watershed',
        'wocat',
        'cca',
    )

    MIDDLEWARE_CLASSES = (
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.security.SecurityMiddleware',
        'django.middleware.locale.LocaleMiddleware',
        'django.middleware.common.CommonMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
        'accounts.middleware.WocatAuthenticationMiddleware',
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
        join(BASE_DIR, 'locale'),
    )

    # The first language is the default language.
    LANGUAGES = (
        ('en', _('English')),
        ('fr', _('French')),
        ('es', _('Spanish')),
        ('ru', _('Russian')),
        ('km', _('Khmer')),
        ('lo', _('Lao')),
        ('ar', _('Arabic')),
        ('pt', _('Portuguese')),
        ('af', _('Afrikaans')),
    )
    # languages with extraordinarily long words that need 'forced' line breaks
    # to remain consistent in the box-layout.
    WORD_WRAP_LANGUAGES = [
        'km',
        'lo',
    ]

    TIME_ZONE = 'Europe/Zurich'
    USE_I18N = True
    USE_L10N = True
    USE_TZ = True
    BASE_URL = values.Value(environ_prefix='', default='https://qcat.wocat.net')

    # Static files (CSS, JavaScript, Images)
    # https://docs.djangoproject.com/en/dev/howto/static-files/
    STATIC_URL = '/static/'
    STATIC_ROOT = join(BASE_DIR, '..', 'static')
    STATICFILES_DIRS = (
        join(BASE_DIR, 'static'),
    )
    STATICFILES_FINDERS = (
        'django.contrib.staticfiles.finders.FileSystemFinder',
        'django.contrib.staticfiles.finders.AppDirectoriesFinder',
        'compressor.finders.CompressorFinder',
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
    THUMBNAIL_ALIASES = {
        'summary': {
            'screen': {
                'header_image': {
                    'size': (0, 1840),
                    'crop': 'smart',
                    'upscale': True
                },
                'half_height': {
                    'size': (640, 640),
                    'crop': 'smart',
                    'upscale': True
                },
                'map': {
                    'size': (560, 0)
                },
                'flow_chart': {
                    'size': (900, 0),
                    'upscale': True
                }
            },
            'print': {
                'header_image': {
                    'size': (0, 7360),
                    'crop': 'smart',
                    'upscale': True
                },
                'half_height': {
                    'size': (2560, 2560),
                    'crop': 'smart',
                    'upscale': True
                },
                'map': {
                    'size': (2240, 0)
                },
                'flow_chart': {
                    'size': (3600, 0),
                    'upscale': True
                }
            }
        }
    }

    SUMMARY_PDF_PATH = join(MEDIA_ROOT, 'summary-pdf')

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
        'sekizai.context_processors.sekizai',
        'qcat.context_processors.template_settings'
    )

    AUTH_USER_MODEL = 'accounts.User'
    AUTHENTICATION_BACKENDS = (
        'accounts.authentication.WocatAuthenticationBackend',
    )
    LOGIN_URL = 'login'

    TEST_RUNNER = 'qcat.discover_runner.QcatTestSuiteRunner'
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
    # For Elasticsearch >= 2.3: https://www.elastic.co/guide/en/elasticsearch/reference/current/breaking-changes-2.3.html  # noqa
    ES_NESTED_FIELDS_LIMIT = values.IntegerValue(default=250, environ_prefix='')
    # For each language (as set in the setting ``LANGUAGES``), a language
    # analyzer can be specified. This helps to analyze the text in the
    # corresponding language for better search results.
    # https://www.elastic.co/guide/en/elasticsearch/reference/1.6/analysis-lang-analyzer.html  # noqa
    ES_ANALYZERS = (
        ('en', 'english'),
        ('es', 'spanish'),
    )
    # https://www.elastic.co/guide/en/elasticsearch/reference/2.0/query-dsl-query-string-query.html#_reserved_characters
    ES_QUERY_RESERVED_CHARS = ['\\', '+', '-', '=', '&&', '||', '>', '<', '!', '(', ')', '{', '}', '[', ']', '^', '"',
                               '~', '*', '?', ':', '/']

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
            'rest_framework.renderers.JSONRenderer',
            'rest_framework_xml.renderers.XMLRenderer',
            'rest_framework_csv.renderers.CSVRenderer',
        ),
        'DEFAULT_THROTTLE_RATES': {
            'anon': '10/day',
            'user': '2000/day',
        },
        'DEFAULT_VERSIONING_CLASS':
            'rest_framework.versioning.NamespaceVersioning',
        'PAGE_SIZE': 25,
    }
    SWAGGER_SETTINGS = {
        'api_version': '0.1',
        'doc_expansion': 'list',
        'exclude_namespaces': ['api-root'],
    }
    API_PAGE_SIZE = values.IntegerValue(default=25, environ_prefix='')

    DATABASES = values.DatabaseURLValue(environ_required=True)

    # SECURITY WARNING: don't run with debug turned on in production!
    DEBUG = values.BooleanValue(default=False)

    TEMPLATE_DEBUG = values.BooleanValue(default=False)

    ALLOWED_HOSTS = values.ListValue(default=['localhost', '127.0.0.1'])

    SECRET_KEY = values.SecretValue(environ_required=True)

    # The base URL of the Typo3 REST API used for authentication
    AUTH_API_URL = values.Value(environ_prefix='',
                                default='https://beta.wocat.net/api/v1/')

    # The username used for API login
    AUTH_API_USER = values.Value(environ_prefix='')

    # The key used for API login
    AUTH_API_KEY = values.Value(environ_prefix='')
    AUTH_API_TOKEN = values.Value(environ_prefix='')

    # The URL of the WOCAT authentication form. Used to handle both login
    # and logout
    AUTH_LOGIN_FORM = values.Value(
        environ_prefix='',
        default='https://dev.wocat.net/en/sitefunctions/login.html'
    )
    AUTH_COOKIE_NAME = values.Value(default='fe_typo_user', environ_prefix='')

    # https://raw.githubusercontent.com/SeleniumHQ/selenium/master/py/CHANGES
    # for the latest supported firefox version.
    TESTING_FIREFOX_PATH = values.Value(environ_prefix='')

    USE_CACHING = values.BooleanValue(default=True)
    CACHES = values.CacheURLValue(default='locmem://')
    KEY_PREFIX = values.Value(environ_prefix='', default='')

    # If set to true, the template 503.html is displayed.
    MAINTENANCE_MODE = values.BooleanValue(environ_prefix='', default=False)
    MAINTENANCE_LOCKFILE_PATH = join(BASE_DIR, 'maintenance.lock')

    # "Feature toggles"
    IS_ACTIVE_FEATURE_MODULE = values.BooleanValue(
        environ_prefix='', default=False
    )
    IS_ACTIVE_FEATURE_WATERSHED = values.BooleanValue(
        environ_prefix='', default=False
    )

    SENTRY_DSN = values.Value(environ_prefix='')

    HOST_STRING_DEV = values.Value(environ_prefix='')
    HOST_STRING_DEMO = values.Value(environ_prefix='')
    HOST_STRING_LIVE = values.Value(environ_prefix='')

    # touch file to reload uwsgi
    TOUCH_FILE_DEV = values.Value(environ_prefix='')
    TOUCH_FILE_DEMO = values.Value(environ_prefix='')
    TOUCH_FILE_LIVE = values.Value(environ_prefix='')

    WARN_HEADER = values.Value(environ_prefix='')
    NEXT_MAINTENANCE = join(BASE_DIR, 'envs/NEXT_MAINTENANCE')
    DEPLOY_TIMEOUT = values.Value(environ_prefix='', default=900)

    # Settings for piwik integration. Tracking happens in the frontend
    # (base template) and backend (API)
    PIWIK_SITE_ID = values.IntegerValue(environ_prefix='', default=None)
    PIWIK_URL = values.Value(environ_prefix='', default='https://piwik.wocat.net/')
    PIWIK_AUTH_TOKEN = values.Value(environ_prefix='')
    PIWIK_API_VERSION = values.IntegerValue(environ_prefix='', default=1)

    # google webdeveloper verification
    GOOGLE_WEBMASTER_TOOLS_KEY = values.Value(environ_prefix='')

    # Google Maps Javascript API key
    GOOGLE_MAPS_JAVASCRIPT_API_KEY = values.Value(environ_prefix='')

    # Mail settings (notification mails)
    DEFAULT_FROM_EMAIL = 'info@wocat.net'
    DO_SEND_EMAILS = values.BooleanValue(environ_prefix='', default=False)
    DO_SEND_STAFF_ONLY = values.BooleanValue(environ_prefix='', default=True)

    WOCAT_IMPORT_DATABASE_URL = values.Value(environ_prefix='')
    WOCAT_IMPORT_DATABASE_URL_LOCAL = values.Value(environ_prefix='')

    # TODO: Temporary test of UNCCD flagging.
    TEMP_UNCCD_TEST = values.ListValue(environ_prefix='')
