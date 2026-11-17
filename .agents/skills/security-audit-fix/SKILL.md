---
name: zeaz-security-audit-fix
title: ZEAZ Security Audit Fix
description: Reusable skill for fixing security code-scanning findings across any cvsz repository.
version: "0.1.0"
license: MIT
tags: [zeaz, security, audit, code-scanning, remediation]
supported_harnesses: [codex, claude, opencode]
risk_level: medium
requires_network: false
requires_credentials: true
evidence_state: reproducible
---

# ZEAZ Security Audit Fix

## Purpose

This skill provides a reusable, cross-repository playbook for fixing security code-scanning findings (e.g., CodeQL, Bandit, Snyk, Semgrep) in any cvsz-owned GitHub repository. It standardizes the remediation workflow from evidence collection through PR merge, ensuring consistent security remediation practice across all cvsz repositories.

## When to Apply

Use this skill when:

- Code scanning (CodeQL, Bandit, Semgrep, or similar) reports security findings that require remediation.
- A security audit identifies code-level vulnerabilities needing fixes.
- A repository's `SECURITY.md` or `AUDIT_FINDINGS.md` lists unresolved security findings.
- You need to apply the same fix pattern across multiple cvsz repositories.

Do **not** use this skill for:

- Infrastructure-as-code misconfigurations (use infrastructure-specific remediation).
- Dependency vulnerability updates (use dependency-update playbooks instead).
- Runtime configuration issues unrelated to source code.

## Prerequisites

- GitHub CLI (`gh`) authenticated with write access to the target repository.
- Git configured with GPG signing (`commit.gpgsign=true`).
- Access to the target repository's security alerts / code scanning alerts page.
- Familiarity with the repository's language ecosystem (Python, Go, JavaScript, etc.) to apply safe fixes.

## Step 1: Authenticate and Identify the Repository

```bash
# Switch to cvsz account (author and merger)
gh auth switch -u cvsz
gh auth status  # Verify: active account cvsz

# Set git identity
git config user.name "cvsz"
git config user.email "seaza@msn.com"

# Verify GPG signing is configured
git config commit.gpgsign  # Should return "true"
```

Set the target repository:

```bash
REPO_OWNER="cvsz"
REPO_NAME="<repo-name>"   # e.g., autodj, zeaz, etc.
REPO_PATH="${REPO_OWNER}/${REPO_NAME}"
```

## Step 2: Create Feature Branch from Main

```bash
# Fetch latest main
git fetch origin main
git checkout -b feat/security-audit-fix-$(date +%Y%m%d) origin/main
git branch --show-current  # Verify: feat/security-audit-fix-YYYYMMDD
```

## Step 3: Discover Security Findings

Run code scanning and collect findings:

```bash
# List open security alerts
gh api "repos/${REPO_OWNER}/${REPO_NAME}/code-scanning/alerts" \
  --jq '.[] | {rule: .rule.id, severity: .rule.severity, state: .state, location: .most_recent_instance.location.path}' \
  --jq '.[] | select(.state == "open")' > security-findings.json

# Alternatively, via GitHub UI:
# https://github.com/${REPO_OWNER}/${REPO_NAME}/security/code-scanning
```

Record findings in `SECURITY_AUDIT_FINDINGS.md` (create if missing):

```markdown
# Security Audit Findings - ${REPO_NAME}

Date: $(date +%Y-%m-%d)
Scanner: CodeQL / ${SCANNER_NAME}

| Rule ID | Severity | File | Line | Status |
|---------|----------|------|------|--------|
| ${rule_id} | ${severity} | ${file} | ${line} | open |
```

## Step 4: Analyze and Plan Fixes

For each finding:

1. Read the affected file and surrounding context.
2. Determine the root cause.
3. Design a minimal, behavior-preserving fix.
4. Verify the fix does not introduce new issues.

Document each finding in `SECURITY_AUDIT_FINDINGS.md` with:

- Root cause analysis
- Fix applied
- Evidence (before/after code snippets)
- Test results

## Step 5: Implement Fixes

Apply fixes file by file. General patterns:

### Example: Fixing a SQL Injection Finding

```python
# BEFORE (vulnerable)
query = f"SELECT * FROM users WHERE username = '{user_input}'"
cursor.execute(query)

# AFTER (fixed)
query = "SELECT * FROM users WHERE username = ?"
cursor.execute(query, (user_input,))
```

### Example: Fixing a Hardcoded Secret Finding

```python
# BEFORE (vulnerable)
API_KEY = "sk-1234567890abcdef"

# AFTER (fixed)
import os
API_KEY = os.environ.get("API_KEY", "REPLACE_ME")
```

### Example: Fixing a Path Traversal Finding

```python
# BEFORE (vulnerable)
file_path = os.path.join(base_dir, user_input)

# AFTER (fixed)
from pathlib import Path
requested = Path(user_input).resolve()
base = Path(base_dir).resolve()
if not requested.is_relative_to(base):
    raise ValueError("Path traversal detected")
file_path = requested
```

### General Rules

- **No new secrets**: Never commit real credentials; use `REPLACE_ME` placeholders.
- **No `shell=True`**: All `subprocess` calls must use argument lists.
- **No unsafe deserialization**: Use `tomllib`, `json` only; no `pickle`/`yaml.load`.
- **Fail-closed**: When in doubt, deny rather than allow.
- **Minimal changes**: Fix only the vulnerable code, not unrelated refactoring.

## Step 6: Validate the Fixes

Run the project's validation suite:

```bash
# Python projects
python -m compileall -q .
python -m ruff check .
python -m ruff format --check .
python -m mypy .
python -m pytest -q -p no:faulthandler -p no:cacheprovider

# Re-scan to confirm findings are resolved
gh api "repos/${REPO_OWNER}/${REPO_NAME}/code-scanning/alerts" \
  --jq '.[] | select(.state == "open")' \
  | jq length  # Should be 0 for fixed findings
```

Document results in `SECURITY_AUDIT_FINDINGS.md`:

```markdown
| Rule ID | File | Fix Applied | Test Result | Evidence State |
|---------|------|-------------|-------------|----------------|
| ${rule_id} | ${file} | ${fix_description} | PASS | VERIFIED |
```

## Step 7: Commit Changes

Commit with GPG signing:

```bash
git add -A
git commit -S -m "fix: remediate security code-scanning findings

Fix security vulnerabilities identified in code scanning:

- ${rule_id_1}: ${brief_description}
- ${rule_id_2}: ${brief_description}

All fixes validated with:
- compileall: PASS
- ruff check: PASS
- ruff format: PASS
- mypy: PASS
- pytest: ${TEST_COUNT} passed

Security impact: Reduces attack surface by fixing ${NUM_FIXES} findings.
Compatibility: Backward-compatible; no behavior changes.
Documentation: SECURITY_AUDIT_FINDINGS.md updated.
```

Verify the commit is signed:

```bash
git log --format="%H %G?" -1
# Should show: <SHA> G
```

## Step 8: Push and Open PR

```bash
git push origin feat/security-audit-fix-$(date +%Y%m%d)

gh pr create \
  --title "fix: remediate security code-scanning findings" \
  --body-file <(cat <<'EOF'
## Summary

Remediate security code-scanning findings in ${REPO_NAME}.

### Changes
- Fixed ${NUM_FIXES} security findings identified by code scanning
- Each fix includes root cause analysis, fix, and verification
- All changes are backward-compatible

### Validation
- compileall: PASS
- ruff check: PASS
- ruff format: PASS
- mypy: PASS
- pytest: ${TEST_COUNT} passed

### Security Impact
- Reduces attack surface by fixing ${NUM_FIXES} findings
- No new secrets introduced; placeholders used where needed
- Fail-closed defaults maintained

### Documentation
- SECURITY_AUDIT_FINDINGS.md updated with per-finding evidence

### Rollback
- Revert commit if any issue arises
EOF
) \
  --base main \
  --head feat/security-audit-fix-$(date +%Y%m%d)

PR_URL=$(gh pr view --json url --jq '.url')
echo "PR created: ${PR_URL}"
```

## Step 9: Independent Review (policedbc)

Switch to policedbc and review:

```bash
gh auth switch -u policedbc
gh auth status  # Verify: active account policedbc

# Review the PR
gh pr view ${PR_NUMBER} --json headRefOid --jq '.headRefOid'
gh pr diff ${PR_NUMBER}
gh pr checks ${PR_NUMBER}

# Approve
gh pr review ${PR_NUMBER} --approve --body "Independent review: Security fixes verified. All changes are minimal, behavior-preserving, and pass all validation gates. Security findings resolved."

# Verify approval
gh pr view ${PR_NUMBER} --json reviewDecision --jq '.reviewDecision'
# Should return: APPROVED
```

## Step 10: Merge (cvsz)

Switch back to cvsz and merge:

```bash
gh auth switch -u cvsz
gh auth status  # Verify: active account cvsz

# Verify exact HEAD SHA before merge
HEAD_SHA=$(gh pr view ${PR_NUMBER} --json headRefOid --jq '.headRefOid')
echo "HEAD SHA: ${HEAD_SHA}"

# Pre-merge verification
# - policedbc APPROVAL for exact HEAD SHA ✓
# - No new commits after approval ✓
# - CI/local validation green ✓
# - Mergeable, open, not draft ✓

# Merge with exact head commit enforcement
gh pr merge ${PR_NUMBER} --merge --match-head-commit --delete-branch
echo "Exit code: $?"

# Post-merge verification
git fetch origin
git checkout main
git pull origin main  # fast-forward
git log --oneline -1  # Verify merge commit present
```

## Step 11: Post-Merge Verification

```bash
# Verify code is present on main
git log --oneline -1 | grep "fix: remediate security"
# Should show the merge commit

# Verify CI is green on main
gh run list --branch main --limit 5 --status success
```

## Evidence State Definitions

Per `ZEAZ-INTRODUCTION.md`:

| State | Definition |
|-------|------------|
| VERIFIED | Reproducible evidence exists (test output, diff, artifact) |
| PARTIALLY VERIFIED | Some evidence exists but not complete |
| UNVERIFIED | No reproducible evidence yet |
| BLOCKED | Concrete prerequisite prevents verification |
| NOT APPLICABLE | Does not apply to this context |

A fix is `VERIFIED` only when test output and diff evidence exist.

## Rollback Plan

If any issue is discovered after merge:

1. Identify the merge commit SHA: `git log --oneline -1`
2. Revert: `git revert -m 1 <merge-commit-SHA>`
3. Push the revert: `git push origin main`
4. Or revert the feature branch commit and re-open PR

## Reusable Template

This skill is reusable across any cvsz repository. Replace `${REPO_NAME}` with the target repository name and adapt language-specific fix patterns as needed.

---

**Security:** Never commit credentials, tokens, or production endpoints. Use `REPLACE_ME` placeholders.

**GPG signing:** `commit.gpgsign=true` is required; merge commits are GPG-signed when cvsz merges.
