#!/usr/bin/env bash
# setup-git-credential-helper.sh — Configure git credential helper to use D:/.git-credentials
# and run gh auth setup-git for the Four-Eyes Git & PR Workflow.
#
# This script:
#   1. Sets the global credential helper to store credentials in D/./.git-credentials
#   2. Runs gh auth setup-git to initialise git config for GitHub CLI
#   3. Verifies the configuration

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "error: not inside a git repository" >&2
  exit 1
}

# 1. Set credential helper to store in D:/.git-credentials
#    Use forward-slash style path; git on Windows accepts either.
CRED_HELPER="store --file=D/.git-credentials"
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

if [ -f "D/.git-credentials" ]; then
  echo "PASS: D/.git-credentials file exists with permissions $(stat -c '%a' 'D/.git-credentials' 2>/dev/null || echo 'unknown')."
else
  echo "WARN: D/.git-credentials file not found immediately; git may create on first credential request."
fi

echo "Done. You can now proceed with the Four-Eyes Git & PR Workflow."
echo "  - Switch to author account:   gh auth switch -u cvsz"
echo "  - Switch to auditor account: gh auth switch -u policedbc"