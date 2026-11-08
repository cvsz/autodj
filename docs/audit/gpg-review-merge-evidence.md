# GPG Review & Merge Evidence — Camfrog AutoDJ

**Repository:** github.com/cvsz/autodj  
**Workflow:** cvsz implements → policedbc independent review → cvsz controlled merge  
**Baseline SHA:** `fb5e99a`  
**Branch:** `feat/autodj-library-scan-safety`  
**Status:** BLOCKED at GPG signing (see below)

## Step A — cvsz implementation (attempted)

| Check | Result |
|-------|--------|
| `gh auth switch -u cvsz` | PASS — active account: cvsz |
| `gh auth status` | PASS — logged in as cvsz (token scopes include repo, workflow, admin:*) |
| `gh api user --jq .login` | `cvsz` |
| Git identity | `user.name=cvsz`, `user.email=seaza@msn.com` |
| `commit.gpgsign` | `true` |
| `gpg.program` | `/home/cvsz/.local/bin/gpg-loopback.sh` |
| GPG secret keys for cvsz `<seaza@msn.com>` | 4 keys present (ed25519, nistp256, ed25519, rsa2048) |
| `git commit -S` signing | **FAILED — BLOCKED** |

### GPG signing blocker

`gpg.loopback` signing requires `GPG_PASSPHRASE` (passed via fd 3 by `gpg-loopback.sh`) or a TTY for pinentry. Neither is available in this environment:

- `GPG_PASSPHRASE` environment variable: **not set**
- TTY for pinentry: **none** (`gpg: cannot open '/dev/tty': No such device or address`; `gpg: Sorry, we are in batchmode - can't get input`)

Attempted clearsign with each configured cvsz UID: all failed in batch mode without a passphrase source.

Per policy: **do not falsely claim signed commits.** Commits are not GPG-signed. The branch is kept unmerged pending a signing-capable environment.

## Step B — policedbc independent review (pending)

| Check | Result |
|-------|--------|
| `gh auth switch -u policedbc` | Account exists in gh config (policedbc + policedbc-m); **not switched to** (blocked at Step A) |
| `gh api user --jq .login` | Not executed |
| PR HEAD SHA review | Not executed |
| Independent approval | **PENDING** — cannot proceed without a signed commit / pushed PR |

policedbc is configured in gh but was not used because no PR was created (signing blocker prevents the cvsz→PR step per policy).

## Step C — cvsz controlled merge (pending)

| Gate | Result |
|------|--------|
| policedbc approval for exact HEAD SHA | PENDING |
| CI passed | PENDING (no PR opened) |
| Build passed | BLOCKED (Windows) |
| Integration tests passed | PASS (Linux, 336 pytest) |
| Security checks passed | PASS (ruff, config validation, no secrets) |
| No unresolved Critical/High issue | PASS |
| PR open and not Draft | PENDING (no PR opened) |
| Branch mergeable | PENDING |
| No new commits after approval | N/A |

## Evidence artifacts

- PR inventory: `docs/audit/all-pr-inventory.md`, `all-pr-matrix.md`, `all-pr-disposition.md`, `all-pr-dependencies.md`
- Test results: 336 passed (see `build-lint-test-report.md`)
- Ruff: pass (see `build-lint-test-report.md`)
- New regression tests: `tests/test_library_scan_safety.py`
- GPG keys: present but unsigned (passphrase required)

## Unblock path

To complete the GPG review/merge workflow, run on a host with `GPG_PASSPHRASE` set (or a TTY + pinentry) and the cvsg signing key unlocked:

```
gh auth switch -u cvsz
git config commit.gpgsign true
git commit -S -m "fix: ..."
git verify-commit HEAD
git push origin feat/autodj-library-scan-safety
gh pr create --base main --head feat/autodj-library-scan-safety --title "..."
gh auth switch -u policedbc
gh pr review <PR> --approve   # after independent audit
gh auth switch -u cvsz
gh pr merge <PR>               # controlled merge, only after approval + green checks
```
