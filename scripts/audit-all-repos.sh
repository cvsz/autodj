#!/usr/bin/env bash
# audit-all-repos.sh — Run audit-repo.sh on all repos under the cvsz GitHub account
#
# Usage: ./scripts/audit-all-repos.sh [max_repos]
#
# Outputs:
#   /tmp/opencode/audit-all-summary.txt — summary of all results
#   /tmp/opencode/audit-<repo>/audit-report.txt — per-repo detailed reports

set -euo pipefail

MAX_REPOS="${1:-}"
# Only list public repos owned by the user (not forks, not private)
REPO_LIST="$(gh api user/repos --jq '.[] | select(.fork == false and .private == false) | .full_name' 2>/dev/null || true)"

if [ -z "$REPO_LIST" ]; then
  echo "ERROR: Could not list repos. Make sure gh CLI is authenticated."
  exit 1
fi

TOTAL=$(echo "$REPO_LIST" | wc -l)
SUMMARY="/tmp/opencode/audit-all-summary.txt"
mkdir -p /tmp/opencode

echo "============================================================" | tee "$SUMMARY"
echo "BATCH AUDIT: All repos under cvsz" | tee -a "$SUMMARY"
echo "Date: $(date -u '+%Y-%m-%d %H:%M:%S UTC')" | tee -a "$SUMMARY"
echo "Total repos: $TOTAL" | tee -a "$SUMMARY"
echo "============================================================" | tee -a "$SUMMARY"

PASSED=0
FAILED=0
ERROR=0
SKIPPED=0

COUNT=0
while IFS= read -r repo; do
  [ -z "$repo" ] && continue
  COUNT=$((COUNT + 1))
  if [ -n "$MAX_REPOS" ] && [ "$COUNT" -gt "$MAX_REPOS" ]; then
    break
  fi

  echo ""
  echo "[$COUNT/$TOTAL] Auditing $repo ..."

  WORKDIR="/tmp/opencode/audit-$(echo "$repo" | tr '/' '_')"
  if ./scripts/audit-repo.sh "$repo" "$WORKDIR" > /tmp/opencode/audit-stdout.txt 2>&1; then
    RESULT="PASS"
    PASSED=$((PASSED + 1))
  else
    RC=$?
    if [ "$RC" -eq 2 ]; then
      RESULT="ERROR (clone failed)"
      ERROR=$((ERROR + 1))
    else
      RESULT="FAIL"
      FAILED=$((FAILED + 1))
    fi
  fi

  echo "  -> $RESULT" | tee -a "$SUMMARY"
done <<< "$REPO_LIST"

echo ""
echo "============================================================" | tee -a "$SUMMARY"
echo "BATCH AUDIT SUMMARY" | tee -a "$SUMMARY"
echo "============================================================" | tee -a "$SUMMARY"
echo "Total:    $TOTAL" | tee -a "$SUMMARY"
echo "Passed:   $PASSED" | tee -a "$SUMMARY"
echo "Failed:   $FAILED" | tee -a "$SUMMARY"
echo "Errors:   $ERROR" | tee -a "$SUMMARY"
echo "Skipped:  $SKIPPED" | tee -a "$SUMMARY"
echo "============================================================" | tee -a "$SUMMARY"
echo "Detailed reports: /tmp/opencode/audit-<owner>_<repo>/audit-report.txt" | tee -a "$SUMMARY"
echo "Summary: $SUMMARY" | tee -a "$SUMMARY"
