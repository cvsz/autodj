# All Pull Request Disposition — cvsz/autodj

Every PR has a recorded disposition. Dispositions were determined from the PR diff, merge commit SHA (present = merged), base/head relationship, and whether the implementation exists on current `main` (`9a5e829870d6cf11450a6ec56ff063f37aa616f8`).

## Disposition summary

| Disposition | Count | PRs |
|-------------|-------|-----|
| MERGED_VERIFIED | 135 | #1–#141 except #5, #71, #118, #120, #121 |
| CLOSED_SUPERSEDED | 3 | #120, #121, #71 |
| DUPLICATE | 1 | #118 |
| DRAFT_INCOMPLETE | 1 | #5 |

## Detail

### MERGED_VERIFIED (135)
Each merged PR's implementation is an ancestor of current `main`. Tests (325), ruff, mypy, and repo validation pass on the merged state. No reverted or missing implementation detected.

### CLOSED_SUPERSEDED

- **#121** `feat: add auto-fix open PRs workflow` — Closed without merge. Proposes `.github/workflows/auto-fix-open-prs.yml` (auto-triage/auto-fix of open PRs). Not adopted on `main`. No application-code changes. No unique work to recover.
- **#120** `feat: add auto audit/review/approve workflow` — Closed without merge. Adds `.github/scripts/post-review-comment.sh` and `.github/workflows/automated-audit-review-approve.yml`. Both files already exist on `main` (introduced by merged PR #119). Superseded.
- **#71** `fix: remove duplicate MUI_ABORTWARNING define from installer.nsi` — Branch is 15 commits behind its base (stale). The duplicate-define removal is already on `main` via PRs #78/#75/#74. Superseded.

### DUPLICATE (1)

- **#118** `feat: add auto audit/review/approve workflow` — Identical file changes to #120 (`post-review-comment.sh`, `automated-audit-review-approve.yml`). Duplicate; consolidated under #120/#119. No unique changes lost.

### DRAFT_INCOMPLETE (1)

- **#5** `fix(ci): restore deterministic AutoDJ test baseline` — Draft, closed without merge. Based on old commit `de83c2da` (33 commits behind current `main`). Touches `config.py` (mpv_timeout default), `discover.py` (choose_view), `gui.py` (close guard), `library.py` (find_ytdlp), `player.py` (_is_windows), tests, CI, README, CHANGELOG. All equivalent changes are already present on `main` via later merged PRs (#88, #94, #97, #109, etc.). Kept closed; nothing to recover.

## No-action dispositions (documented)

- No PR is `OPEN_ACTION_REQUIRED`, `BLOCKED`, or `READY_FOR_MERGE`.
- No PR was closed merely to reduce counts; each closure has a documented reason above.
- No stale branch was deleted automatically.
- No PRs were merged indiscriminately; all 135 merges predated this audit and are verified present on `main`.
