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
- `REDIS_URL` set to a Redis service reachable from Heroku, using the provider's full connection URL (including TLS and authentication when required). The local Compose container only serves local development.
- `REDIS_SSL_VERIFY=False` for Heroku Key-Value Store only: it uses self-signed certificates. TLS encryption remains enabled through `rediss://`, but this setting disables server certificate verification. Other providers default to certificate verification; do not disable it when trusted certificates are available.
- `DATABASE_URL` set to the Neon PostgreSQL connection string with SSL enabled

On Heroku the site is HTTPS only. Heroku sets `DYNO` on every dyno, so when it's set, `settings.py` redirects `http://` to `https://` and marks the session and CSRF cookies secure. Local runs don't set `DYNO`, so they stay on plain HTTP. HSTS is still off.

Keep credentials in Heroku config vars, never in the repository or local test `.env` files. The first release migration creates the schema in the empty Neon database. No Render data migration is needed.

## Production smoke test

After the push, the deploy job runs `.github/scripts/smoke-test-production.sh`. `git push` returns while the release command (migrations) is still running, and the old release keeps serving until it finishes. So the script first waits for the Heroku API to show the pushed commit as the current release. It fails if that release fails or isn't live within 10 minutes. Then it checks that the home page, login, sign-up and the home page's stylesheet return 200, and that the pages show the expected text. It retries for up to 2 minutes while the dynos restart. Any failed check fails the deploy job with an error annotation. If the push step skips a stale deployment, the smoke test is skipped too.

To run it locally, set `HEROKU_API_KEY`, `HEROKU_APP`, `APP_URL` (no trailing slash) and `EXPECTED_SHA` (the deployed commit), then run the script.

## Production Redis setup and smoke check

Before merging the Redis branch, provision Heroku Key-Value Store on `binge-and-bosses-team5`. Confirm the add-on has finished provisioning and that its managed `REDIS_URL` starts with `rediss://`. Keep the connection string in Heroku, never in Git or shared logs. In the app's Settings > Config Vars, set `REDIS_SSL_VERIFY=False` for Heroku KVS, following [Heroku's built-in Django backend instructions](https://devcenter.heroku.com/articles/connecting-heroku-redis#using-the-built-in-redis-backend-support). Do not change the managed URL or copy the production credentials into local `.env`.

With `DEBUG=False`, an absent or blank `REDIS_URL` now stops startup with a configuration error, including during builds. Provision/configure Redis before deploying. Local development with `DEBUG=True` retains the localhost fallback and does not receive TLS-only options. The Redis service in `compose.yaml` is local only; Heroku deploys the Python app through the existing Procfile.

After the PR is approved, merged, and deployed by CI, open a one-off Django shell (requires the Heroku CLI and access to the app):

```bash
heroku run --app binge-and-bosses-team5 python binge_and_bosses/manage.py shell
```

Run the following without printing credentials or cached access tokens:

```python
from uuid import uuid4
from django.core.cache import cache

key = f"deployment_check:{uuid4().hex}"
try:
    cache.set(key, "connected", timeout=30)
    assert cache.get(key) == "connected"
    print("Production Redis write/read passed")
finally:
    cache.delete(key)
```

Then check login, library, game search, and game details on the production URL. Record the deployed commit and outcomes before calling the deployment smoke test complete. A successful CI run uses fake upstream responses and isolated caches; it does not establish a live production Redis connection. Redis outages can still fail game requests; cache-outage fallback is separate work.



