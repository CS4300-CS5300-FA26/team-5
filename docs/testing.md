# Testing

The course grades tests every sprint: new features need tests, and coverage must stay at **80% or higher**. CI fails the build below 80%.

## Running the tests
From the `binge_and_bosses/` folder (the one with `manage.py`):

```bash
uv run python manage.py test
```

Run it from `binge_and_bosses/`, not the repo root. From the root, `python manage.py test` fails because there's no `manage.py` there, and `python binge_and_bosses/manage.py test` runs but finds 0 tests.

Django creates a temporary test database and deletes it afterward, so tests never touch your `db.sqlite3` or production. Leave `DATABASE_URL` unset when you run tests.

## Checking coverage locally
This is what CI runs (`coverage` is installed by `uv sync`):

```bash
uv run coverage run manage.py test
uv run coverage report -m
```

`report -m` lists the line numbers in each file that no test ran. Those are what to test next.

## Writing a test
Tests live in each app's `tests.py`. Each test is a method whose name starts with `test_`. [games/tests.py](../binge_and_bosses/games/tests.py) is a short example:

```python
class LandingPageTests(TestCase):
    def test_home_page_shows_empty_message_without_games(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No games yet...")
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

## Coming soon
- **Behave** runs the Gherkin scenarios from our user stories as tests. It's set up in PR #63 (design: `docs/design/behave.md` on that branch). Once that merges, the README explains how to run the scenarios, and each new feature's PR adds its story's scenarios.
- **Tests that need an outside API** (like the RAWG game search) must not call the real API. They replace it with fake responses, so tests work without a key and don't use up our request quota.
