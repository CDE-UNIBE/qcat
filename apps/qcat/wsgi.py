"""
WSGI config for qcat project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/dev/howto/deployment/wsgi/
"""
import sys
import envdir
from os.path import join, dirname, abspath

# Root directory for this project
QCAT_DIR = dirname(dirname(dirname(abspath(__file__))))

# Add the apps folder to the path and read the env-vars.
sys.path.append(join(QCAT_DIR, 'apps'))
envdir.read(join(QCAT_DIR, 'envs'))

# Load the wsgi application with django-configurations.
from configurations.wsgi import get_wsgi_application
application = get_wsgi_application()
