Installation and Setup 
======================

Requirements
------------

The qcat application needs a whole range of server applications:

* Apache webserver
* Postgresql >= 9.4 with postgis extension
* uwsgi: application server for python web applications together
* elasticsearch: search engine based on Lucene
* memcached:  Memory caching

Postgresql
..........

Postgresql 9.4 or bigger is needed as JSONP is used. Postgis 2.1 or bigger is needed as well.


uwsgi
.....

uwsgi is needed at least in version 2.x or bigger. In the following explanations we use uwsgi in emperor mode.
Furthermore uwsgi needs the python3 plugin and apache needs the uwsgi-proxy module::

	apt-get install uwsgi-emperor uwsgi-plugin-python3 libapache2-mod-proxy-uwsgi


Other required packages
........................

::

	sudo apt-get install python3-pip  python3-psycopg2 libpg-dev python3-pil memcached libmemcached-dev nodejs nodejs-legacy npm


wkhtmltopdf: a version with patched QT is required. Get the current stable version at http://wkhtmltopdf.org/downloads.html ::

    cd /tmp
    wget <download_file>
    sudo tar xvf wkhtmltox-0.12.3_linux-generic-amd64.tar.xz
    sudo mv wkhtmltox/bin/wkhtmlto* /usr/bin


Installation
------------

Backend installation
......................


#. Creating user 'qcat'::

	sudo adduser qcat && addgroup qcat:qcat

#. Create the application folder::

	sudo mkdir qcat-live
	chown qcat:qcat qcat-live

#. Install virtualenv::

	sudo pip3 install virtualenv

#. Now change privileges to user 'qcat'::

	sudo -u qcat -i
	cd qcat-live

#. Get the application from the github repository::

	git clone https://github.com/CDE-UNIBE/qcat.git source

#. Create virtualenv and activate it::

	virtualenv -p python3 virtualenv
	source virtualenv/bin/activate

#. Install all requirements python requirements for the application::

	cd source
	pip3 install -r requirements/production.txt

#. Now we are ready to install the system based stuff. This is done with fabric from another computer::

	fab deploy_demo

#. Now we can try, if the Django applicatio is valid::

	cd qcat-live/source
	python3 manage.py validate


Frontend installation
.....................

#. Change to project folder and use NPM to install Bower and Grunt::

	cd qcat-live/source
	npm install -g grunt-cli bower

#. Install the project dependencies::

	npm install

#. Change to qcat user and let Bower collect the required libraries::

	bower install

#. Use Grunt to build the static files::

	grunt build










