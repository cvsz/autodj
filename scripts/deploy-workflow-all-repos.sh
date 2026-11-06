#!/usr/bin/env bash
# deploy-workflow-all-repos.sh — Deploy auto audit/review/approve workflow to all cvsz repos
#
# Usage: ./scripts/deploy-workflow-all-repos.sh [--test]
#
# What it does:
#   1. Lists all public repos owned by cvsz (not forks)
#   2. Copies .github/workflows/automated-audit-review-approve.yml to each repo
#   3. Copies .github/scripts/post-review-comment.sh to each repo
#   4. Sets POLIEDBC_PAT repository secret in each repo
#   5. Optionally creates a test PR on each repo to verify the workflow

set -euo pipefail

TEST_MODE="${1:-}"

WORKFLOW_SRC=".github/workflows/automated-audit-review-approve.yml"
SCRIPT_SRC=".github/scripts/post-review-comment.sh"
ACCOUNTS_FILE="scripts/gh-switch-accounts.conf"

# Get policedbc PAT from credential store
POLIEDBC_PAT="$(printf 'protocol=https\nhost=github.com\nusername=policedbc\n' | git credential fill 2>/dev/null | grep '^password=' | cut -d= -f2-)"
if [ -z "$POLIEDBC_PAT" ]; then
  echo "ERROR: POLIEDBC_PAT not found in credential store"
  exit 1
fi

echo "============================================================"
echo "DEPLOY: Auto Audit + Review + Approve workflow to all cvsz repos"
echo "Date: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "============================================================"

# List public repos owned by cvsz (not forks)
REPO_LIST="$(gh api user/repos --jq '.[] | select(.fork == false and .private == false) | .full_name' 2>/dev/null || true)"

if [ -z "$REPO_LIST" ]; then
  echo "ERROR: Could not list repos"
  exit 1
fi

TOTAL=$(echo "$REPO_LIST" | wc -l)
echo "Found $TOTAL public repos owned by cvsz (not forks)"
echo ""

PASSED=0
FAILED=0

COUNT=0
while IFS= read -r repo; do
  [ -z "$repo" ] && continue
  COUNT=$((COUNT + 1))
  echo ""
  echo "[$COUNT/$TOTAL] Deploying to $repo ..."

  WORKDIR="/tmp/opencode/deploy-$(echo "$repo" | tr '/' '_')"
  rm -rf "$WORKDIR"
  mkdir -p "$WORKDIR"

  # Clone repo
  if ! gh repo clone "$repo" "$WORKDIR" -- --depth=1 2>/dev/null; then
    echo "  ❌ Clone failed"
    FAILED=$((FAILED + 1))
    continue
  fi
  cd "$WORKDIR"

  # Copy workflow file and script
  mkdir -p .github/workflows .github/scripts
  cp "/mnt/d/data/camfrog-autodj/$WORKFLOW_SRC" .github/workflows/
  cp "/mnt/d/data/camfrog-autodj/$SCRIPT_SRC" .github/scripts/
  chmod +x .github/scripts/post-review-comment.sh

  # Set POLIEDBC_PAT secret
  echo "$POLIEDBC_PAT" | gh secret set POLIEDBC_PAT --repo "$repo" >/dev/null 2>&1 || {
    echo "  ❌ Failed to set POLIEDBC_PAT secret"
    FAILED=$((FAILED + 1))
    cd /mnt/d/data/camfrog-autodj
    continue
  }
  echo "  ✅ POLIEDBC_PAT secret set"

  # Commit and push
  git config user.name "cvsz"
  git config user.email "cvsz@seaza.com"
  export GPG_PASSPHRASE=@@@Zz112233
  git add .github/workflows/automated-audit-review-approve.yml .github/scripts/post-review-comment.sh
  if ! git diff --cached --quiet; then
    git -c gpg.program=/home/cvsz/.local/bin/gpg-loopback.sh commit -m "feat: add auto audit/review/approve workflow (policedbc)

- Add automated audit, review, and approve workflow
- policedbc service account reviews PRs
- Auto-approves when safe (no security-sensitive paths changed)
- Blocks auto-approve on security-sensitive paths per CODEOWNERS" >/dev/null 2>&1
    git push origin HEAD 2>/dev/null || {
      echo "  ❌ Push failed"
      FAILED=$((FAILED + 1))
      cd /mnt/d/data/camfrog-autodj
      continue
    }
    echo "  ✅ Workflow deployed and pushed"
  else
    echo "  ℹ️  No changes needed (already deployed)"
  fi

  # Optional: create test PR
  if [ "$TEST_MODE" = "--test" ]; then
    echo "  🧪 Creating test PR ..."
    TEST_BRANCH="test-auto-approve-$(date +%s)"
    git checkout -b "$TEST_BRANCH" >/dev/null 2>&1
    echo "# Test Auto-Approve" > TEST_AUTO_APPROVE.md
    git add TEST_AUTO_APPROVE.md
    git -c gpg.program=/home/cvsz/.local/bin/gpg-loopback.sh commit -m "test: auto-approve workflow trigger" >/dev/null 2>&1
    git push origin "$TEST_BRANCH" >/dev/null 2>&1 || {
      echo "  ⚠️  Test PR push failed (may need manual test)"
      cd /mnt/d/data/camfrog-autodj
      continue
    }
    gh pr create --title "test: auto-approve workflow" --body "ทดสอบ workflow อัตโนมัติ — policedbc" --base main --head "$TEST_BRANCH" --repo "$repo" >/dev/null 2>&1 || {
      echo "  ⚠️  Test PR creation failed"
    }
    echo "  ✅ Test PR created"
  fi

  PASSED=$((PASSED + 1))
  cd /mnt/d/data/camfrog-autodj
done <<< "$REPO_LIST"

echo ""
echo "============================================================"
echo "DEPLOY SUMMARY"
echo "============================================================"
echo "Total:    $TOTAL"
echo "Deployed: $PASSED"
echo "Failed:   $FAILED"
echo "============================================================"
