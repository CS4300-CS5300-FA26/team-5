# Project layout

```
team-5/
├── Procfile                   ← Heroku web and release commands
├── binge_and_bosses/          ← the Django project; run manage.py commands from here
│   ├── manage.py
│   ├── binge_and_bosses/      ← project settings and top-level URLs
│   │   ├── settings.py
│   │   └── urls.py
│   ├── templates/base.html    ← shared page layout (Bootstrap); new pages extend it
│   ├── behave.ini             ← skips @wip scenarios by default
│   ├── features/              ← landing, account, search, details, library, rating and review scenarios; steps in steps/
│   ├── authentication/        ← accounts: custom User model, sign-up, log-in
│   │   ├── models.py          ← User (settings.AUTH_USER_MODEL)
│   │   ├── forms.py           ← SignupForm, LoginForm (Bootstrap-styled)
│   │   ├── views.py           ← signup view; log-in/out come from Django
│   │   ├── urls.py            ← everything under /accounts/
│   │   ├── static/authentication/css/
│   │   └── templates/registration/  ← login.html, signup.html
│   └── games/                 ← the "games" app
│       ├── models.py          ← Game metadata and Catalog library entries (status, rating, review)
│       ├── forms.py           ← ReviewForm validates the optional rating and review
│       ├── views.py           ← home, library, IGDB search and details views
│       ├── igdb_client.py     ← search_game and get_game_details call IGDB
│       ├── urls.py
│       ├── templates/games/   ← index.html (visitor landing page), home.html (player home page), library.html, search.html, details.html
│       ├── static/games/css/  ← landing.css (shared by the landing, home, library and search pages)
│       ├── migrations/        ← committed; never delete or edit by hand
│       └── tests.py
├── .github/
│   ├── workflows/ci.yaml          ← unit tests + Behave + coverage on every push and PR
│   ├── workflows/ai-review.yml    ← AI review comment on every PR
│   ├── ai-review-guide.md         ← what the AI reviewer looks for
│   └── scripts/                   ← the AI review script and its tests
├── docs/                      ← you are here
├── pyproject.toml             ← the packages we depend on (edit with `uv add`)
├── uv.lock                    ← exact pinned versions of every package; commit it
├── .python-version            ← Python version (3.12)
└── README.md                  ← setup, running, adding packages, AI usage log
```

## How a page gets to the browser
Using the home page as the example:

1. `binge_and_bosses/urls.py` sends `/` to the games app's `urls.py`.
2. `games/urls.py` sends `""` to `views.index`.
3. `views.index` renders `games/index.html`, the landing page, for visitors. For a logged-in player it reads their library from `Catalog` and renders `games/home.html` instead.
4. The template shows different buttons to visitors and logged-in players (`user.is_authenticated`).

New features follow the same path: URL → view → model → template.

Search and details fetch IGDB data through `games/igdb_client.py`, which gets and caches the Twitch access token IGDB needs. Adding a game imports its metadata into `Game` through `games/catalog.py`. The library stores each player's saved games as `Catalog` entries, with their status, rating and review. The game page shows everyone's ratings and reviews; library owners can save their own through `ReviewForm`.

## Pages
| URL | Name | What it is |
| --- | --- | --- |
| `/` | `index` | Visitors get the landing page: what the app does, an example library, Sign up and Log in. Players get their home page: a search box, library stats, games popular with other players that they don't have yet, and recently added games. Makes no IGDB calls. |
| `/search/?q=title` | `game_search` | Search IGDB by title (main games, remakes, remasters, ports and expansions; no mods or alternate editions); shows up to five results with their release year, and marks games already in your library. If IGDB fails, shows this visitor's last results for the same search (kept in the session). No login required. |
| `/<int:game_id>/` | `game_details` | Details for an IGDB game ID. If IGDB fails, goes back to the search results with an error when opened from a search, otherwise shows the error on this page. No login required. |
| `/library/` | `library` | The user's saved games, statuses and ratings. `?sort=recent` (default), `title` or `rating` (unrated last). Requires login. |
| `/<int:game_id>/add/` | `add_to_library` | Add an IGDB game to the user's library. POST and login required. |
| `/<int:game_id>/remove/` | `remove_from_library` | Remove a game from the user's library. POST and login required. |
| `/<int:game_id>/review/` | `save_review` | Save the user's rating and review. POST, login and a library entry required. |
| `/accounts/signup/` | `signup` | Sign-up. Logs the new user in and goes to the library. |
| `/accounts/login/` | `login` | Log-in. Goes to the library, or to `?next=` if set. |
| `/accounts/logout/` | `logout` | Log-out. Must be a POST (a form with `{% csrf_token %}`), not a link. Goes to the login page. |
| `/admin/` | | Django admin |

Use the name in code and templates (`reverse("library")`, `{% url 'login' %}`) rather than writing the URL out. The redirects after logging in and out are set by `LOGIN_REDIRECT_URL` and `LOGOUT_REDIRECT_URL` in `settings.py`.

## Templates
`templates/base.html` holds the page skeleton and Bootstrap. A page extends it and fills in its blocks:

```django
{% extends "base.html" %}
{% block title %}Library | Binge and Bosses{% endblock %}
{% block content %}
    <h1>...</h1>
{% endblock %}
```

Every page uses it, and it holds the shared nav bar (#59, PR #67).

## Users
Always refer to the user model as `settings.AUTH_USER_MODEL` (in model fields) or `get_user_model()` (in code), never `django.contrib.auth.models.User`. We use our own `authentication.User`, so Django's built-in one isn't the one in the database.

Sign-up asks for a username, email and password. It rejects a taken username or email with one generic message, "Unable to create an account with those details. Try logging in or resetting your password.", so the page doesn't reveal which one is registered (#62). Login uses a username and shows "Invalid username or password." for both an unknown username and a wrong password (#61).

## Adding a new app
Django apps group one area of the site (games, accounts, reviews, …). From the repository root, for a new app called `reviews`:

```bash
cd binge_and_bosses
uv run python manage.py startapp reviews
```

Then add it to `INSTALLED_APPS` in `settings.py`. `startapp` doesn't create a `urls.py`, so create `reviews/urls.py` with a `urlpatterns` list (copy `games/urls.py`), and `include()` it from `binge_and_bosses/urls.py`.

## Settings come from the environment
`settings.py` reads these from `binge_and_bosses/.env` locally, or from Heroku's config vars in production:

| Variable | Default | What it does |
| --- | --- | --- |
| `SECRET_KEY` | none (required) | Django's signing key. Never commit it. |
| `IGDB_CLIENT_ID` | none (required) | Client ID of a Twitch developer app, used for IGDB. Required even to start Django. Tests and CI use the dummy value `test-id`. |
| `IGDB_CLIENT_SECRET` | none (required) | That app's Client Secret. Required even to start Django. Tests and CI use the dummy value `test-secret`; real searches need working credentials. |
| `DEBUG` | `False` | Set `DEBUG=True` in your local `.env` to get error pages and static files while developing. Never `True` in production. |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Hostnames the site answers to. |
| `CSRF_TRUSTED_ORIGINS` | empty | Origins allowed to submit forms (needed for the production URL). |
| `DATABASE_URL` | empty → local SQLite | A Postgres connection URL. Leave it unset locally and in tests. |
