#!/bin/bash
# set envs according to docker-compose containers
mv /code/envs/DATABASE_URL /code/envs/DATABASE_URL.bak
mv /code/envs/ES_HOST /code/envs/ES_HOST.bak
mv /code/envs/CACHE_URL /code/envs/CACHE_URL.bak
echo "postgis://qcat@postgres:5432/qcat" > /code/envs/DATABASE_URL
echo "elasticsearch" > /code/envs/ES_HOST
echo "memcached://memcached:11211" > /code/envs/CACHE_URL

# prepare database and data
python manage.py migrate --noinput
python manage.py load_qcat_data
python manage.py loaddata technologies approaches cca watershed

# create static assets
npm install
bower install
grunt build:deploy --force
python manage.py collectstatic --noinput

# refresh elasticsearch
# python manage.py rebuild_es_indexes
exec "$@"
