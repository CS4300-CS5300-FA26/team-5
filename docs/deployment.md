# Deployment

Production is at [binge-and-bosses.onrender.com](https://binge-and-bosses.onrender.com/), on [Render](https://render.com)'s free tier, built from this repo's `main` branch. `\.github\workflows\ci.yaml` contains the specific job that checks if the push passes all the CI checks, and only if it does will it allow a deployment to our website on Render.

## What a deploy does
Render runs [build.sh](../binge_and_bosses/build.sh) from the repository root. It:

1. Installs the packages in `requirements.txt`. That file is generated from `uv.lock`, so production gets the same app package versions as CI and your machine, without dev packages. Render doesn't use uv itself.
2. Collects static files (CSS, images) into `staticfiles/`, which WhiteNoise serves.
3. Applies database migrations.
4. Tries to create the admin superuser. The build continues if that command fails, including when the user already exists.

Then Render starts the site with the start command set in its dashboard (gunicorn is in `requirements.txt` for this).

If you add a model, commit its migration. `build.sh` applies it on the next deploy.

## Settings in production
Render supplies the same environment variables as your local `.env` (see the table in [Project layout](project-layout.md#settings-come-from-the-environment)). Set them in the Render dashboard, never in code.

`SECRET_KEY` and `RAWG_API_KEY` are required even at startup. Keep `DEBUG=False` in production. CI's dummy keys are only for tests; they can't make real RAWG requests work.
`RENDER_DEPLOY_HOOK_URL` is already stored within the repository so it is not needed to add to you `.env`

## Free-tier behavior to know about
- **The site sleeps after 15 minutes without visitors.** The next visit takes about a minute while it wakes up. That's expected, not a crash.
- **Files written on the server are lost** on every deploy, restart, or sleep. Anything that must be kept goes in the database.
- **Which database production uses is an open question**, tracked in #53. If `DATABASE_URL` isn't set, production falls back to SQLite on that wiped disk.

- **Smoke test after each deploy** (#35, Sprint 2).
- **Custom domain** (#39, Sprint 3). Must be a domain we own, not a subdomain.
