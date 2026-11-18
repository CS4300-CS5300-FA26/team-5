# Deployment

Production target: [bingeandbosses.com](https://bingeandbosses.com) (also `www.bingeandbosses.com`), served by the Heroku app [binge-and-bosses-team5](https://binge-and-bosses-team5-4e736711771e.herokuapp.com/), with PostgreSQL on Neon. The Heroku app and Neon project exist; the Neon database is empty and cutover is pending. The old Render database is disposable, so no data transfer is planned.

## CI deployment

`.github/workflows/ci.yaml` runs the test job on pushes and pull requests. After the test job passes on a push to `main`, the deploy job checks out that exact commit and pushes it to the Heroku Git `main` branch over HTTPS. GitHub Actions uses the `heroku-production` environment and its `HEROKU_API_KEY` secret. Deploys to this app are serialized. This uses Git directly; it does not require the Heroku CLI or a GitHub deployment App.

The root `.python-version` and `uv.lock` are the Python buildpack's runtime and dependency files. Keep `uv.lock` as the only package-manager lock or requirements file in the repository; the buildpack rejects multiple package-manager files. Heroku finds `binge_and_bosses/manage.py` and runs `collectstatic` during the build. WhiteNoise serves the collected files.

## Processes and database

The root [Procfile](../Procfile) declares the web process and a release command. The web process runs Gunicorn and binds to Heroku's `PORT`. The release command applies Django migrations with `--noinput` on each deployment.

The Heroku app needs these config vars:

- `SECRET_KEY`, `IGDB_CLIENT_ID` and `IGDB_CLIENT_SECRET` (all required at startup; CI's dummy values can't make real IGDB requests)
- `DEBUG=False`
- `ALLOWED_HOSTS` containing `bingeandbosses.com`, `www.bingeandbosses.com` and `binge-and-bosses-team5-4e736711771e.herokuapp.com`
- `CSRF_TRUSTED_ORIGINS` containing `https://bingeandbosses.com`, `https://www.bingeandbosses.com` and `https://binge-and-bosses-team5-4e736711771e.herokuapp.com`
- `DATABASE_URL` set to the Neon PostgreSQL connection string with SSL enabled

On Heroku the site is HTTPS only. Heroku sets `DYNO` on every dyno, so when it's set, `settings.py` redirects `http://` to `https://` and marks the session and CSRF cookies secure. Local runs don't set `DYNO`, so they stay on plain HTTP. HSTS is still off.

Keep credentials in Heroku config vars, never in the repository or local test `.env` files. The first release migration creates the schema in the empty Neon database. No Render data migration is needed.

## Cutover checklist

Deployment and the production smoke test remain pending. After the CI deploy succeeds, verify the Heroku release and check the site, sign-up, login, and static files at the production URL before treating cutover as complete.
