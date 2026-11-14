# Team conventions

The team agreed on this guide and the PR template on Discord (#31).
Rules below come from the linked team docs and that agreement.

## Build/setup and tests

For local app setup, read the [README](README.md#how-to-run-binge--bosses).
For Render's build process, read [Deployment](docs/deployment.md).
Run the following from the repository root; after `cd`, all tests run from
`binge_and_bosses/`. These are test-only values; leave `DATABASE_URL` unset
and keep production credentials out of local `.env` files used for tests.
See [Testing](docs/testing.md) for test behavior, coverage and skipped `@wip` scenarios.

```bash
export SECRET_KEY=ci-only-not-a-real-key DEBUG=True RAWG_API_KEY=test-key
unset DATABASE_URL
uv sync --locked
cd binge_and_bosses
uv run --locked python manage.py test
uv run --locked python manage.py behave --simple
uv run --locked coverage run manage.py test
uv run --locked coverage run --append manage.py behave --simple
uv run --locked coverage report -m --fail-under=80
```

## Code conventions

Read [Project layout](docs/project-layout.md) before placing code or changing URLs, templates or users.

- Put Django code in `binge_and_bosses/`: accounts in `authentication/`, games in `games/`.
- Use `settings.AUTH_USER_MODEL` in model fields and `get_user_model()` in code.
- Use fake RAWG responses in tests; never call the real API.
- New pages extend `base.html` (the shared `templates/base.html`) and fill its blocks.
- Commit migrations with model changes; never delete or edit existing migrations by hand.
- Keep secrets, `.env`, databases, virtual environments and generated static files out of commits.

## Pull requests and definition of done

Read [Pull requests](docs/pull-requests.md) before opening, reviewing or merging a PR.
Aim for under ~400 changed lines per PR; split unrelated work.
Use merge commits when merging PRs.

- Link the story or issue with `Closes #<number>` and explain what changed and why.
- For each feature, include the story's Gherkin as a Behave `.feature` file in the same PR
  ([agreed design, decision 9](docs/design/behave.md#decisions)).
- Write tests first and see them fail before implementing the behavior; record commands and results.
- CI's `test` check passes, including unit tests, Behave and at least 80% combined coverage.
- Before approving, CI is green and every AI review
  [Must fix](.github/ai-review-guide.md#output-format-github-markdown) is fixed or answered.
- When AI helps, describe the tool and its work in the PR and add a matching
  [README AI usage log](README.md#ai-usage-log) row.
- Get one teammate approval after the last push; another push needs approval again.
