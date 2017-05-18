import contextlib
import os
import time
import urllib.request

import envdir
import configurations

from fabric.context_managers import cd, prefix
from fabric.contrib.files import exists
from fabric.api import run, env
from fabric.colors import green
from fabric.decorators import task, runs_once, parallel
from fabric.contrib import django
from fabric.tasks import execute
from django.conf import settings

# Load the django settings. This needs to read the env-variables and setup
# django-configurations, before the settings_module can be accessed.
envdir.read(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'envs'))
configurations.setup()
django.settings_module('qcat.settings')


ENVIRONMENTS = {
    'develop': {
        'branch': 'develop',
        'label': 'dev',
        'host_string': settings.HOST_STRING_DEV,
        'touch_file': settings.TOUCH_FILE_DEV,
        'use_deploy_announcement': False
    },
    'demo': {
        'branch': 'master',
        'label': 'live',
        'host_string': settings.HOST_STRING_DEMO,
        'touch_file': settings.TOUCH_FILE_DEMO,
        'use_deploy_announcement': False,
        'url': 'https://qcat-demo.wocat.net/{}/wocat/list/?type=all',
    },
    'master': {
        'branch': 'master',
        'label': 'live',
        'host_string': settings.HOST_STRING_LIVE,
        'touch_file': settings.TOUCH_FILE_LIVE,
        'use_deploy_announcement': True,
        'url': 'https://qcat.wocat.net/{}/wocat/list/?type=all',
    },
    'common': {
        'project_name': 'qcat',
        'repo_url': 'https://github.com/CDE-UNIBE/qcat.git',
        'base_path': '/srv/webapps',
    }
}

# Mapping of branches and the hosts on which these branches are checked out
BRANCH_HOSTINGS = {
    'develop': ['develop'],
    'master': ['master', 'demo'],
}
# set this tag to the latest commit to reload config and rebuild cache during
# the deploy.
REBUILD_CONFIG_TAG = 'rebuild_config'


def set_environment(environment_name):
    """
    Setup given environment and all its configured values.
    """
    # Put values from configuration to environment.
    env.environment = environment_name
    for configuration in [environment_name, 'common']:
        for option, value in ENVIRONMENTS[configuration].items():
            setattr(env, option, value)

    # Set attributes that are combined based on the configuration.
    site_folder = '{base_path}/{project_name}-{label}'.format(
        base_path=env.base_path,
        project_name=env.project_name,
        label=env.label,
    )
    setattr(env, 'site_folder', site_folder)
    setattr(env, 'source_folder', '{}/source'.format(site_folder))


@task
@runs_once
def deploy(branch):
    """
    Execute with "fab deploy:<branch>". This will deploy the branch to the hosts
    set in BRANCH_HOSTINGS
    """
    if branch not in BRANCH_HOSTINGS.keys():
        raise BaseException('{} is not a valid branch'.format(branch))

    for environment in BRANCH_HOSTINGS[branch]:
        print('deploying %s' % environment)
        # use execute, so task can run in parallel.
        execute(
            task=deploy_host,
            environment=environment
        )


@task
def show_logs(environment_name, file='django.log', n=100):
    """
    Arguments can be passed like fab develop show_logs:file=myfile.log,n=1
    """
    set_environment(environment_name)
    run('tail -n {n} {folder}/logs/{file}'.format(
        n=n, folder=env.source_folder, file=file)
    )


@parallel
def deploy_host(environment):
    set_environment(environment)
    if env.use_deploy_announcement:
        _set_maintenance_warning()

    _set_maintenance_mode(True)
    _get_latest_source()
    _update_virtualenv()
    _clean_static_folder()
    _update_static_files()
    _update_database()
    if _has_config_update_tag():
        _reload_configuration_fixtures()
        _delete_caches()
        _reload_uwsgi()
        _rebuild_elasticsearch_indexes()
        _purge_summary_pdfs()
    _set_maintenance_mode(False)

    print(green("Everything OK"))
    _access_project()
    _clean_sessions()


def _get_latest_source():
    with cd(env.source_folder):
        run('git fetch')
        run('git pull origin %(branch)s' % env)
        run('git fetch --tags')


def _update_virtualenv():
    with virtualenv():
        run('pip3 install -r requirements/production.txt')


def _clean_static_folder():
    with cd(env.source_folder):
        run('rm -r static/*')


def _update_static_files():
    with cd(env.source_folder):
        run('npm install &>/dev/null')
        run('bower install | xargs echo')
        run('grunt build:deploy --force')

    _manage_py('collectstatic --noinput')
    _manage_py('compress --force')


def _update_database():
    _manage_py('migrate --noinput')
    _manage_py('load_qcat_data')


def _has_config_update_tag():
    with cd(env.source_folder):
        git_tags = run('git tag -l --points-at HEAD')
        return git_tags.stdout.startswith(REBUILD_CONFIG_TAG)

    return False


def _reload_configuration_fixtures():
    _manage_py('loaddata technologies approaches cca watershed')


def _delete_caches():
    _manage_py('delete_caches')


def _rebuild_elasticsearch_indexes():
    _manage_py('rebuild_es_indexes')


def _purge_summary_pdfs():
    with cd(env.site_folder):
        # -f suppresses error when folder is empty
        run('rm -f upload/summary-pdf/*')


def _reload_uwsgi():
    """Touch the uwsgi-conf to restart the server"""
    run('touch %(touch_file)s' % env)


def _set_maintenance_mode(value):
    # Toggle maintenance mode on or off. This will reload apache!
    run('echo {bool_value} > {envs_file}'.format(
        bool_value=str(value),
        envs_file=os.path.join(env.source_folder, 'envs', 'MAINTENANCE_MODE')))
    # There were issues with permissions, so the lock-file remained in place.
    # Prevent this from happening again.
    if exists(settings.MAINTENANCE_LOCKFILE_PATH):
        run('rm {}'.format(settings.MAINTENANCE_LOCKFILE_PATH))
    _reload_uwsgi()


def _access_project():
    """
    Call the homepage of the project for given branch if an url is set. This is a cheap way to fill the lru cache.
    """
    if hasattr(env, 'url'):
        # wait for uwsgi-restart after touch.
        time.sleep(10)
        for lang in settings.LANGUAGES:
            url = urllib.request.urlopen(env.url.format(lang[0]))
            with contextlib.closing(url) as request:
                request.read()
                print('Read response from: {}'.format(request.url))


def _set_maintenance_warning():
    """
    Activate the maintenance warning and wait until the deploy timeout is over,
    giving people the chance to save their work.
    This is a brute method, but deploying without a maintenance is not an option
    at this time, as some tasks (configuration and cache rebuilding) are not
    always required and are built on human interaction. They also are relatively
    expensive and don't need to be executed on each deploy.
    """
    _manage_py('set_next_maintenance')
    time.sleep(settings.DEPLOY_TIMEOUT)


def _clean_sessions():
    """
    This should be in a crontab.
    """
    _manage_py('clearsessions')


def _manage_py(command):
    with virtualenv():
        run('python3 manage.py %s' % command)


@contextlib.contextmanager
def virtualenv():
    with prefix('source %(site_folder)s/virtualenv/bin/activate' % env):
        with cd(env.source_folder):
            yield
