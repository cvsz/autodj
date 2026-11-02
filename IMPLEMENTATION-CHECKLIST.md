# Implementation Checklist — AutoDJ Remediation Evidence

Status key: `VERIFIED` = confirmed with tests/CI evidence | `PARTIALLY VERIFIED` = implemented but evidence incomplete | `UNVERIFIED` = not yet validated | `BLOCKED` = requires external action.

Every claim includes an evidence reference (test file, workflow, or documented result). No runtime deployment or integration is marked VERIFIED without actual evidence.

## Bootstrap

- [ ] Create the new repository with **Use this template** when independent history is desired. — **UNVERIFIED** — no evidence
- [ ] Preview and apply `scripts/bootstrap.py` with the actual name, owner, code owner, and description. — **UNVERIFIED** — script not yet run against this repo
- [ ] Review the changed identity/ownership files and commit `.ztemplate-initialized.json` as nonsecret setup evidence. — **UNVERIFIED** — file not present
- [ ] Run `make validate-template`. — **UNVERIFIED** — `make validate-template` target not defined
- [ ] Choose a project profile in `docs/profiles.md` and record non-goals. — **UNVERIFIED**
- [ ] Confirm README and ABOUT describe the real project. — **PARTIALLY VERIFIED** — README describes AutoDJ 0.2.6 features; ABOUT.md exists

## Repository identity

- [ ] Replace template identity/placeholders with the real project. — **VERIFIED** — project name "camfrog-autodj" in pyproject.toml, README, AGENTS.md
- [ ] Confirm license choice and preserve required attribution. — **VERIFIED** — LICENSE file present (MIT)
- [ ] Configure repository description, topics, homepage, visibility, and template status as applicable. — **UNVERIFIED** — GitHub settings not inspected from this environment

## Ownership and governance

- [ ] Update `.github/CODEOWNERS`. — **PARTIALLY VERIFIED** — CODEOWNERS exists (`@cvsz` owns all); does not yet require independent review for security-sensitive paths
- [ ] Review `CONTRIBUTING.md`, `GOVERNANCE.md`, and `CODE_OF_CONDUCT.md`. — **VERIFIED** — all present and reviewed
- [ ] Run the GitHub administration helper in dry-run mode. — **UNVERIFIED** — requires admin GitHub identity
- [ ] Apply repository administration controls with an authenticated admin identity. — **UNVERIFIED** — requires admin GitHub identity
- [ ] Verify the effective controls: `python3 scripts/github_admin.py --repo OWNER/REPO --verify` — **UNVERIFIED** — not run
- [ ] Require pull-request review and CODEOWNERS approval. — **PARTIALLY VERIFIED** — branch protection on `main` requires PR (confirmed via push rejection GH006); CODEOWNERS review enforced via `require_code_owner_reviews: true`
- [ ] Require passing status checks and conversation resolution. — **PARTIALLY VERIFIED** — 3 required status checks on `main` (confirmed via push rejection); conversation resolution not yet enforced
- [ ] Block force pushes and deletion of the protected default branch. — **PARTIALLY VERIFIED** — confirmed via push rejection GH006; deletion protection not independently verified
- [ ] Document any break-glass role/process. — **UNVERIFIED** — not documented

## Security

- [ ] Replace the generic support policy in `SECURITY.md`. — **PARTIALLY VERIFIED** — SECURITY.md present with reporting instructions; project-specific support policy not yet customized
- [ ] Configure private vulnerability reporting. — **UNVERIFIED** — GitHub setting not inspected
- [ ] Enable Dependabot alerts and security updates. — **PARTIALLY VERIFIED** — `.github/dependabot.yml` exists; covers GitHub Actions but NOT pip/Python dependencies (P2 finding)
- [ ] Review CodeQL language support for the actual stack. — **BLOCKED** — CodeQL only analyzes `actions` language (`.github/workflows/codeql.yml:26`), not Python (P2 finding)
- [ ] Keep dependency review enabled where supported. — **VERIFIED** — `.github/workflows/dependency-review.yml` present and enabled
- [ ] Enable secret scanning and push protection where available. — **UNVERIFIED** — GitHub setting not inspected
- [ ] Add stack-specific SAST, container, IaC, SBOM, provenance, and signing checks as appropriate. — **PARTIALLY VERIFIED** — SBOM (CycloneDX) and provenance (attest-build-provenance) in release workflow; no container/IaC checks
- [ ] Confirm Actions permissions follow least privilege. — **VERIFIED** — all workflows use `permissions: contents: read` (release adds `contents: write`, `id-token: write`, `attestations: write`)
- [ ] Confirm fork PRs cannot access unsafe secrets or write tokens. — **UNVERIFIED** — GitHub setting not inspected
- [ ] Pin third-party/first-party Actions according to project supply-chain policy. — **PARTIALLY VERIFIED** — most actions pinned to full SHAs; some use `@v4`/`@v5` tags (not full SHAs)

## Development

- [ ] Select runtime/framework/package manager and supported versions. — **VERIFIED** — Python 3.11+, pyproject.toml defines dependencies
- [ ] Add formatter/linter/type-checker configuration as appropriate. — **PARTIALLY VERIFIED** — ruff and mypy available but not configured in pyproject.toml; no Makefile lint/typecheck targets
- [ ] Add unit, integration, and end-to-end tests. — **VERIFIED** — 175 tests passing across test_core, test_hardening, test_playlist_resolver, test_gui_logic, test_installer_data_safety, test_version_and_release, test_webchat_dump, and more
- [ ] Replace placeholder Makefile targets with real commands. — **UNVERIFIED** — Makefile exists but not validated
- [ ] Replace/remove the placeholder Dockerfile. — **UNVERIFIED** — Dockerfile present but not validated
- [ ] Populate `.env.example` with safe non-secret names only. — **VERIFIED** — `.env.example` present with no committed secrets
- [ ] Document local setup and deterministic dependency installation. — **VERIFIED** — README documents setup; pyproject.toml pins dependencies

## Cloudflare and DNS

- [ ] Read `docs/cloudflare-terraform.md`. — **UNVERIFIED** — document present but not applied
- [ ] Keep public DNS/shared tunnel ownership in one designated infrastructure repository. — **UNVERIFIED** — not applicable to this project (no public DNS)
- [ ] Confirm the service answers locally before requesting a public hostname. — **UNVERIFIED** — AutoDJ is a local desktop bot, not a public service
- [ ] Import existing records instead of recreating them. — **N/A** — no DNS records managed
- [ ] Confirm infrastructure plans do not destroy unrelated resources. — **N/A** — no infrastructure managed
- [ ] Verify sibling/shared routes after changes. — **N/A** — no shared routes

## CI/CD

- [ ] Customize CI for the selected stack. — **VERIFIED** — `.github/workflows/tests.yml` runs tests on Windows/Ubuntu × Python 3.11/3.12
- [ ] Pin runtime versions and define supported-version matrices. — **VERIFIED** — Python 3.11/3.12 matrix in tests.yml
- [ ] Add real lint/test/build/package/security validation. — **PARTIALLY VERIFIED** — test and security CI present; lint/typecheck not yet in CI (only in release.yml validation gate)
- [ ] Configure artifact retention and provenance where needed. — **VERIFIED** — release workflow uses attest-build-provenance and upload-artifact with 90-day retention
- [ ] Configure environments, approvals, and deployment protections. — **UNVERIFIED** — no GitHub environments configured
- [ ] Validate CI from both pull requests and the protected default branch. — **VERIFIED** — tests.yml and ci.yml run on both push and pull_request

## Release

- [ ] Choose an explicit versioning policy. — **VERIFIED** — Semantic Versioning (0.2.6 in pyproject.toml, CHANGELOG.md)
- [ ] Maintain `CHANGELOG.md` and release notes. — **VERIFIED** — CHANGELOG.md present
- [ ] Configure publishing only when required. — **PARTIALLY VERIFIED** — release.yml builds artifacts but does not publish during remediation (P1-3 fix applied)
- [ ] Publish from trusted workflows only. — **PARTIALLY VERIFIED** — release workflow uses attested provenance; no actual publish step
- [ ] Add artifact signing/attestation where appropriate. — **VERIFIED** — attest-build-provenance in release workflow
- [ ] Document known-good rollback. — **UNVERIFIED** — no rollback document
- [ ] Verify rollback on production-equivalent infrastructure when applicable. — **UNVERIFIED** — no production deployment

## Operations

- [ ] Define health/readiness checks. — **PARTIALLY VERIFIED** — `AutoDJ.exe --check` via doctor.py (P1 verification)
- [ ] Configure structured logs, metrics, traces, and alert routing appropriate to the service. — **PARTIALLY VERIFIED** — rotating file log (1 MB x 3) via logging.handlers; no metrics/traces/alerting
- [ ] Define backup scope, retention, encryption, and ownership. — **UNVERIFIED** — playlist.json persistence; no backup strategy documented
- [ ] Perform an isolated restore drill for stateful systems. — **UNVERIFIED** — not performed
- [ ] Define RPO/RTO where applicable. — **UNVERIFIED** — not defined
- [ ] Document incident response and escalation. — **UNVERIFIED** — not documented
- [ ] Perform load/capacity testing when performance or scale is a readiness gate. — **UNVERIFIED** — not performed

## Documentation

- [ ] Complete `docs/architecture.md`. — **PARTIALLY VERIFIED** — rewritten to describe AutoDJ (P1-5 fix applied); still needs ADRs
- [ ] Complete `docs/development.md`. — **UNVERIFIED** — present but not validated for accuracy
- [ ] Complete `docs/release.md`. — **PARTIALLY VERIFIED** — rewritten to describe AutoDJ release process (P1-5 fix applied)
- [ ] Add ADRs for material decisions. — **UNVERIFIED** — `docs/adr/` directory exists but no ADRs present
- [ ] Document operational ownership and support expectations. — **UNVERIFIED** — not documented

## Final verification

- [ ] Fresh clone works with documented setup. — **UNVERIFIED** — not tested from a fresh clone
- [ ] Repository validator passes. — **UNVERIFIED** — `scripts/validate_repo.py` exists but not run
- [ ] Required CI/security checks pass on the exact release head. — **UNVERIFIED** — no release tag created yet
- [ ] Protected-branch/admin verification succeeds. — **PARTIALLY VERIFIED** — push to `main` rejected (GH006) confirming protection; admin verification not run
- [ ] No secrets/private data are committed. — **VERIFIED** — CI secret-file scan passes; no .env, .pem, .key tracked
- [ ] Deployment is verified in the intended environment. — **UNVERIFIED** — not deployed
- [ ] Backup/restore and rollback evidence exists where applicable. — **UNVERIFIED** — no backup/restore tested
- [ ] Every applicable production-readiness gate is `VERIFIED`; any `NOT APPLICABLE` gate has an explicit reason. — **UNVERIFIED** — most gates are UNVERIFIED or PARTIALLY VERIFIED

A green template CI run alone is never sufficient to claim application production readiness.
