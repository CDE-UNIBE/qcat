from os.path import join

from fabric.contrib.files import exists
from fabric.api import local, run, sudo
from fabric.colors import green, yellow

REPO_URL = 'https://github.com/CDE-UNIBE/qcat.git'


def provision():
    project_name = 'qcat'
    site_folder = '/srv/webapps/%s' % (project_name)
    source_folder = site_folder + '/source'
    _install_prerequirements()
    _create_directory_structure(site_folder)
    _get_latest_source(source_folder)
    print(yellow(
        "Provisioning completed. You may now create the local settings file!"))


def deploy():
    project_name = 'qcat'
    site_folder = '/srv/webapps/%s' % (project_name)
    source_folder = site_folder + '/source'
    _set_maintenance_mode(True, source_folder)
    _get_latest_source(source_folder)
    _update_virtualenv(source_folder)
    _clean_static_folder(source_folder)
    _update_static_files(source_folder)
    _update_database(source_folder)
    _set_maintenance_mode(False, source_folder)
    print(green("Everything OK"))


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
        run('git clone %s %s' % (REPO_URL, source_folder))
    current_commit = local("git log -n 1 --format=%H", capture=True)
    run('cd %s && git reset --hard %s' % (source_folder, current_commit))


def _update_virtualenv(source_folder):
    virtualenv_folder = source_folder + '/../virtualenv'
    if not exists(virtualenv_folder + '/bin/pip'):
        # Virtualenv does not yet exist
        run('virtualenv --python=python3 %s' % virtualenv_folder)
    run('%s/bin/pip3 install -r %s/requirements.txt'
        % (virtualenv_folder, source_folder))


def _clean_static_folder(source_folder):
    run('cd %s && rm -r static/*' % source_folder)


def _update_static_files(source_folder):
    run('cd %s && npm install' % source_folder)
    run('cd %s && bower install | xargs echo' % source_folder)
    run('cd %s && grunt build:deploy --force' % source_folder)
    run('cd %s && ../virtualenv/bin/python3 manage.py collectstatic --noinput'
        % (source_folder))


def _update_database(source_folder):
    run('cd %s && ../virtualenv/bin/python3 manage.py migrate --noinput'
        % (source_folder))
    run('cd %s && ../virtualenv/bin/python3 manage.py load_qcat_data'
        % (source_folder))


def _reload_apache(site_folder):
    run('cd %s && touch wsgi/wsgi.py' % site_folder)


def _set_maintenance_mode(value, source_folder):
    # Toggle maintenance mode on or off. This will reload apache!
    run('echo {bool_value} > {envs_file}'.format(
        bool_value=str(value),
        envs_file=join(source_folder, 'envs', 'MAINTENANCE_MODE')
    ))
