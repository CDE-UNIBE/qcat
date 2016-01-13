Installation
============

This section covers the installation of QCAT for local development. For
instructions on how to deploy QCAT to a server, refer to the
`Deployment`_ section.

.. _Deployment: deployment.html


Prerequisites
-------------

The following prerequisites are needed. Make sure to have them installed
on your system.

Python 3
^^^^^^^^

QCAT is written in `Python 3`_, which is already installed on many
operating systems.

Git
^^^

The source code of QCAT is managed in `Git`_, a free and open source
distributed version control system.

PostgreSQL
^^^^^^^^^^

`PostgreSQL`_ is the database management system behind QCAT. In order to
install QCAT, you need to create a database first and install the
`PostGIS`_ extension for this database.

.. important::
    At least version 9.4 of PostgreSQL is needed as support of the
    JSON-B data type is required.

.. _Python 3: http://python.org/
.. _Git: http://git-scm.com/
.. _PostgreSQL: http://www.postgresql.org/
.. _PostGIS: http://postgis.net/


Elasticsearch
^^^^^^^^^^^^^

`Elasticsearch`_ is used as a search engine to query the questionnaires.

.. seealso::
    :doc:`/development/elasticsearch`

.. _Elasticsearch: https://www.elastic.co/products/elasticsearch


wkhtmltopdf
^^^^^^^^^^^

`wkhtmltopdf`_ is used to create pdf files. This must be installed, as well
as ``libfontconfig``. Make sure to install the latest release from the offical
page, instead of the version in your package manager.

.. _wkhtmltopdf: http://wkhtmltopdf.org/


Installation on a UNIX system
-----------------------------

These instructions will take you through the process of installing QCAT
on your computer, assuming that you are running a UNIX system (for
example Ubuntu). The package `virtualenvwrapper`_ is highly recommended.


.. _virtualenvwrapper: http://virtualenvwrapper.readthedocs.org/en/latest/

Preparation
^^^^^^^^^^^

Create a folder for the project and create a virtual environment in it::

    $ mkproject qcat

Get the code::

    $ git clone https://github.com/CDE-UNIBE/qcat.git .

The custom packages for this application are in the folder ```apps```. This
directory must be added to your virtualenv::

    $ add2virtualenv apps/

This command must be executed in the root directory of your activated virtual
environment.

Installation: Application
^^^^^^^^^^^^^^^^^^^^^^^^^

Switch to the source folder, activate the virtual environment and
install the dependencies for the development environment::

    $ cd qcat
    $ source ../env/bin/activate
    (env)$ pip3 install -r requirements/development.txt

.. hint::
    If the installation of the requirements produces errors concerning
    psycopg2, make sure you have the ``python3-dev`` package installed::

        sudo apt-get install python3-dev

Create and set up a database (with PostGIS extension).

Make sure that all required environment variables are set as described in
:doc:`/configuration/settings`

.. hint::
    Authentication happens against the WOCAT user database, an API key
    is needed for this.

Let Django create the database tables for you::

    (env)$ python3 manage.py migrate

..
    Collect the static files needed by Django::

        (env)$ python3 manage.py collectstatic


Load the initial data of QCAT::

    (env)$ python3 manage.py load_qcat_data


Installation: Static files
^^^^^^^^^^^^^^^^^^^^^^^^^^

The static files (such as CSS or JavaScript files and libraries) are
managed using `Bower`_ and `GruntJS`_, both requiring the `NodeJS`_
platform.

.. _Bower: http://bower.io/
.. _GruntJS: http://gruntjs.com/
.. _NodeJS: http://nodejs.org/

Install NodeJS and its package manager::

    sudo apt-get install nodejs nodejs-legacy npm

Use NPM to install Bower and Grunt::

    sudo npm install -g grunt-cli bower

Install the project dependencies::

    sudo npm install

Let Bower collect the required libraries::

    bower install

Use Grunt to build the static files::

    grunt build

.. hint::
    See the documentation on :doc:`grunt` for additional grunt commands.


Run
^^^

Run the application::

    (env)$ python3 manage.py runserver

Open your browser and go to http://localhost:8000 to see if everything
worked.

.. important::
    You need to set up Elasticsearch for QCAT to work properly. If you
    are logged in as an administrator, there is an entry in the user
    menu allowing you to create and update the Elasticsearch indices.

    .. seealso::
        :doc:`/development/elasticsearch`
