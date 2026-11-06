#!/usr/bin/env bash
# audit-repo.sh — Auto audit a single repository using the policedbc checks
#
# Usage: ./scripts/audit-repo.sh <owner/repo> [workdir]
#
# Checks performed:
#   1. Repository structure validation (validate_repo.py if present)
#   2. Secret-bearing file scan (.env, id_rsa, id_ed25519, .pem, .key)
#   3. GitHub Actions workflow YAML validation
#   4. GPG signing configuration
#   5. Credential store availability
#
# Exit codes:
#   0 = all checks passed
#   1 = one or more checks failed
#   2 = could not clone / not a git repo

set -euo pipefail

TARGET="${1:?Usage: $0 <owner/repo> [workdir]}"
WORKDIR="${2:-/tmp/opencode/audit-$(echo "$TARGET" | tr '/' '_')}"
REPORT_FILE="${WORKDIR}/audit-report.txt"

mkdir -p "$WORKDIR"

log() { echo "[$(date +'%H:%M:%S')] $*"; }
fail() { echo "FAIL: $*" | tee -a "$REPORT_FILE"; }
pass() { echo "PASS: $*" | tee -a "$REPORT_FILE"; }
warn() { echo "WARN: $*" | tee -a "$REPORT_FILE"; }

echo "============================================================" | tee "$REPORT_FILE"
echo "AUDIT: $TARGET" | tee -a "$REPORT_FILE"
echo "Workdir: $WORKDIR" | tee -a "$REPORT_FILE"
echo "Date: $(date -u '+%Y-%m-%d %H:%M:%S UTC')" | tee -a "$REPORT_FILE"
echo "============================================================" | tee -a "$REPORT_FILE"

OVERALL=0

# ------------------------------------------------------------------
# Clone the repository (shallow) using gh CLI for auth
# ------------------------------------------------------------------
log "Cloning $TARGET ..."
rm -rf "$WORKDIR"
mkdir -p "$WORKDIR"
if ! gh repo clone "$TARGET" "$WORKDIR" -- --depth=1 2>/tmp/opencode/clone-err.log; then
  fail "Could not clone $TARGET (gh repo clone failed)"
  cat /tmp/opencode/clone-err.log | tee -a "$REPORT_FILE"
  exit 2
fi
cd "$WORKDIR"

# ------------------------------------------------------------------
# Check 1: Repository structure validation
# ------------------------------------------------------------------
log "Check 1: Repository structure validation"
if [ -f scripts/validate_repo.py ]; then
  if python3 scripts/validate_repo.py > /tmp/opencode/validate-out.txt 2>&1; then
    pass "validate_repo.py passed"
    cat /tmp/opencode/validate-out.txt >> "$REPORT_FILE" 2>/dev/null || true
  else
    fail "validate_repo.py failed"
    cat /tmp/opencode/validate-out.txt >> "$REPORT_FILE" 2>/dev/null || true
    OVERALL=1
  fi
else
  warn "scripts/validate_repo.py not found (repo does not use ZEAZ template)"
fi

# ------------------------------------------------------------------
# Check 2: Secret-bearing file scan
# ------------------------------------------------------------------
log "Check 2: Secret-bearing file scan"
SECRET_FILES="$(git ls-files | grep -E '(^|/)(\.env$|id_rsa|id_ed25519|.*\.pem|.*\.key)$' | grep -v '^\.env\.example$' || true)"
if [ -z "$SECRET_FILES" ]; then
  pass "No tracked secret-bearing files"
else
  fail "Tracked secret-bearing files found:"
  echo "$SECRET_FILES" | tee -a "$REPORT_FILE"
  OVERALL=1
fi

# ------------------------------------------------------------------
# Check 3: GitHub Actions workflow YAML validation
# ------------------------------------------------------------------
log "Check 3: GitHub Actions workflow YAML validation"
YAML_FAIL=0
YAML_COUNT=0
while IFS= read -r -d '' yf; do
  YAML_COUNT=$((YAML_COUNT + 1))
  if ! python3 -c "import yaml; yaml.safe_load(open('$yf'))" 2>/dev/null; then
    fail "Invalid YAML: $yf"
    YAML_FAIL=1
  fi
done < <(find .github \( -name '*.yml' -o -name '*.yaml' \) -print0 2>/dev/null || true)

if [ "$YAML_COUNT" -eq 0 ]; then
  pass "No GitHub workflow YAML files found"
elif [ "$YAML_FAIL" -eq 0 ]; then
  pass "All $YAML_COUNT YAML files valid"
else
  OVERALL=1
fi

# ------------------------------------------------------------------
# Check 4: GPG signing configuration
# ------------------------------------------------------------------
log "Check 4: GPG signing configuration"
GPG_SIGN=$(git config --get commit.gpgsign 2>/dev/null || echo "false")
GPG_KEY=$(git config --get user.signingkey 2>/dev/null || echo "(none)")
if [ "$GPG_SIGN" = "true" ] && [ -n "$GPG_KEY" ] && [ "$GPG_KEY" != "(none)" ]; then
  pass "GPG signing enabled: key=$GPG_KEY"
else
  fail "GPG signing not fully configured (commit.gpgsign=$GPG_SIGN, user.signingkey=$GPG_KEY)"
  OVERALL=1
fi

# ------------------------------------------------------------------
# Check 5: Credential store
# ------------------------------------------------------------------
log "Check 5: Credential store availability"
CRED_HELPER=$(git config --get credential.helper 2>/dev/null || echo "(none)")
if [ -f ~/.git-credentials ] || [ "$CRED_HELPER" = "cache --timeout=3600" ] || [ "$CRED_HELPER" = "store" ]; then
  pass "Credential helper configured: $CRED_HELPER"
else
  fail "No credential helper configured"
  OVERALL=1
fi

# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------
echo "" | tee -a "$REPORT_FILE"
echo "============================================================" | tee -a "$REPORT_FILE"
if [ "$OVERALL" -eq 0 ]; then
  echo "RESULT: ✅ PASSED" | tee -a "$REPORT_FILE"
else
  echo "RESULT: ❌ FAILED" | tee -a "$REPORT_FILE"
fi
echo "============================================================" | tee -a "$REPORT_FILE"

log "Report saved to: $REPORT_FILE"
exit $OVERALL
