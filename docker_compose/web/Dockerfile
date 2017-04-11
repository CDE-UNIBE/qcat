FROM python:3.6

ENV PYTHONUNBUFFERED 1
RUN mkdir /code
RUN mkdir /entrypoint
WORKDIR /code

# Django-gis packages and dependencies for static assets
RUN apt-get update && apt-get install -y \
    binutils \
    libproj-dev \
    gdal-bin \
    nodejs \
    nodejs-legacy \
    npm \
    libmemcached-dev

ADD requirements/* /code/
RUN pip install -r development.txt
RUN pip install -r production.txt

ADD . /code/

# Change environment variables linking to other containers
ADD ./docker_compose/web/entrypoint.sh /entrypoint/entrypoint.sh
RUN chmod +x /entrypoint/entrypoint.sh
