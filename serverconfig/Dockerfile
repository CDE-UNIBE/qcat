# Same version as on the servers
FROM ubuntu:14.04

MAINTAINER Sebastian Manger <sebastian.manger@cde.unibe.ch>

ENV POSTGRES 9.4
ENV POSTGIS 2.1

# Sources for postgres 9.4 and postgis 2.1.
RUN sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt trusty-pgdg main" \
    >> /etc/apt/sources.list'
RUN apt-get install -y software-properties-common

# Sources for elasticsearch and required java version (oracle java 8).
RUN add-apt-repository -y ppa:webupd8team/java
RUN apt-get update
RUN echo "oracle-java8-installer shared/accepted-oracle-license-v1-1 select true" | \
    debconf-set-selections && apt-get install -y oracle-java8-installer
RUN apt-get -y install oracle-java8-installer

# Sources for postgis.
RUN apt-get update && apt-get -y install wget
RUN wget --quiet -O - http://apt.postgresql.org/pub/repos/apt/ACCC4CF8.asc | \
    sudo apt-key add -

# Sources for elasticsearch
RUN wget -qO - https://packages.elastic.co/GPG-KEY-elasticsearch | sudo apt-key add -
RUN echo "deb http://packages.elastic.co/elasticsearch/2.x/debian stable main" | \
    sudo tee -a /etc/apt/sources.list.d/elasticsearch-2.x.list

# Install packages; curl and lynx-curl are for debugging within docker.
RUN apt-get update && apt-get -y upgrade
RUN DEBIAN_FRONTEND=noninteractive apt-get -qq -y --force-yes install \
    curl \
    nodejs \
    nodejs-legacy \
    npm \
    git \
    postgresql-$POSTGRES \
    postgresql-client-$POSTGRES \
    postgresql-$POSTGRES-postgis-$POSTGIS \
    postgresql-contrib-$POSTGRES \
    elasticsearch \
    python-psycopg2 \
    xvfb \
    --fix-missing

# Configure postgres and enable postgis.
ADD serverconfig/postgresql.conf /etc/postgresql/$POSTGRES/main/postgresql.conf
ADD serverconfig/pg_hba.conf /etc/postgresql/$POSTGRES/main/pg_hba.conf
RUN service postgresql restart
# RUN sudo -u postgres psql -c "CREATE EXTENSION postgis;"

# Elasticsearch: load configuration and start service.
ADD serverconfig/elasticsearch.yml /etc/elasticsearch/
RUN service elasticsearch restart
