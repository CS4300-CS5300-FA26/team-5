# Testing

The course grades tests every sprint: new features need tests, and coverage must stay at **80% or higher**. CI fails the build below 80%.

## Running the tests
From the `binge_and_bosses/` folder (the one with `manage.py`), install the locked packages and set test-only values:

```bash
uv sync --locked
export SECRET_KEY=ci-only-not-a-real-key DEBUG=True IGDB_CLIENT_ID=test-id IGDB_CLIENT_SECRET=test-secret
unset DATABASE_URL
uv run --locked python manage.py test
```

Run tests from `binge_and_bosses/`, where Django can find the apps' tests. Running from the repo root can fail or find no tests.

Django creates a temporary test database and deletes it afterward, so tests never touch your `db.sqlite3` or production. Leave `DATABASE_URL` unset when you run tests.

## Behave scenarios
Behave is on `main` (#63). From the same folder and with the same test environment:

```bash
uv run --locked python manage.py behave --simple
```

`--simple` uses Django's test client, with no browser or server. The scenarios in `features/` cover the landing page, sign-up, login, logout, search, game details, adding to the library, ratings and reviews. They check the same "Invalid username or password." message for an unknown username and a wrong password.

`behave.ini` skips scenarios tagged `@wip` by default. Each has an issue comment. To include only those scenarios:

```bash
uv run --locked python manage.py behave --simple --tags=@wip
```

No scenarios are tagged `@wip` right now. The duplicate-email scenario runs since #62 was fixed (#66, #71).

Add each new feature's scenarios in the same PR. Check `features/steps/common.py` for shared steps first. The [design](design/behave.md) records the original plan.

## Checking coverage locally
From `binge_and_bosses/`, with the test environment above, run both suites. This is what CI runs (`coverage` is a dev dependency):

```bash
uv run --locked coverage run manage.py test
uv run --locked coverage run --append manage.py behave --simple
uv run --locked coverage report -m --fail-under=80
```

`report -m` lists the line numbers in each file that neither suite ran. Those are what to test next. CI also checks that Django starts without dev packages, so `settings.py` only adds `behave_django` when it's installed.

## Tests that use IGDB
Tests must use fake IGDB responses and never call the real API. `games/tests.py` patches `games.igdb_client.requests.post` for client tests (both the Twitch token request and the IGDB query go through it), `games.views.search_game` for search view tests and `games.catalog.get_game_details` for game details. Behave scenarios tagged `@fake_igdb` get fake IGDB answers from `features/environment.py`; steps change them through `context.search_game` and `context.get_game_details`. The dummy `IGDB_CLIENT_ID` and `IGDB_CLIENT_SECRET` values satisfy settings; they aren't working credentials.

## Writing a test
Tests live in each app's `tests.py`. Each test is a method whose name starts with `test_`. [games/tests.py](../binge_and_bosses/games/tests.py) is a short example:

```python
class LandingPageTests(TestCase):
    def test_visitor_sees_what_the_app_is_for(self):
        response = self.client.get(reverse("index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "One save file for")
```

- `TestCase` gives each test a fresh, empty database.
- `self.client.get("/")` requests a page like a browser would, without running the server.
- Test what a user would notice (the page shows X, the form rejects Y), not how the code does it internally.

## TDD
The course asks us to write tests first:

1. Write a test for the behavior you're about to build. Run it and watch it fail.
2. Write just enough code to make it pass.
3. Clean up the code with the test still passing.

Watching it fail first proves the test can catch a bug.

Linting isn't part of CI yet (#36, Sprint 3).
