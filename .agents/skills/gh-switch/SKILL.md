# gh-switch — Multi-Account GitHub Switcher

A reusable skill for switching a git repo between multiple GitHub accounts
(HTTPS credential store or SSH host aliases), with per-repo identity and GPG
signing config.

## What it does

- `list` — show all configured accounts and which remote the current repo uses
- `status` — show current repo's remote URL and local git identity
- `switch <account>` — repoint `origin` to the account's SSH alias (or HTTPS
  username) and set local `user.name` / `user.email` / `user.signingkey`
- `add <name> <email> <ssh-alias> [signing-key]` — register a new account in
  the accounts registry

## Prerequisites

- SSH config (`~/.ssh/config`) already contains host aliases for each account
  (e.g. `github-poldbc`, `github-arin-z`, `github-arinfamily`).
- `~/.git-credentials` (store helper) contains HTTPS entries for each account
  if you prefer HTTPS over SSH.
- GPG signing key configured globally (`commit.gpgsign=true`); per-account
  signing keys can be overridden in the registry.

## Accounts registry

The script reads `scripts/gh-switch-accounts.conf`. Create it if missing:

```ini
# format: name|email|ssh_alias|signing_key_fingerprint|https_username
cvsz|cvsz@seaza.com|github.com|8BC7A85F1FB5322782921AEC14E1E0BC08F632B0|cvsz
poldbc|poldbc@zeaz|github-poldbc||policedbc
arin-z|arin-z@zeaz|github-arin-z||arin-z
arim-z|arim-z@zeaz|github-arim-z||arim-z
arinfamily|arinfamily.th@gmail.com|github-arinfamily||arinfamily
```

Lines starting with `#` are comments. The `signing_key_fingerprint` and
`https_username` fields are optional.

## Usage

```bash
# See all accounts and current repo status
scripts/gh-switch.sh list

# Show only current repo status
scripts/gh-switch.sh status

# Switch current repo to policedbc (SSH)
scripts/gh-switch.sh switch poldbc

# Switch current repo to arinfamily (SSH)
scripts/gh-switch.sh switch arinfamily

# Register a new account
scripts/gh-switch.sh add newuser newuser@example.com github-newuser
```

## What `switch` changes (local repo only, never pushed)

1. `origin` remote URL → `git@<ssh-alias>:<owner>/<repo>.git` (or
   `https://<https-username>@github.com/<owner>/<repo>.git`)
2. `git config user.name` → account name
3. `git config user.email` → account email
4. `git config user.signingkey` → account signing key (if set in registry)

Remote host / owner / repo name are detected from the current `origin` URL and
preserved; only the account-specific prefix changes.

## Example

```bash
$ git remote -v
origin  git@github.com:cvsz/autodj.git (fetch)
origin  git@github.com:cvsz/autodj.git (push)

$ scripts/gh-switch.sh switch arinfamily
Switched origin to git@github-arinfamily:cvsz/autodj.git
Set user.name=arinfamily, user.email=arinfamily.th@gmail.com

$ git remote -v
origin  git@github-arinfamily:cvsz/autodj.git (fetch)
origin  git@github-arinfamily:cvsz/autodj.git (push)
```

## Files

| File | Purpose |
|---|---|
| `scripts/gh-switch.sh` | Executable switcher script |
| `scripts/gh-switch-accounts.conf` | Account registry (create from example below) |
| `.agents/skills/gh-switch/SKILL.md` | This document |

## Example accounts registry

Save as `scripts/gh-switch-accounts.conf`:

```ini
# Multi-account GitHub registry for gh-switch
# name|email|ssh_alias|signing_key|https_username
cvsz|cvsz@seaza.com|github.com|8BC7A85F1FB5322782921AEC14E1E0BC08F632B0|cvsz
poldbc|poldbc@zeaz|github-poldbc||policedbc
arin-z|arin-z@zeaz|github-arin-z||arin-z
arim-z|arim-z@zeaz|github-arim-z||arim-z
arinfamily|arinfamily.th@gmail.com|github-arinfamily||arinfamily
```

## Security

- The accounts registry may contain email addresses and signing-key fingerprints
  but **never** tokens or passwords. Tokens live only in `~/.git-credentials`
  (mode 600) and SSH keys in `~/.ssh/` (mode 600).
- `gh-switch.sh` modifies only the current repo's local config; it never pushes
  or writes to GitHub directly.
