web: gunicorn --chdir binge_and_bosses --bind 0.0.0.0:$PORT binge_and_bosses.wsgi
release: python binge_and_bosses/manage.py migrate --noinput
