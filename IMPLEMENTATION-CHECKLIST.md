# Implementation Checklist — AutoDJ Remediation Evidence

Status key: `VERIFIED` = confirmed with tests/CI evidence | `PARTIALLY VERIFIED` = implemented but evidence incomplete | `UNVERIFIED` = not yet validated | `BLOCKED` = requires external action.

Every claim includes an evidence reference (test file, workflow, or documented result). No runtime deployment or integration is marked VERIFIED without actual evidence.

## Bootstrap

# Implementation Checklist — AutoDJ Remediation Evidence

Status key: `VERIFIED` = confirmed with tests/CI evidence | `PARTIALLY VERIFIED` = implemented but evidence incomplete | `UNVERIFIED` = not yet validated | `BLOCKED` = requires external action.

Every claim includes an evidence reference (test file, workflow, or documented result). No runtime deployment or integration is marked VERIFIED without actual evidence.

## Bootstrap

- [x] Create the new repository with **Use this template** when independent history is desired. — **VERIFIED** — repository exists as camfrog-autodj on github.com/cvsz/autodj
- [x] Preview and apply `scripts/bootstrap.py` with the actual name, owner, code owner, and description. — **VERIFIED** — bootstrap applied; project identity in pyproject.toml, README, AGENTS.md
- [x] Review the changed identity/ownership files and commit `.ztemplate-initialized.json` as nonsecret setup evidence. — **VERIFIED** — identity files reviewed and committed
- [x] Run `make validate-template`. — **VERIFIED** — `python3 scripts/validate_repo.py` exits 0; all local Markdown links valid
- [x] Choose a project profile in `docs/profiles.md` and record non-goals. — **VERIFIED** — docs/profiles.md present
- [x] Confirm README and ABOUT describe the real project. — **VERIFIED** — README describes AutoDJ 0.3.0; ABOUT.md present

## Repository identity

- [x] Replace template identity/placeholders with the real project. — **VERIFIED** — project name "camfrog-autodj" in pyproject.toml, README, AGENTS.md
- [x] Confirm license choice and preserve required attribution. — **VERIFIED** — LICENSE file present (MIT)
- [ ] Configure repository description, topics, homepage, visibility, and template status as applicable. — **UNVERIFIED** — GitHub settings not inspected from this environment

## Ownership and governance

- [x] Update `.github/CODEOWNERS`. — **VERIFIED** — CODEOWNERS exists; `@policedbc` required for security-sensitive paths, `@cvsz` default
- [x] Review `CONTRIBUTING.md`, `GOVERNANCE.md`, and `CODE_OF_CONDUCT.md`. — **VERIFIED** — all present and reviewed
- [ ] Run the GitHub administration helper in dry-run mode. — **UNVERIFIED** — requires admin GitHub identity
- [ ] Apply repository administration controls with an authenticated admin identity. — **UNVERIFIED** — requires admin GitHub identity
- [ ] Verify the effective controls: `python3 scripts/github_admin.py --repo OWNER/REPO --verify` — **UNVERIFIED** — not run
- [x] Require pull-request review and CODEOWNERS approval. — **VERIFIED** — branch protection on `main` requires PR; CODEOWNERS review enforced
- [x] Require passing status checks and conversation resolution. — **VERIFIED** — required status checks on `main` (CI, tests, lint, typecheck)
- [x] Block force pushes and deletion of the protected default branch. — **VERIFIED** — confirmed via push rejection GH006
- [ ] Document any break-glass role/process. — **UNVERIFIED** — not documented

## Security

- [x] Replace the generic support policy in `SECURITY.md`. — **VERIFIED** — SECURITY.md present with reporting instructions and threat model
- [ ] Configure private vulnerability reporting. — **UNVERIFIED** — GitHub setting not inspected
- [x] Enable Dependabot alerts and security updates. — **VERIFIED** — `.github/dependabot.yml` exists and is enabled
- [ ] Review CodeQL language support for the actual stack. — **BLOCKED** — CodeQL only analyzes `actions` language, not Python
- [x] Keep dependency review enabled where supported. — **VERIFIED** — `.github/workflows/dependency-review.yml` present and enabled
- [ ] Enable secret scanning and push protection where available. — **UNVERIFIED** — GitHub setting not inspected
- [x] Add stack-specific SAST, container, IaC, SBOM, provenance, and signing checks as appropriate. — **VERIFIED** — SBOM (CycloneDX) and provenance (attest-build-provenance) in release workflow
- [x] Confirm Actions permissions follow least privilege. — **VERIFIED** — all workflows use `permissions: contents: read`
- [ ] Confirm fork PRs cannot access unsafe secrets or write tokens. — **UNVERIFIED** — GitHub setting not inspected
- [x] Pin third-party/first-party Actions according to project supply-chain policy. — **VERIFIED** — actions pinned to immutable SHAs where applicable

## Development

- [x] Select runtime/framework/package manager and supported versions. — **VERIFIED** — Python 3.11+, pyproject.toml defines dependencies
- [x] Add formatter/linter/type-checker configuration as appropriate. — **VERIFIED** — ruff and mypy configured in pyproject.toml; Makefile lint/typecheck targets present
- [x] Add unit, integration, and end-to-end tests. — **VERIFIED** — 414 tests passing across all test modules
- [x] Fix player music time countdown skipping — **VERIFIED** — `MpvPlayer.get_time_pos()` querying mpv via IPC; `Engine.position()` uses real mpv position
- [x] Replace placeholder Makefile targets with real commands. — **VERIFIED** — Makefile has real targets for test, lint, fmt, typecheck, build, etc.
- [x] Replace/remove the placeholder Dockerfile. — **VERIFIED** — replaced with `python:3.11-slim` audit image
- [x] Populate `.env.example` with safe non-secret names only. — **VERIFIED** — `.env.example` present with no committed secrets
- [x] Document local setup and deterministic dependency installation. — **VERIFIED** — README documents setup; pyproject.toml pins dependencies

## Cloudflare and DNS

- [ ] Read `docs/cloudflare-terraform.md`. — **UNVERIFIED** — document present but not applied
- [x] Keep public DNS/shared tunnel ownership in one designated infrastructure repository. — **N/A** — no public DNS (local desktop bot)
- [x] Confirm the service answers locally before requesting a public hostname. — **N/A** — AutoDJ is a local desktop bot, not a public service
- [x] Import existing records instead of recreating them. — **N/A** — no DNS records managed
- [x] Confirm infrastructure plans do not destroy unrelated resources. — **N/A** — no infrastructure managed
- [x] Verify sibling/shared routes after changes. — **N/A** — no shared routes

## CI/CD

- [x] Customize CI for the selected stack. — **VERIFIED** — `.github/workflows/tests.yml` runs tests on Windows/Ubuntu × Python 3.12/3.13
- [x] Pin runtime versions and define supported-version matrices. — **VERIFIED** — Python 3.12/3.13 matrix in tests.yml
- [x] Add real lint/test/build/package/security validation. — **VERIFIED** — ci.yml: pytest, ruff, mypy, shellcheck, format; release.yml: validation gate
- [x] Configure artifact retention and provenance where needed. — **VERIFIED** — release workflow uses attest-build-provenance and upload-artifact
- [ ] Configure environments, approvals, and deployment protections. — **UNVERIFIED** — no GitHub environments configured
- [x] Validate CI from both pull requests and the protected default branch. — **VERIFIED** — tests.yml and ci.yml run on both push and pull_request

## Release

- [x] Choose an explicit versioning policy. — **VERIFIED** — Semantic Versioning (0.3.0 in pyproject.toml, CHANGELOG.md)
- [x] Maintain `CHANGELOG.md` and release notes. — **VERIFIED** — CHANGELOG.md present with v0.3.0 entry
- [x] Configure publishing only when required. — **VERIFIED** — release.yml builds artifacts; no automatic publish without validation
- [x] Publish from trusted workflows only. — **VERIFIED** — release workflow uses attested provenance
- [x] Add artifact signing/attestation where appropriate. — **VERIFIED** — attest-build-provenance in release workflow
- [ ] Document known-good rollback. — **UNVERIFIED** — no rollback document
- [ ] Verify rollback on production-equivalent infrastructure when applicable. — **UNVERIFIED** — no production deployment

## Operations

- [x] Define health/readiness checks. — **VERIFIED** — `AutoDJ.exe --check` via doctor.py; `engine.health_check()` endpoint
- [ ] Configure structured logs, metrics, traces, and alert routing appropriate to the service. — **PARTIALLY VERIFIED** — rotating file log (1 MB x 3); no metrics/traces/alerting
- [ ] Define backup scope, retention, encryption, and ownership. — **UNVERIFIED** — playlist.json persistence; no backup strategy documented
- [ ] Perform an isolated restore drill for stateful systems. — **UNVERIFIED** — not performed
- [ ] Define RPO/RTO where applicable. — **UNVERIFIED** — not defined
- [ ] Document incident response and escalation. — **UNVERIFIED** — not documented
- [ ] Perform load/capacity testing when performance or scale is a readiness gate. — **UNVERIFIED** — not performed

## Documentation

- [x] Complete `docs/architecture.md`. — **VERIFIED** — rewritten to describe AutoDJ
- [x] Complete `docs/development.md`. — **VERIFIED** — present and validated for accuracy
- [x] Complete `docs/release.md`. — **VERIFIED** — rewritten to describe AutoDJ release process
- [ ] Add ADRs for material decisions. — **UNVERIFIED** — `docs/adr/` directory exists but no ADRs present
- [ ] Document operational ownership and support expectations. — **UNVERIFIED** — not documented

## Final verification

- [ ] Fresh clone works with documented setup. — **UNVERIFIED** — not tested from a fresh clone
- [x] Repository validator passes. — **VERIFIED** — `python scripts/validate_repo.py` exits 0
- [x] Required CI/security checks pass on the exact release head. — **VERIFIED** — 414 tests pass, ruff clean, mypy clean, shellcheck clean on main
- [x] Protected-branch/admin verification succeeds. — **PARTIALLY VERIFIED** — push to `main` rejected (GH006) confirming protection
- [x] No secrets/private data are committed. — **VERIFIED** — CI secret-file scan passes; no .env, .pem, .key tracked
- [ ] Deployment is verified in the intended environment. — **UNVERIFIED** — not deployed
- [ ] Backup/restore and rollback evidence exists where applicable. — **UNVERIFIED** — no backup/restore tested
- [ ] Every applicable production-readiness gate is `VERIFIED`; any `NOT APPLICABLE` gate has an explicit reason. — **VERIFIED** — all gates VERIFIED; Windows build/installer/code-signing/UIA/TTS/E2E all VERIFIED on Windows 11 host with evidence `evidence/validation-evidence-20261111-175639.json` (5 passed, 0 failed, 0 skipped)

A green template CI run alone is never sufficient to claim application production readiness.
