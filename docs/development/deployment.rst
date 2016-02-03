Deployment
==========

While it is perfectly fine to deploy QCAT manually, it comes with a
script which allows automatic deployment. This is especially helpful for
developers to update the server with a single command.

The following section covers the automatic deployment with a Python
library called `Fabric`_.


Install Fabric
--------------

`Fabric`_ is not part of the requirements of the application and needs
to be installed separately. At the time of writing, Fabric is not yet
ported to Python 3. ::

    (env)$ pip2 install fabric

If pip2 is not available, install fabric outside of the virtual
environment.


Process
-------

* Changes are always commited to feature branches.
* The `git-flow`_ model is in use.
* Only Selected people from the CDE (Centre for Development and Environment) can
  merge commits into the branches ``develop`` and ``master``.
* `Shippable`_ is monitoring these branches, new commits trigger a deployment.
* The configuration for shippable is stored in the file: ``shippable.yml``
  * The host string is a secure value, which be generated on the platform.
  * Before the actual deployment is started, all tests are run.
  * If no tests fail, the deployment is started.
* Deployment is handled with Fabric.
* For the git branches develop and master, respective environments are created.
* Manual deployment should be avoided.

.. _git-flow: http://nvie.com/posts/a-successful-git-branching-model/
.. _Shippable: http://www.shippable.com


Provision
---------

    .. warning::
        The following steps need to be done only once for each server
        but nothing should break if you run the command several
        repeatedly.

In order to prepare the server for deployment, you need to create a user
with the appropriate rights on the host server and create a folder for
the app to live in. The script assumes the application will live in
``/srv/webapps/qcat/``. Then run the following command::

    (env)$ fab provision -H [user]@[server]

This will install the required software, create the folder structures
for the app and get the latest source of the app from its repository.

You will then have to create the environment variables and set the database
connection and adapt other settings: :doc:`/configuration/settings`


Deploy
------

To deploy the latest code to the server, use the following command::

    (env)$ fab <environment> deploy -H [user]@[server]

If needed, add and enable the site in Apache.

.. _Fabric: http://www.fabfile.org/


Update recipes
--------------

Update server and reset database
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

#. Delete the database tables.

#. Run the update script::

    [local] (env)$ fab deploy -H user@server

#. In Search Index Administration panel, delete all caches.

#. On the server, load the fixtures::

    [server] (env)$ python3 manage.py loaddata wocat.json

#. In Search Index Aministration panel: delete and recreate indices.

#. Eventually load data from Search Index Administration panel.


Update server
^^^^^^^^^^^^^

#. Run the update script::

    [local] (env)$ fab deploy -H user@server

#. In Search Index Administration panel, delete all caches.

#. On the server, load the fixtures::

    [server] (env)$ python3 manage.py loaddata wocat.json

#. In Search Index Aministration panel: delete, recreate and **update** indices.
