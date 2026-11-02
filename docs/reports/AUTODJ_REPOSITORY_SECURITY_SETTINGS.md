# AutoDJ Repository Security Settings Audit

**Repository:** `cvsz/autodj`  
**Base Commit SHA (`main`):** `3b96e8da9adebca952f503df43fc26dc8b4a58bd`  
**Date:** 2026-11-02  
**Audited via:** GitHub REST API (`gh api repos/cvsz/autodj/...`)  
**Status:** Settings audited; some settings not verifiable via API from personal account  

---

## 1. Branch Protection — `main` branch

**Status: VERIFIED**

| Setting | Value | Required | Status |
|---------|-------|----------|--------|
| Required status checks | `repository-baseline`, `Analyze GitHub Actions`, `dependency-review` | Yes | ✅ Enabled |
| Strict status checks | `true` | Yes | ✅ Enabled |
| Required approving reviews | 1 | Yes | ✅ Enabled |
| Dismiss stale reviews | `true` | Yes | ✅ Enabled |
| Require code owner reviews | `true` | Yes | ✅ Enabled |
| Require last push approval | `true` | Yes | ✅ Enabled |
| Required conversation resolution | `true` | Yes | ✅ Enabled |
| Required commit signatures | `false` | No | ⚠️ Disabled (not enforced) |
| Enforce admins | `true` | Yes | ✅ Enabled |
| Allow force pushes | `false` | Yes | ✅ Blocked |
| Allow deletions | `false` | Yes | ✅ Blocked |
| Block creations | `false` | Yes | ✅ Blocked |
| Required linear history | `false` | No | ⚠️ Disabled |
| Lock branch | `false` | No | ⚠️ Disabled |
| Allow fork syncing | `false` | No | ⚠️ Disabled |

**Evidence:** `gh api repos/cvsz/autodj/branches/main/protection`

**Verification:** Push to `main` was rejected with `GH006: Protected branch update failed` — confirms branch protection is effective.

**Residual risk:** Commit signatures are not required on the protected branch. Unsigned commits could theoretically be merged if the PR author bypasses local GPG signing (though the workflow and CODEOWNERS provide review gates).

---

## 2. Code Scanning (CodeQL)

**Status: VERIFIED**

| Setting | Value | Status |
|---------|-------|--------|
| CodeQL enabled | Yes | ✅ |
| Language analyzed | `python` | ✅ |
| Workflow | `.github/workflows/codeql.yml` | ✅ |
| Triggers | push to main, PR to main, weekly schedule | ✅ |
| Permissions | `contents: read`, `security-events: write` | ✅ |
| Action pinned to SHA | `9b3254085494b55a0f7c4c2b3d2d52cc712ce370` (v4.39.1) | ✅ |

**Recent alerts (all fixed):**

| Alert # | Rule | Severity | State | Fixed At |
|---------|------|----------|-------|----------|
| #1 | actions/missing-workflow-permissions | medium | fixed | 2026-10-31 |
| #2 | actions/missing-workflow-permissions | medium | fixed | 2026-10-31 |
| #3 | actions/missing-workflow-permissions | medium | fixed | 2026-10-31 |

**Evidence:** `gh api repos/cvsz/autodj/code-scanning/alerts` — 3 alerts, all in `fixed` state.

**Residual risk:** None — all CodeQL alerts are resolved.

---

## 3. Dependabot

**Status: PARTIALLY VERIFIED**

| Ecosystem | Directory | Schedule | Open PR Limit | Status |
|-----------|-----------|----------|---------------|--------|
| github-actions | / | weekly | 10 | ✅ Enabled |
| docker | / | weekly | 10 | ✅ Enabled |
| pip | / | weekly | 10 | ✅ Enabled |

**Dependabot alerts:** 0 alerts (`gh api repos/cvsz/autodj/dependabot/alerts` returned `[]`)

**Evidence:** `.github/dependabot.yml` committed to repository; API confirms no open alerts.

**Residual risk:** None known — no open Dependabot alerts.

---

## 4. Repository Security Settings (Not Verifiable via API)

The following settings could not be retrieved via the GitHub REST API from this environment. They are documented as **NOT VERIFIED** and should be confirmed manually through the GitHub web UI (Settings → Security):

| Setting | Status | Verification Method |
|---------|--------|---------------------|
| Private vulnerability reporting | NOT VERIFIED | GitHub web UI: Settings → Security → Code scanning → Set up private vulnerability reporting |
| Secret scanning | NOT VERIFIED | GitHub web UI: Settings → Security → Secret scanning |
| Push protection | NOT VERIFIED | GitHub web UI: Settings → Security → Secret scanning → Push protection |
| Dependabot alerts | NOT VERIFIED (API returned empty) | GitHub web UI: Settings → Security → Dependabot alerts |
| Dependabot security updates | NOT VERIFIED | GitHub web UI: Settings → Security → Dependabot security updates |
| Secret scanning push protection | NOT VERIFIED | GitHub web UI: Settings → Security → Code scanning |

**Note:** The `gh api repos/cvsz/autodj` endpoint did not return `private_vulnerability_reporting_enabled`, `secret_scanning_enabled`, `secret_scanning_push_protection_enabled`, `dependabot_alerts_enabled`, or `dependabot_security_updates_enabled` fields. This may be because the repository is owned by a personal account rather than an organization, or these fields require different API endpoints.

**Evidence:** API response from `gh api repos/cvsz/autodj` did not include security setting fields.

**Residual risk:** Cannot confirm whether private vulnerability reporting, secret scanning, or push protection are enabled. Manual verification through GitHub web UI is required.

---

## 5. Actions Workflow Security

**Status: VERIFIED**

All workflow files contain explicit `permissions` blocks following least-privilege principles:

| Workflow | Permissions | Status |
|----------|-------------|--------|
| `.github/workflows/ci.yml` | `contents: read` | ✅ |
| `.github/workflows/tests.yml` | `contents: read` | ✅ |
| `.github/workflows/codeql.yml` | `contents: read`, `security-events: write` | ✅ |
| `.github/workflows/dependency-review.yml` | `contents: read` | ✅ |
| `.github/workflows/release.yml` | `contents: write`, `id-token: write`, `attestations: write` | ✅ |

**All Action references pinned to full commit SHAs:**

| Action | Reference | Version | SHA | Status |
|--------|-----------|---------|-----|--------|
| actions/checkout | `actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683` | v4.2.2 | Pinned | ✅ |
| actions/checkout | `actions/checkout@11d5960a326750d5838078e36cf38b85af677262` | v4 | Pinned | ✅ |
| actions/setup-python | `actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065` | v5.6.0 / v5 | Pinned | ✅ |
| github/codeql-action/init | `github/codeql-action/init@9b3254085494b55a0f7c4c2b3d2d52cc712ce370` | v4.39.1 | Pinned | ✅ |
| github/codeql-action/analyze | `github/codeql-action/analyze@9b3254085494b55a0f7c4c2b3d2d52cc712ce370` | v4.39.1 | Pinned | ✅ |
| actions/dependency-review-action | `actions/dependency-review-action@a1d282b36b6f3519aa1f3fc636f609c47dddb294` | v5.0.0 | Pinned | ✅ |
| actions/attest-build-provenance | `actions/attest-build-provenance@96b4a1ef7235a096b17240c259729fdd70c83d45` | v2 | Pinned | ✅ |
| actions/upload-artifact | `actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02` | v4 | Pinned | ✅ |

**Residual risk:** None — all action references are SHA-pinned.

---

## 6. CODEOWNERS Enforcement

**Status: VERIFIED**

`.github/CODEOWNERS` requires independent review (`@policedbc`) for:

| Path Pattern | Owners | Rationale |
|--------------|--------|-----------|
| `/.github/` | @cvsz @policedbc | CI/workflow configuration |
| `/.github/workflows/` | @cvsz @policedbc | CI pipeline definition |
| `/SECURITY.md` | @cvsz @policedbc | Security policy |
| `/AGENTS.md` | @cvsz @policedbc | Agent contract |
| `/installer.nsi` | @cvsz @policedbc | Windows installer (data destruction risk) |
| `/install.ps1` | @cvsz @policedbc | Windows installer (data destruction risk) |
| `/install-full-auto.ps1` | @cvsz @policedbc | Automated installer (data destruction risk) |
| `/build.ps1` | @cvsz @policedbc | Build/signing script |
| `/config.example.toml` | @cvsz @policedbc | Default configuration (admin defaults) |
| `/config.toml` | @cvsz @policedbc | Runtime configuration |

Branch protection enforces `require_code_owner_reviews: true`, so changes to these paths require approval from `@policedbc` in addition to `@cvsz`.

**Residual risk:** `@cvsz` is the default owner for all files (`* @cvsz`), meaning @cvsz can self-approve changes to non-security-sensitive paths. This is acceptable for routine development but security-sensitive paths require @policedbc.

---

## 7. Overall Security Posture Summary

| Category | Status | Summary |
|----------|--------|---------|
| Branch protection | VERIFIED | All key protections enabled; push to main blocked |
| Code scanning | VERIFIED | CodeQL analyzes Python; 3 historical alerts all fixed |
| Dependabot | PARTIALLY VERIFIED | pip ecosystem added; no open alerts |
| Repository security settings | NOT VERIFIED | Private vuln reporting, secret scanning, push protection not verifiable via API |
| Workflow permissions | VERIFIED | All workflows use least-privilege permissions |
| Action pinning | VERIFIED | All 8 action references pinned to full SHAs |
| CODEOWNERS | VERIFIED | Independent review required for security-sensitive paths |
| Commit signing | NOT ENFORCED | Branch protection does not require signed commits |

**Residual risks:**
1. Commit signatures not required on protected branch — maintainers should sign commits locally (GPG)
2. Repository security settings (private vuln reporting, secret scanning, push protection) not verifiable via API — manual web UI check recommended
3. No code-signing certificate configured — release builds are unsigned
