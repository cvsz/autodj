# AutoDJ Release Process

## Scope

This document describes how AutoDJ releases are built, validated, and published. It replaces the generic template release guidance with AutoDJ-specific gates and evidence requirements.

## Versioning

AutoDJ uses Semantic Versioning (MAJOR.MINOR.PATCH). The current version is `0.3.0`, declared in:
- `pyproject.toml` (`version = "0.3.0"`)
- `camfrog_autodj/__init__.py` (`__version__ = "0.3.0"`)
- `version_info.txt` (Windows file version resource)
- `CHANGELOG.md` (changelog entries)

`tests/test_version_and_release.py::test_versions_agree` verifies all three stay in sync.

## Release gating

No release is created or published automatically. The release workflow (`.github/workflows/release.yml`) enforces the following sequence:

### Gate 1 — Validation (ubuntu-latest, Python 3.12/3.13)

Must pass before any build artifact is produced:

1. **Checkout** the exact tag commit
2. **Install dependencies** (`-e .`, pytest, ruff, mypy)
3. **Run unit tests** — `python -m pytest -q -p no:faulthandler -p no:cacheprovider` (baseline: 414 passed)
4. **Lint** — `ruff check camfrog_autodj tests tools`
5. **Format check** — `ruff format --check camfrog_autodj tests tools`
6. **Strict typecheck** — `mypy camfrog_autodj`
7. **Shell lint** — `shellcheck scripts/*.sh tools/*.sh`
8. **Secret scan** — rejects any tracked `.env`, `id_rsa`, `id_ed25519`, `*.pem`, `*.key` (except `.env.example`)

If any gate fails, the job fails and the release is blocked.

### Gate 2 — Build (windows-latest)

Runs only if Gate 1 passed:

1. **Checkout** the exact tag commit
2. **Install dependencies** (`-e .`, pyinstaller, cyclonedx-bom)
3. **Install NSIS** (choco)
4. **Build AutoDJ.exe** — `build.ps1 -Clean -NoSign` (no automatic signing during remediation)
5. **Build NSIS installer** — `makensis /DVERSION=<tag> installer.nsi`
6. **Generate CycloneDX SBOM** — `cyclonedx-py environment`
7. **Generate SHA256 checksums** — `SHA256SUMS.txt`
8. **Attest build provenance** — `actions/attest-build-provenance@v2`
9. **Upload artifacts** — 90-day retention

## Release checklist

1. Confirm the release commit is the intended exact head (`git rev-parse <tag>^{}`)
2. Ensure Gate 1 + Gate 2 checks pass on that exact head (CI evidence)
3. Confirm protected-branch/admin controls are effective (push to `main` rejected with GH006)
4. Update `CHANGELOG.md` and compatibility/migration notes
5. GPG-sign the annotated tag: `git tag -s vX.Y.Z -m "Release X.Y.Z"`
6. Verify the tag SHA matches the CI-validated commit
7. Create the release manually with artifacts, SBOM, checksums
8. Record release evidence in `docs/reports/`
9. Do not deploy to production without explicit authorization

## Rollback

Documented rollback paths:
- **Last known-good artifact:** previous GitHub Release assets remain available
- **Application rollback:** uninstall previous version, reinstall previous MSI/exe
- **Configuration rollback:** `config.toml.bak` is created by auto-discovery; operator can restore manually
- **No data migration** is required between versions (playlist.json is forward-compatible)

A rollback document without environment-appropriate execution evidence is not proof that recovery will work.

## Production readiness

Release authorization and production readiness are distinct. A maintainer may authorize a release with accepted risk, but accepted risk does not convert unverified readiness gates into verified. The following gates remain UNVERIFIED as of remediation:
- Deployment in intended environment
- Backup/restore drill
- Load/capacity testing
- Incident response drill
