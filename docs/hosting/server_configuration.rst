Hosting
=======

This chapter describes the setup on the servers that host this project. This
project can be run on any kind of setup that supports wsgi, the following
information describes one possible implementation. All configuration files are
stored in the folder ``serverconfig``.


Architecture
------------
`Apache`_ is used as `reverse proxy`_; `uwsgi`_ serves the application itself.


Apache
^^^^^^
The configuration from ``serverconfig/apache_<environment>.conf`` may directly
be used as symlink in your allowed hosts. This configuration is built on Apache
version 2.4.7 and ensures that:

* All traffic is redirected to use HTTPS
* The communication with the application server is handled with a socket file

Following Apache modules must be enabled:

* a2enmod proxy
* a2enmod rewrite
* a2enmod deflate
* a2enmod headers

The Apache server may be replaced with `nginx`_, if traffic increases heavily.


Uwsgi
^^^^^
This is the actual application server (`see uwsgi docs`_). It should be run in
the emperor/tyrant mode. This configuration is built for uwsgi version 2.0.12.

A sample configuration for this application:

* Emperor: adapt the script: ``serverconfig/uwsgi_emperor.conf`` and create a
  new file in /etc/init.

* Vassals: Symlink (``serverconfig/uwsgi_<environment>.conf``) in the folder
  that is ruled by your emperor.

.. _Apache: https://httpd.apache.org/
.. _reverse proxy: https://httpd.apache.org/docs/2.4/mod/mod_proxy.html
.. _see uwsgi docs: http://uwsgi-docs.readthedocs.org/
.. _nginx: http://nginx.org/en/
