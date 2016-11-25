import contextlib
import urllib.request
from os.path import join, dirname

import envdir
import configurations
from fabric.context_managers import lcd
from fabric.contrib.files import exists
from fabric.api import local, run, sudo, env
from fabric.colors import green, yellow
from fabric.decorators import task, runs_once
from fabric.operations import require
from fabric.contrib import django
from django.conf import settings

# Load the django settings. This needs to read the env-variables and setup
# django-configurations, before the settings_module can be accessed.
envdir.read(join(dirname(dirname(__file__)), 'envs'))
configurations.setup()
django.settings_module('qcat.settings')


ENVIRONMENTS = {
    'develop': {
        'branch': 'develop',
        'label': 'dev',
        'host_string': settings.HOST_STRING_DEV,
        'touch_file': settings.TOUCH_FILE_DEV,
        'opbeat_url': settings.OPBEAT_URL_DEV,
        'opbeat_bearer': settings.OPBEAT_BEARER_DEV,
    },
    'demo': {
        'branch': 'master',
        'label': 'live',
        'host_string': settings.HOST_STRING_DEMO,
        'touch_file': settings.TOUCH_FILE_DEMO,
        'opbeat_url': settings.OPBEAT_URL_DEMO,
        'opbeat_bearer': settings.OPBEAT_BEARER_DEMO,
        'url': 'https://qcat-demo.wocat.net/{}/wocat/list/?type=all',
    },
    'master': {
        'branch': 'master',
        'label': 'live',
        'host_string': settings.HOST_STRING_LIVE,
        'touch_file': settings.TOUCH_FILE_LIVE,
        'opbeat_url': settings.OPBEAT_URL_LIVE,
        'opbeat_bearer': settings.OPBEAT_BEARER_LIVE,
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


def set_environment(environment_name):
    """
    Set the proper environment and all it's configured values.

    Args:
        environment_name: string - the dict key for ENVIRONMENTS

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
def deploy(branch):
    """
    Deploy the project.
    Execute with "fab <branch> deploy".
    """
    if branch not in BRANCH_HOSTINGS.keys():
        raise BaseException('{} is not a valid branch'.format(branch))

    for environment in BRANCH_HOSTINGS[branch]:
        set_environment(environment)
        _set_maintenance_mode(True, env.source_folder)
        _get_latest_source(env.source_folder)
        _update_virtualenv(env.source_folder)
        _clean_static_folder(env.source_folder)
        _update_static_files(env.source_folder)
        _update_database(env.source_folder)
        _set_maintenance_mode(False, env.source_folder)
        _rebuild_configuration_cache()
        print(green("Everything OK"))
        _access_project()


@task
def provision(environment):
    set_environment(environment)
    _install_prerequirements()
    _create_directory_structure(env.site_folder)
    _get_latest_source(env.source_folder)
    print(yellow("Provisioning completed. You may now create "
                 "the local settings file!"))


@task
def load_qcat_data(environment):
    set_environment(environment)
    run('cd {} && python manage.py load_qcat_data'.format(env.source_folder))


@task
def show_logs(environment, file='django.log', n=100):
    """
    Arguments can be passed like fab develop show_logs:file=myfile.log,n=1
    """
    set_environment(environment)
    run('tail -n {n} {folder}/logs/{file}'.format(n=n, folder=env.source_folder, file=file))


def _install_prerequirements():
    sudo('apt-get install apache2 git python3 python3-pip nodejs '
         'nodejs-legacy npm')
    sudo('npm install -g grunt-cli bower')
    sudo('pip3 install virtualenv')


def _create_directory_structure(site_folder):
    for subfolder in ('static', 'virtualenv', 'source'):
        run('mkdir -p %s/%s' % (site_folder, subfolder))


def _get_latest_source(source_folder):
    if exists(source_folder + '/.git'):
        # Repository already there, fetch new commits
        run('cd %s && git fetch' % (source_folder))
    else:
        # Create new repository
        run('git clone %s %s' % (env.repo_url, source_folder))
    # current_commit = local("git log -n 1 --format=%H", capture=True)
    # run('cd %s && git reset --hard %s' % (source_folder, current_commit))
    run('cd %s && git pull origin %s' % (source_folder, env.branch))


def _update_virtualenv(source_folder):
    virtualenv_folder = source_folder + '/../virtualenv'
    if not exists(virtualenv_folder + '/bin/pip'):
        # Virtualenv does not yet exist
        run('virtualenv --python=python3 %s' % virtualenv_folder)
    run('%s/bin/pip3 install -r %s/requirements/production.txt'
        % (virtualenv_folder, source_folder))


def _clean_static_folder(source_folder):
    run('cd %s && rm -r static/*' % source_folder)


def _update_static_files(source_folder):
    run('cd %s && npm install' % source_folder)
    run('cd %s && bower install | xargs echo' % source_folder)
    run('cd %s && grunt build:deploy --force' % source_folder)
    run('cd %s && ../virtualenv/bin/python3 manage.py collectstatic --noinput'
        % source_folder)
    run('cd %s && ../virtualenv/bin/python3 manage.py compress --force ' %
        source_folder)


def _update_database(source_folder):
    run('cd %s && ../virtualenv/bin/python3 manage.py migrate --noinput'
        % (source_folder))
    run('cd %s && ../virtualenv/bin/python3 manage.py load_qcat_data'
        % (source_folder))


def _reload_apache(site_folder):
    run('cd %s && touch wsgi/wsgi.py' % site_folder)


def _reload_uwsgi():
    """Touch the uwsgi-conf to restart the server"""
    run('touch {}'.format(env.touch_file))


def _set_maintenance_mode(value, source_folder):
    # Toggle maintenance mode on or off. This will reload apache!
    run('echo {bool_value} > {envs_file}'.format(
        bool_value=str(value),
        envs_file=join(source_folder, 'envs', 'MAINTENANCE_MODE')))
    # There were issues with permissions, so the lock-file remained in place.
    # Prevent this from happening again.
    if exists(settings.MAINTENANCE_LOCKFILE_PATH):
        run('rm {}'.format(settings.MAINTENANCE_LOCKFILE_PATH))
    _reload_uwsgi()


def _rebuild_configuration_cache():
    run('cd %s && ../virtualenv/bin/python3 manage.py build_config_caches' %
        env.source_folder)


def _access_project():
    """
    Call the homepage of the project for given branch if an url is set. This is a cheap way to fill the lru cache.
    """
    if hasattr(env, 'url'):
        for lang in settings.LANGUAGES:
            with contextlib.closing(urllib.request.urlopen(env.url.format(lang[0]))) as request:
                request.read()
                print('Read response from: {}'.format(request.url))


@task
@runs_once
def register_deployment(environment):
    """
    Call register_deployment with a local path that contains a .git directory
    after a release has been deployed.
    """
    set_environment(environment)
    local_project_folder = dirname(dirname(__file__))
    with(lcd(local_project_folder)):
        revision = local('git log -n 1 --pretty="format:%H"', capture=True)
        branch = local('git rev-parse --abbrev-ref HEAD', capture=True)
        local('curl https://intake.opbeat.com/api/v1/organizations/{}'
              ' -H "Authorization: Bearer {}"'
              ' -d rev="{}"'
              ' -d branch="{}"'
              ' -d status=completed'.format(env.opbeat_url,
                                            env.opbeat_bearer,
                                            revision,
                                            branch))
