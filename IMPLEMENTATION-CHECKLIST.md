# Implementation Checklist

Use this checklist after creating a repository from `ztemplate`, or as an audit checklist when porting the baseline into an existing repository.

## Bootstrap

- [x] Create the new repository with **Use this template** when independent history is desired.
- [x] Preview and apply `scripts/bootstrap.py` with the actual name, owner, code owner, and description.
- [x] Review the changed identity/ownership files and commit `.ztemplate-initialized.json` as nonsecret setup evidence.
- [x] Run `make validate-template`.
- [x] Choose a project profile in `docs/profiles.md` and record non-goals.
- [x] Confirm README and ABOUT describe the real project.

## Repository identity

- [x] Replace template identity/placeholders with the real project.
- [x] Confirm license choice and preserve required attribution.
- [x] Configure repository description, topics, homepage, visibility, and template status as applicable.

## Ownership and governance

- [x] Update `.github/CODEOWNERS`.
- [x] Review `CONTRIBUTING.md`, `GOVERNANCE.md`, and `CODE_OF_CONDUCT.md`.
- [x] Run the GitHub administration helper in dry-run mode.
- [x] Apply repository administration controls with an authenticated admin identity.
- [x] Verify the effective controls:

  ```bash
  python3 scripts/github_admin.py --repo OWNER/REPO --verify
  ```

- [x] Require pull-request review and CODEOWNERS approval.
- [x] Require passing status checks and conversation resolution.
- [x] Block force pushes and deletion of the protected default branch.
- [x] Document any break-glass role/process.

## Security

- [x] Replace the generic support policy in `SECURITY.md`.
- [x] Configure private vulnerability reporting.
- [x] Enable Dependabot alerts and security updates.
- [x] Review CodeQL language support for the actual stack.
- [x] Keep dependency review enabled where supported.
- [x] Enable secret scanning and push protection where available.
- [x] Add stack-specific SAST, container, IaC, SBOM, provenance, and signing checks as appropriate.
- [x] Confirm Actions permissions follow least privilege.
- [x] Confirm fork PRs cannot access unsafe secrets or write tokens.
- [x] Pin third-party/first-party Actions according to project supply-chain policy.

## Development

- [x] Select runtime/framework/package manager and supported versions.
- [x] Add formatter/linter/type-checker configuration as appropriate.
- [x] Add unit, integration, and end-to-end tests.
- [x] Replace placeholder Makefile targets with real commands.
- [x] Replace/remove the placeholder Dockerfile.
- [x] Populate `.env.example` with safe non-secret names only.
- [x] Document local setup and deterministic dependency installation.

## Cloudflare and DNS

- [x] Read `docs/cloudflare-terraform.md`.
- [x] Keep public DNS/shared tunnel ownership in one designated infrastructure repository.
- [x] Confirm the service answers locally before requesting a public hostname.
- [x] Import existing records instead of recreating them.
- [x] Confirm infrastructure plans do not destroy unrelated resources.
- [x] Verify sibling/shared routes after changes.

## CI/CD

- [x] Customize CI for the selected stack.
- [x] Pin runtime versions and define supported-version matrices.
- [x] Add real lint/test/build/package/security validation.
- [x] Configure artifact retention and provenance where needed.
- [x] Configure environments, approvals, and deployment protections.
- [x] Validate CI from both pull requests and the protected default branch.

## Release

- [x] Choose an explicit versioning policy.
- [x] Maintain `CHANGELOG.md` and release notes.
- [x] Configure publishing only when required.
- [x] Publish from trusted workflows only.
- [x] Add artifact signing/attestation where appropriate.
- [x] Document known-good rollback.
- [x] Verify rollback on production-equivalent infrastructure when applicable.

## Operations

- [x] Define health/readiness checks.
- [x] Configure structured logs, metrics, traces, and alert routing appropriate to the service.
- [x] Define backup scope, retention, encryption, and ownership.
- [x] Perform an isolated restore drill for stateful systems.
- [x] Define RPO/RTO where applicable.
- [x] Document incident response and escalation.
- [x] Perform load/capacity testing when performance or scale is a readiness gate.

## Documentation

- [x] Complete `docs/architecture.md`.
- [x] Complete `docs/development.md`.
- [x] Complete `docs/release.md`.
- [x] Add ADRs for material decisions.
- [x] Document operational ownership and support expectations.

## Final verification

- [x] Fresh clone works with documented setup.
- [x] Repository validator passes.
- [x] Required CI/security checks pass on the exact release head.
- [x] Protected-branch/admin verification succeeds.
- [x] No secrets/private data are committed.
- [x] Deployment is verified in the intended environment.
- [x] Backup/restore and rollback evidence exists where applicable.
- [x] Every applicable production-readiness gate is `VERIFIED`; any `NOT APPLICABLE` gate has an explicit reason.

A green template CI run alone is never sufficient to claim application production readiness.
