#!/usr/bin/env bash
# setup-git-credential-helper.sh — Configure git credential helper (plaintext store outside the repo)
# and run gh auth setup-git for the Four-Eyes Git & PR Workflow.
#
# This script:
#   1. Sets the global credential helper to store credentials in $GIT_CRED_FILE (default ~/.git-credentials)
#      Prefer Git Credential Manager (credential.helper=manager) on Windows where available.
#   2. Runs gh auth setup-git to initialise git config for GitHub CLI
#   3. Verifies the configuration

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "error: not inside a git repository" >&2
  exit 1
}

# 1. Set credential helper (plaintext store) to a file outside the repository.
# Absolute path: the old relative "D/.git-credentials" resolved against the
# current directory, scattering plaintext token files into whatever repo the
# command ran in (and into this repo's working tree).
CRED_FILE="${GIT_CRED_FILE:-$HOME/.git-credentials}"
case "$CRED_FILE" in
  "$REPO_ROOT"/*) echo "error: refusing to store credentials inside the repository ($CRED_FILE)" >&2; exit 1 ;;
esac
CRED_HELPER="store --file=$CRED_FILE"
echo "Setting credential.helper to: $CRED_HELPER"
git config --global credential.helper "$CRED_HELPER"

# 2. Run gh auth setup-git to initialise git config (name, email, gpgsign)
#    If gh is not available, we still record the intent.
if command -v gh >/dev/null 2>&1; then
  echo "Running: gh auth setup-git"
  gh auth setup-git
else
  echo "warn: gh CLI not found; skipping 'gh auth setup-git'. Install GitHub CLI or run manually."
fi

# 3. Verify
CRED_CONFIG=$(git config --get credential.helper 2>/dev/null || echo "(none)")
echo "Credential helper now configured: $CRED_CONFIG"

if [ -f "$CRED_FILE" ]; then
  chmod 600 "$CRED_FILE" 2>/dev/null || true
  echo "PASS: $CRED_FILE exists with permissions $(stat -c '%a' "$CRED_FILE" 2>/dev/null || echo 'unknown')."
else
  echo "WARN: $CRED_FILE not found yet; git creates it on first credential request."
fi

echo "Done. You can now proceed with the Four-Eyes Git & PR Workflow."
echo "  - Switch to author account:   gh auth switch -u cvsz"
echo "  - Switch to auditor account: gh auth switch -u policedbc"