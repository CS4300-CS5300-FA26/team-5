# Project layout

```
team-5/
├── binge_and_bosses/          ← the Django project; run manage.py commands from here
│   ├── manage.py
│   ├── build.sh               ← what Render runs on each deploy (see deployment.md)
│   ├── binge_and_bosses/      ← project settings and top-level URLs
│   │   ├── settings.py
│   │   └── urls.py
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
├── requirements.txt           ← Python packages
└── README.md                  ← setup, running, AI usage log
```

## How a page gets to the browser
Using the home page as the example:

1. `binge_and_bosses/urls.py` sends `/` to the games app's `urls.py`.
2. `games/urls.py` sends `""` to `views.index`.
3. `views.index` loads every `Game` from the database.
4. It renders `games/index.html` with those games.

New features follow the same path: URL → view → model → template.

## Adding a new app
Django apps group one area of the site (games, accounts, reviews, …).

```bash
cd binge_and_bosses
python3 manage.py startapp <name>
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
