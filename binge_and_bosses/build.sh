#!/usr/bin/env bash
# -------------------------------
# Script used to build on render
# -------------------------------

set -o errexit
PROJ_DIR=binge_and_bosses



pip install -r requirements.txt

python3 $PROJ_DIR/manage.py collectstatic --no-input
python3 $PROJ_DIR/manage.py migrate
python3 $PROJ_DIR/manage.py createsuperuser --no-input || true
