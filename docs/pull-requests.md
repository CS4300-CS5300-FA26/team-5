# Pull requests

Nobody can push to `main` directly. Every change goes through a pull request (PR).

## The usual flow
1. **Claim the issue.** Assign yourself and move it to *In Progress* on the [Sprint Board](https://github.com/orgs/CS4300-CS5300-FA26/projects/5), so nobody else starts the same thing.
2. **Branch from the latest `main`:**
   ```bash
   git switch main
   git pull
   git switch -c short-description-of-change
   ```
3. **Commit and push.** Commit messages say what changed ("Add search results page"), not "updates" or "fix".
4. **Open the PR.** Put `Closes #<issue number>` in the description so the issue closes when the PR merges. Move the issue to *In Review*.
5. **Wait for checks and a review** (below).
6. **Merge** once it's approved and the checks are green. Delete the branch afterward.

Not ready for review yet? Open it as a **draft**. Teammates can see it and comment, and the AI review waits until you mark it ready.

## What runs on your PR
| Check | What it does | If it fails |
| --- | --- | --- |
| **CI** (`ci.yaml`) | Runs all tests and requires at least 80% coverage. Also runs on every push to any branch. | Click *Details* on the failed check and read the log. Usually a failing test or new code without tests. See [Testing](testing.md). |
| **AI code review** (`ai-review.yml`) | Posts a review comment with suggestions. Skips draft PRs. | It never blocks merging. Treat it as one reviewer's opinion: fix what's right, reply on what's wrong. |

## Getting it merged
- **One approval from a teammate** is required.
- **The last push needs approval.** If you push after someone approved, a teammate must approve again.

## Reviewing a teammate's PR
- Pull the branch and run it if the change is visible in the browser.
- Check that tests cover the new behavior, not just that CI is green.
- Ask questions. "Why X?" is a fine review comment.
- Approve when you'd be comfortable fixing a bug in this code yourself.

## Commit attribution
The course only credits commits linked to your GitHub account. Check yours once:

```bash
git config user.email
```

That email must be one listed in your GitHub account's email settings. If a commit shows someone else's avatar or no avatar on GitHub, ask in Discord before pushing more.

## Things to avoid
- **PRs that depend on another open PR** ("stacked" PRs). They're hard to review and merge in the right order. Branch from `main` and wait if you need someone else's work.
- **Huge PRs.** Smaller PRs get reviewed faster and better. Split by feature if you can.
- **Committing `db.sqlite3`, `.env`, or `staticfiles/`.** They're in `.gitignore`. If `git status` shows one, don't `git add` it.
