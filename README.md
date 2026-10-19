# Binge & Bosses (Team 5)
CS 4300/5300 Fall 2026 — Team 5 group project

## Team Members:
- Ethan Capehart
- Michael Gonzalez
- Carlos Lucero Ortega
- Ryan Rupakheti
- Laura Baird

## What is Binge & Bosses
Binge & Bosses is a backlog management and social interaction platform geared for gamers who want to do the following:
- Track their backlog of games
- Review games they have played
- See the activity of their friends
- Get game recommendations
- Track the time spent in-game

## How to run Binge & Bosses
### Step 1. Install uv and the requirements
This project uses [uv](https://docs.astral.sh/uv/) to manage Python and packages. Install it once:
- macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh` (or `brew install uv`)
- Windows: `winget install --id=astral-sh.uv -e`

Then, from the repository root, run:
```bash
uv sync
```
This installs the Python version in `.python-version` (3.12) if you don't have it, and creates `.venv/` with the exact package versions in `uv.lock`. Run commands with `uv run` so they use that environment. In VS Code or PyCharm, set the interpreter to `.venv`.

### Step 2. Create .env file
within `binge_and_bosses/` create a file called `.env` in the same directory as `manage.py`

### Step 3. Add secret key
Next, generate a secret key and place it within the `.env` file with the format like:
```.env
SECRET_KEY=<SECRET_KEY_HERE>
``` 
You can generate a secret key by running
```
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### Step 4. Run the server
```bash
cd binge_and_bosses
uv run python manage.py runserver
```

## How to run the tests
After Steps 1–3, run the tests from the `binge_and_bosses/` directory (the one containing `manage.py`):
```bash
cd binge_and_bosses
uv run python manage.py test
```
Django creates a temporary test database and deletes it afterward, so the tests do not change `db.sqlite3`. Leave `DATABASE_URL` unset so the tests use local SQLite; never point tests at the production database.

Note: running `binge_and_bosses/manage.py test` from the repository root finds 0 tests, so `cd` into `binge_and_bosses/` first.

CI also checks coverage. To see it locally:
```bash
uv run coverage run manage.py test
uv run coverage report -m
```

## Adding or updating packages
- Add a package: `uv add <package>`. For tools only needed in development or CI (like `coverage`), use `uv add --dev <package>`.
- Then regenerate `requirements.txt`, which Render installs from:
  ```bash
  uv export --no-dev --no-emit-project -o requirements.txt
  ```
- Commit `pyproject.toml`, `uv.lock`, and `requirements.txt` together. CI fails if `uv.lock` or `requirements.txt` is out of date.
- Don't `pip install` into the project or edit `requirements.txt` by hand.

## AI code review
Every pull request gets an automatic review comment from OpenAI's `gpt-6-luna` model (`.github/workflows/ai-review.yml`). It posts a new comment-only review for each push and collapses its earlier reviews as outdated, so the latest review sits right after the latest commit. The review is advisory: a teammate still has to review and approve before merging. To change what the bot looks for, edit `.github/ai-review-guide.md`. The workflow reads the API key from the `OPENAI_API_KEY` repository secret.

## Sprint Plan

| Sprint  | Deliverables |  
|---|---|
| 1  | User accounts (with sign up & log-in), game search with third-party API integration, view games (database & Backlog CRUD), Basic UI navigation  | 
| 2  | Add games, set status, rate & review games | 
| 3  | Review games, friend connections, profile customization, review ratings from friends | 
| 4  | AI Recommendations (AI API integration using backlog as context; one line recommendation), Friend activity | 
## AI Usage Log

| Date       | AI        | Use  |
| --- | --- | --- |
| 09/28/2026 | Pardot AI | Used to refine sprint 0-2 on it's concluding stages to reformat logi UI diagrams and storyboards |
| 10/04/2026 | Pardot AI | Advice on Django secret key implementation and avoiding a push to render |
| 10/04/2026 | Pardot AI | Django app deployment instructions post settings.py modification | 
| 10/05/2026 | Claude | Render deployment debugging | 
| 10/06/2026 | Claude Code (Claude Opus 5.5) | Generated the landing page tests in `games/tests.py` (a saved game appears on the home page; the empty-list message appears when there are no games) and the README test instructions, and ran them locally. Submitted in a pull request for teammate review before merging. |
| 10/12/2026 | Claude Code (Claude Opus 5.5) | Wrote the AI code review workflow, its script and unit tests, and the reviewer guide in `.github/`. Laura reviewed the code and set the API key secret; submitted in a pull request for teammate review. |
| 10/12/2026 | Claude Code (Claude Opus 5.5) | Extended the AI review so it reads the PR's commit messages, its previous review, and teammates' comments, with tests. Laura reviewed it; submitted in a pull request for teammate review. |
| 10/12/2026 | Claude Code (Claude Opus 5.5) | Made the AI review handle huge diffs (per-file and per-directory limits, a list of all changed files) so a committed package can't hide the app's changes, with tests. Laura reviewed it; submitted in a pull request for teammate review. |
| 10/12/2026 | Claude Code (Claude Opus 5.5) | Edited the AI reviewer guide so the bot stops asking authors to confirm how outside APIs behave, and keeps unlikely edge cases out of Must fix. Laura reviewed it; submitted in a pull request for teammate review. |
| 10/12/2026 | Claude Code (Claude Opus 5.5) | Moved the project to uv: wrote `pyproject.toml`, generated `uv.lock` and the pinned `requirements.txt`, pinned Python 3.12, switched CI to uv with a check that `requirements.txt` matches the lock, and updated the README setup steps. Submitted in a pull request for teammate review. |
| 10/16/2026 | Claude Opus 5.5 | Generated log out button tests (log out button logs user out and removes their session from the database and index page displays correctly depending on if user is logged in) and library page tests(library page redirects logged out users to login and library displays correctly for logged in users) in `games/tests.py`. Also created placeholder library html template. |
