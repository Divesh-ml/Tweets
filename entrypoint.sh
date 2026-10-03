#!/bin/sh
set -eu

cd /app
python manage.py migrate --noinput
exec "$@"
