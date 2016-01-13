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
    ├── AUTH_API_USER
    ├── AUTH_LOGIN_FORM
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
    ├── TESTING_FIREFOX_PATH
    └── WKHTMLTOPDF_CMD

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

.. _Django documentation: https://docs.djangoproject.com/en/1.7/ref/settings/

Following environment variables must be set in order for django to run:

    * ```DJANGO_CONFIGURATION``` (for development: 'DevDefaultSite')
    * ```DJANGO_SETTINGS_MODULE``` (for develpment: 'apps.qcat.settings')
    * ```DATABASE_URL```
    * ```DJANGO_SECRET_KEY```


QCAT settings
-------------

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


``WKHTMLTOPDF_CMD``
^^^^^^^^^^^^^^^^^^^

Path to the path of wkhtmltopdf. On unix system, execute
```which wkhtmltopdf```; also refer to the `offical wkhtmltopdf docs`_.

.. _offical wkhtmltopdf docs: https://pypi.python.org/pypi/django-wkhtmltopdf
