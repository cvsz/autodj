#!/usr/bin/env bash
# gh-switch — switch current git repo between multiple GitHub accounts.
#
# Usage:
#   gh-switch.sh list          # list accounts + current repo status
#   gh-switch.sh status        # current repo status only
#   gh-switch.sh switch <acct> # repoint origin + set local identity
#   gh-switch.sh add <name> <email> <ssh_alias> [signing_key] [https_user]
#
# Reads account registry from scripts/gh-switch-accounts.conf (relative to repo root).
# Format: name|email|ssh_alias|signing_key_fingerprint|https_username
#
# Only modifies the CURRENT repo's local git config. Never pushes to GitHub.

set -euo pipefail

# ---------------------------------------------------------------------------
# Resolve repo root (works when run from any subdirectory)
# ---------------------------------------------------------------------------
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "error: not inside a git repository" >&2
  exit 1
}
ACCOUNTS_FILE="$REPO_ROOT/scripts/gh-switch-accounts.conf"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
die() { echo "error: $*" >&2; exit 1; }
warn() { echo "warn: $*" >&2; }

parse_account() {
  # $1 = account name
  # sets: ACCT_NAME ACCT_EMAIL ACCT_SSH_ALIAS ACCT_SIGNING_KEY ACCT_HTTPS_USER
  local name="$1" line
  [ -f "$ACCOUNTS_FILE" ] || die "accounts registry not found: $ACCOUNTS_FILE"
  line="$(grep -v '^\s*#' "$ACCOUNTS_FILE" | grep -v '^\s*$' | grep "^${name}|" | head -1)"
  [ -n "$line" ] || die "account '$name' not found in $ACCOUNTS_FILE"

  IFS='|' read -r ACCT_NAME ACCT_EMAIL ACCT_SSH_ALIAS ACCT_SIGNING_KEY ACCT_HTTPS_USER <<< "$line"
  ACCT_SIGNING_KEY="${ACCT_SIGNING_KEY:-}"
  ACCT_HTTPS_USER="${ACCT_HTTPS_USER:-}"
}

# Detect owner/repo from a remote URL (ssh or https)
parse_origin() {
  # sets: ORIG_HOST ORIG_OWNER ORIG_REPO ORIG_URL
  local url="$1"
  ORIG_URL="$url"

  if [[ "$url" =~ ^git@([^:]+):(.+)/(.+)\.git$ ]]; then
    ORIG_HOST="${BASH_REMATCH[1]}"
    ORIG_OWNER="${BASH_REMATCH[2]}"
    ORIG_REPO="${BASH_REMATCH[3]%.git}"
  elif [[ "$url" =~ ^https://([^/]+)/(.+)/(.+)\.git$ ]]; then
    ORIG_HOST="${BASH_REMATCH[1]}"
    ORIG_OWNER="${BASH_REMATCH[2]}"
    ORIG_REPO="${BASH_REMATCH[3]%.git}"
  elif [[ "$url" =~ ^https://[^@]+@([^/]+)/(.+)/(.+)\.git$ ]]; then
    ORIG_HOST="${BASH_REMATCH[1]}"
    ORIG_OWNER="${BASH_REMATCH[2]}"
    ORIG_REPO="${BASH_REMATCH[3]%.git}"
  else
    die "could not parse origin URL: $url"
  fi
}

new_remote_url() {
  # $1 = ssh_alias or https_username, $2 = https or ssh
  local alias="$1" mode="$2"
  if [ "$mode" = "ssh" ]; then
    echo "git@${alias}:${ORIG_OWNER}/${ORIG_REPO}.git"
  else
    echo "https://${alias}@github.com/${ORIG_OWNER}/${ORIG_REPO}.git"
  fi
}

current_remote() {
  git remote get-url origin 2>/dev/null || die "no 'origin' remote configured"
}

list_accounts() {
  echo "=== Configured accounts ==="
  if [ ! -f "$ACCOUNTS_FILE" ]; then
    echo "(no accounts registry at $ACCOUNTS_FILE)"
  else
    grep -v '^\s*#' "$ACCOUNTS_FILE" | grep -v '^\s*$' | while IFS='|' read -r name email ssh_alias signing_key https_user; do
      [ -z "$name" ] && continue
      printf '  %-14s %-30s ssh=%-18s https=%-12s signing=%s\n' \
        "$name" "$email" "${ssh_alias:-(none)}" "${https_user:-(none)}" "${signing_key:-(none)}"
    done
  fi
  echo ""
  echo "=== Current repo ($REPO_ROOT) ==="
  local url mode alias owner repo
  url="$(current_remote)"
  if [[ "$url" =~ ^git@ ]]; then mode="ssh"; elif [[ "$url" =~ ^https ]]; then mode="https"; else mode="unknown"; fi
  echo "  remote: $url ($mode)"
  echo "  user.name:  $(git config user.name || echo '(not set)')"
  echo "  user.email: $(git config user.email || echo '(not set)')"
  echo "  signingkey: $(git config user.signingkey || echo '(not set)')"
}

status() {
  list_accounts
}

switch_account() {
  local acct="$1"
  parse_account "$acct"

  local cur_url cur_mode
  cur_url="$(current_remote)"
  parse_origin "$cur_url"

  local new_url mode
  if [ -n "$ACCT_SSH_ALIAS" ]; then
    new_url="$(new_remote_url "$ACCT_SSH_ALIAS" ssh)"
    mode="ssh"
  elif [ -n "$ACCT_HTTPS_USER" ]; then
    new_url="$(new_remote_url "$ACCT_HTTPS_USER" https)"
    mode="https"
  else
    die "account '$acct' has no ssh_alias or https_username configured"
  fi

  echo "Switching origin:"
  echo "  from: $cur_url"
  echo "  to:   $new_url"

  git remote set-url origin "$new_url"

  git config user.name "$ACCT_NAME"
  git config user.email "$ACCT_EMAIL"
  if [ -n "$ACCT_SIGNING_KEY" ]; then
    git config user.signingkey "$ACCT_SIGNING_KEY"
    echo "  user.signingkey = $ACCT_SIGNING_KEY"
  else
    warn "no signing key for '$acct'; leaving existing user.signingkey unchanged"
  fi

  echo ""
  echo "Switched origin to: $new_url ($mode)"
  echo "Set user.name=$ACCT_NAME, user.email=$ACCT_EMAIL"
  echo ""
  echo "Note: if using SSH, ensure the public key for '$acct' is added to GitHub."
  echo "      Test with: ssh -T $ACCT_SSH_ALIAS"
}

add_account() {
  local name="$1" email="$2" ssh_alias="$3" signing_key="${4:-}" https_user="${5:-}"
  [ -n "$name" ] && [ -n "$email" ] && [ -n "$ssh_alias" ] || die "usage: add <name> <email> <ssh_alias> [signing_key] [https_user]"

  touch "$ACCOUNTS_FILE"
  # Remove existing entry for same name if present
  grep -v "^${name}|" "$ACCOUNTS_FILE" > "${ACCOUNTS_FILE}.tmp" 2>/dev/null || true
  mv "${ACCOUNTS_FILE}.tmp" "$ACCOUNTS_FILE"

  echo "${name}|${email}|${ssh_alias}|${signing_key}|${https_user}" >> "$ACCOUNTS_FILE"
  echo "Added account '$name' to $ACCOUNTS_FILE"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
cmd="${1:-}"
case "$cmd" in
  list|ls)
    list_accounts
    ;;
  status|st)
    status
    ;;
  switch)
    [ -n "${2:-}" ] || die "usage: $0 switch <account>"
    switch_account "$2"
    ;;
  add)
    [ -n "${4:-}" ] || die "usage: $0 add <name> <email> <ssh_alias> [signing_key] [https_user]"
    add_account "$2" "$3" "$4" "${5:-}" "${6:-}"
    ;;
  *)
    echo "gh-switch — multi-account GitHub switcher"
    echo ""
    echo "Usage: $0 {list|status|switch|add}"
    echo ""
    echo "  list              Show accounts and current repo status"
    echo "  status            Same as list"
    echo "  switch <acct>     Repoint origin + set local identity for <acct>"
    echo "  add <n> <e> <a> [k] [u]  Add account to registry"
    echo ""
    echo "Accounts registry: $ACCOUNTS_FILE"
    exit 1
    ;;
esac
