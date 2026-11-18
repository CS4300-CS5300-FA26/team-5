# Deployment

Production target: [binge-and-bosses-team5](https://binge-and-bosses-team5-4e736711771e.herokuapp.com/), with PostgreSQL on Neon. The Heroku app and Neon project exist; the Neon database is empty and cutover is pending. The old Render database is disposable, so no data transfer is planned.

## CI deployment

`.github/workflows/ci.yaml` runs the test job on pushes and pull requests. After the test job passes on a push to `main`, the deploy job checks out that exact commit and pushes it to the Heroku Git `main` branch over HTTPS. GitHub Actions uses the `heroku-production` environment and its `HEROKU_API_KEY` secret. Deploys to this app are serialized. This uses Git directly; it does not require the Heroku CLI or a GitHub deployment App.

The root `.python-version` and `uv.lock` are the Python buildpack's runtime and dependency files. Keep `uv.lock` as the only package-manager lock or requirements file in the repository; the buildpack rejects multiple package-manager files. Heroku finds `binge_and_bosses/manage.py` and runs `collectstatic` during the build. WhiteNoise serves the collected files.

## Processes and database

The root [Procfile](../Procfile) declares the web process and a release command. The web process runs Gunicorn and binds to Heroku's `PORT`. The release command applies Django migrations with `--noinput` on each deployment.

The Heroku app needs these config vars:

- `SECRET_KEY`, `IGDB_CLIENT_ID` and `IGDB_CLIENT_SECRET` (all required at startup; CI's dummy values can't make real IGDB requests)
- `DEBUG=False`
- `ALLOWED_HOSTS` containing `binge-and-bosses-team5-4e736711771e.herokuapp.com`
- `CSRF_TRUSTED_ORIGINS` containing `https://binge-and-bosses-team5-4e736711771e.herokuapp.com`
- `DATABASE_URL` set to the Neon PostgreSQL connection string with SSL enabled

Keep credentials in Heroku config vars, never in the repository or local test `.env` files. The first release migration creates the schema in the empty Neon database. No Render data migration is needed.

## Production smoke test

After the push, the deploy job runs `.github/scripts/smoke-test-production.sh`. `git push` returns while the release command (migrations) is still running, and the old release keeps serving until it finishes. So the script first waits for the Heroku API to show the pushed commit as the current release. It fails if that release fails or isn't live within 10 minutes. Then it checks that the home page, login, sign-up and the home page's stylesheet return 200, and that the pages show the expected text. It retries for up to 2 minutes while the dynos restart. Any failed check fails the deploy job with an error annotation. If the push step skips a stale deployment, the smoke test is skipped too.

To run it locally, set `HEROKU_API_KEY`, `HEROKU_APP`, `APP_URL` (no trailing slash) and `EXPECTED_SHA` (the deployed commit), then run the script.
