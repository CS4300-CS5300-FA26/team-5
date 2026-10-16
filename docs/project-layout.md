# Project layout

```
team-5/
├── binge_and_bosses/          ← the Django project; run manage.py commands from here
│   ├── manage.py
│   ├── build.sh               ← what Render runs on each deploy (see deployment.md)
│   ├── binge_and_bosses/      ← project settings and top-level URLs
│   │   ├── settings.py
│   │   └── urls.py
│   ├── authentication/        ← accounts: custom User model, sign-up, log-in
│   │   ├── models.py          ← User (settings.AUTH_USER_MODEL)
│   │   ├── views.py           ← signup view; log-in/out come from Django
│   │   ├── urls.py            ← everything under /accounts/
│   │   └── templates/registration/
│   └── games/                 ← the "games" app
│       ├── models.py          ← Game model
│       ├── views.py           ← index view (the home page)
│       ├── urls.py
│       ├── templates/games/index.html
│       ├── migrations/        ← committed; never delete or edit by hand
│       └── tests.py
├── .github/
│   ├── workflows/ci.yaml          ← tests + coverage on every push and PR
│   ├── workflows/ai-review.yml    ← AI review comment on every PR
│   ├── ai-review-guide.md         ← what the AI reviewer looks for
│   └── scripts/                   ← the AI review script and its tests
├── docs/                      ← you are here
├── pyproject.toml             ← the packages we depend on (edit with `uv add`)
├── uv.lock                    ← exact pinned versions of every package; commit it
├── .python-version            ← Python version (3.12)
├── requirements.txt           ← generated from uv.lock for Render; never edit by hand
└── README.md                  ← setup, running, adding packages, AI usage log
```

## How a page gets to the browser
Using the home page as the example:

1. `binge_and_bosses/urls.py` sends `/` to the games app's `urls.py`.
2. `games/urls.py` sends `""` to `views.index`.
3. `views.index` loads every `Game` from the database.
4. It renders `games/index.html` with those games.

New features follow the same path: URL → view → model → template.

## Users
Always refer to the user model as `settings.AUTH_USER_MODEL` (in model fields) or `get_user_model()` (in code), never `django.contrib.auth.models.User`. We use our own `authentication.User`, so Django's built-in one isn't the one in the database.

## Adding a new app
Django apps group one area of the site (games, accounts, reviews, …).

```bash
cd binge_and_bosses
uv run python manage.py startapp <name>
```

Then add it to `INSTALLED_APPS` in `settings.py` and `include()` its `urls.py` from `binge_and_bosses/urls.py`.

## Settings come from the environment
`settings.py` reads these from `binge_and_bosses/.env` locally, or from Render's environment in production:

| Variable | Default | What it does |
| --- | --- | --- |
| `SECRET_KEY` | none (required) | Django's signing key. Never commit it. |
| `DEBUG` | `False` | Set `DEBUG=True` in your local `.env` to get error pages and static files while developing. Never `True` in production. |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Hostnames the site answers to. |
| `CSRF_TRUSTED_ORIGINS` | empty | Origins allowed to submit forms (needed for the production URL). |
| `DATABASE_URL` | empty → local SQLite | A Postgres connection URL. Leave it unset locally and in tests. |
