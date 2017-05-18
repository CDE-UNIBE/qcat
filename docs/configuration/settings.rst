Application settings
====================

This chapter covers the configuration of the QCAT application. The pattern
```config``` from the 12 factor app is widely followed, so many variables are
stored in the environment.

For easy management of environment variables, the package `envdir`_ is used.
The variables are stored in the folder ```/envs```; your folder should look as
follows ::

    envs/
    ├── AUTH_API_KEY
    ├── AUTH_API_URL
    ├── CACHE_URL
    ├── DATABASE_URL
    ├── DJANGO_ALLOWED_HOSTS
    ├── DJANGO_CONFIGURATION
    ├── DJANGO_DEBUG
    ├── DJANGO_SECRET_KEY
    ├── DJANGO_SETTINGS_MODULE
    ├── DJANGO_TEMPLATE_DEBUG
    ├── DJANGO_USE_CACHING
    ├── MAINTENANCE_MODE
    └── TESTING_FIREFOX_PATH


.. seealso::
    `dj-database-url`_ for the format of ```DATABASE_URL```
.. seealso::
    `django-cache-url`_ for the format of ```CACHE_URL```

.. _envdir: https://pypi.python.org/pypi/envdir
.. _dj-database-url: https://github.com/kennethreitz/dj-database-url
.. _django-cache-url: https://github.com/ghickman/django-cache-url


Django settings
---------------

Most of the settings are identical to the Django settings. Please refer
to the `Django documentation`_ for further information.

.. _Django documentation: https://docs.djangoproject.com/en/1.8/ref/settings/

Following environment variables must be set in order for django to run:

    * ```DJANGO_CONFIGURATION``` (for development: 'DevDefaultSite')
    * ```DJANGO_SETTINGS_MODULE``` (for develpment: 'apps.qcat.settings')
    * ```DATABASE_URL```
    * ```DJANGO_SECRET_KEY```


QCAT settings
-------------

``API_PAGE_SIZE``
^^^^^^^^^^^^^^^^^
Page size of results for the API providing questionnaire details.

``AUTH_API_KEY``
^^^^^^^^^^^^^^^^

``AUTH_API_TOKEN``
^^^^^^^^^^^^^^^^^^
The API token used for the authentication.

Default: ``None``

``AUTH_API_URL``
^^^^^^^^^^^^^^^^

``AUTH_API_USER``
^^^^^^^^^^^^^^^^^

``AUTH_COOKIE_NAME``
^^^^^^^^^^^^^^^^^^^^

``AUTH_LOGIN_FORM``
^^^^^^^^^^^^^^^^^^^

``DEPLOY_TIMEOUT``
^^^^^^^^^^^^^^^^^^
Timeout between announcement of deploy and actual maintenance window in seconds.

``ES_ANALYZERS``
^^^^^^^^^^^^^^^^

``ES_HOST``
^^^^^^^^^^^

``ES_INDEX_PREFIX``
^^^^^^^^^^^^^^^^^^^

``ES_NESTED_FIELDS_LIMIT``
^^^^^^^^^^^^^^^^^^^^^^^^^^

``ES_PORT``
^^^^^^^^^^^

``ES_QUERY_RESERVED_CHARS``
^^^^^^^^^^^^^^^^^^^^^^^^^^^
Some charactes have special meaning to ES queries.
https://www.elastic.co/guide/en/elasticsearch/reference/2.0/query-dsl-query-string-query.html#_reserved_characters

``GOOGLE_MAPS_JAVASCRIPT_API_KEY``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``GOOGLE_WEBMASTER_TOOLS_KEY``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``GRAPPELLI_ADMIN_TITLE``
^^^^^^^^^^^^^^^^^^^^^^^^^

``GRAPPELLI_INDEX_DASHBOARD``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``HOST_STRING_DEMO``
^^^^^^^^^^^^^^^^^^^^
Used for continuous delivery (fabric).

``HOST_STRING_DEV``
^^^^^^^^^^^^^^^^^^^
Used for continuous delivery (fabric).

``HOST_STRING_LIVE``
^^^^^^^^^^^^^^^^^^^^
Used for continuous delivery (fabric).

``IS_ACTIVE_FEATURE_MODULE``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Feature toggle for questionnaire-modules

``IS_ACTIVE_FEATURE_SUMMARY``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Feature toggle for summaries

``IS_ACTIVE_FEATURE_WATERSHED``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Feature toggle for questionnaire 'watershed'

``KEY_PREFIX``
^^^^^^^^^^^^^^

``LOCALE_PATHS``
^^^^^^^^^^^^^^^^

``LOGIN_URL``
^^^^^^^^^^^^^

``MAINTENANCE_LOCKFILE_PATH``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``MAINTENANCE_MODE``
^^^^^^^^^^^^^^^^^^^^
See https://github.com/shanx/django-maintenancemode

``NEXT_MAINTENANCE``
^^^^^^^^^^^^^^^^^^^^
See https://github.com/shanx/django-maintenancemode

``NOSE_ARGS``
^^^^^^^^^^^^^

``PIWIK_API_VERSION``
^^^^^^^^^^^^^^^^^^^^^

``PIWIK_AUTH_TOKEN``
^^^^^^^^^^^^^^^^^^^^

``PIWIK_SITE_ID``
^^^^^^^^^^^^^^^^^

``PIWIK_URL``
^^^^^^^^^^^^^

``REACTIVATE_WOCAT_ACCOUNT_URL``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

An URL to which users are redirected if the login failed because their account
is not yet activated. Background is that upon switching to the new WOCAT website
in 2017, all existing user accounts have to be reactivated manually.

Default: ``https://beta.wocat.net/accounts/reactivate/``

``REST_FRAMEWORK``
^^^^^^^^^^^^^^^^^^
Settings for: ``http://www.django-rest-framework.org/``

``SEND_MAILS``
^^^^^^^^^^^^^^


``SENTRY_DSN``
^^^^^^^^^^^^^^
See https://docs.sentry.io/clients/python/integrations/django/

``SUMMARY_PDF_PATH``
^^^^^^^^^^^^^^^^^^^^
Path to folder to store/'cache' created pdfs

``SWAGGER_SETTINGS``
^^^^^^^^^^^^^^^^^^^^
See https://django-rest-swagger.readthedocs.io/en/latest/

``TEMP_UNCCD_TEST``
^^^^^^^^^^^^^^^^^^^

``TESTING_FIREFOX_PATH``
^^^^^^^^^^^^^^^^^^^^^^^^

``THUMBNAIL_ALIASES``
^^^^^^^^^^^^^^^^^^^^^

``TOUCH_FILE_DEMO``
^^^^^^^^^^^^^^^^^^^
Location of uwsgi-touchfile, used for continuous delivery.

``TOUCH_FILE_DEV``
^^^^^^^^^^^^^^^^^^
Location of uwsgi-touchfile, used for continuous delivery.

``TOUCH_FILE_LIVE``
^^^^^^^^^^^^^^^^^^^
Location of uwsgi-touchfile, used for continuous delivery.

``UPLOAD_IMAGE_THUMBNAIL_FORMATS``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
A dictionary specifying the different thumbnail formats for images. For
every uploaded image, a thumbnail is created in each of the formats.

Example::

    UPLOAD_IMAGE_THUMBNAIL_FORMATS = {

        # '[NAME]': ([WIDTH], [HEIGHT])
        'header': (900, 300),

        'small': (200, 100),
    }


``UPLOAD_MAX_FILE_SIZE``
^^^^^^^^^^^^^^^^^^^^^^^^
An integer indicating the maximum file size for a single file upload.
In Bytes.

``UPLOAD_VALID_FILES``
^^^^^^^^^^^^^^^^^^^^^^
A dictionary indicating what file types are valid for upload and with
which extension they shall be saved.

Example::

    UPLOAD_VALID_FILES = {

        # 'TYPE': Used to group different types of files
        'image': (

            # ('[CONTENT_TYPE]', 'FILE_EXTENSION')
            ('image/jpeg', 'jpg'),
            ('image/png', 'png'),
            ('image/gif', 'gif'),
        ),
        'document': (
            ('application/pdf', 'pdf'),
        )
    }


``USE_NEW_WOCAT_AUTHENTICATION``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A boolean indicating whether to use the new (2017) WOCAT website as
authentication service or not.

Default: ``False``

``WARN_HEADER``
^^^^^^^^^^^^^^^
Text to display as warn header at the bottom of the page.

``WOCAT_IMPORT_DATABASE_URL``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``WORD_WRAP_LANGUAGES``
^^^^^^^^^^^^^^^^^^^^^^^
List of languages to add the css-attribute: word-wrap. Use this with languages
without spaces between words, such as Khmer.
