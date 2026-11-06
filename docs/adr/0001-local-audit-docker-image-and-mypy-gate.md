# ADR 0001: Local audit Docker image `zpostgresql` and mypy CI gate configuration

- Status: Accepted
- Date: 2026-11-06
- Owners: @cvsz

## Context

The repository shipped a generic placeholder Dockerfile (`FROM alpine:3.24` with an echo CMD) that could not build or audit anything. The implementation checklist marked "Replace/remove the placeholder Dockerfile" as UNVERIFIED. Reviewers/auditors had no reproducible local container for running the project's test suite, lint, and type checks.

Separately, the Release workflow's Gate 1 runs `mypy camfrog_autodj` as a strict typecheck gate. On the release head it failed with 8 errors in 5 files: missing type stubs for third-party dependencies (`pywinauto`, `pyttsx3`, `mutagen`, `yt_dlp`, `pyperclip`) that AutoDJ cannot control. A broken release gate blocks every tag push.

## Decision

1. Replace the placeholder Dockerfile with a `python:3.11-slim`-based image that installs the project with dev dependencies, self-verifies at build time (`ruff check`, `ruff format --check`, full `pytest` suite), and defaults to running the test suite. Build and tag it locally as `zpostgresql:latest` (alias `zpostgresql:audit`) for audit/reviewer use.
2. Add `[tool.mypy] ignore_missing_imports = true` to `pyproject.toml` so the mypy release gate type-checks AutoDJ's own code instead of failing on unstubbed third-party dependencies.
3. Run `ruff format` so the codebase complies with the project's own pre-commit format step (`fmt lint test`), and make `ruff format --check` part of the Docker image build gate.

## Alternatives considered

- Install type stubs (`types-*`) in CI: rejected because several dependencies (pywinauto, pyttsx3, mutagen) have no official/maintained stubs, so the gate would remain fragile.
- Keep the placeholder Dockerfile: rejected; it provides no audit value and contradicts AGENTS.md guidance to replace Makefile/Dockerfile placeholders before enabling a delivery pipeline.
- Suppress BLE001 broadly: rejected; only the deliberate defensive catch in `camfrog_autodj/__main__.py` (auto-launch best-effort) is kept, with `# noqa: BLE001` placed on the same line as `Exception` so `ruff format` cannot strand it.

## Consequences

Positive: reviewers can run `docker build -t zpostgresql:latest . && docker run --rm zpostgresql:latest` from any host with Docker; the release typecheck gate passes on the exact head; lint/format/tests are consistent between local and CI.

Negative: `ignore_missing_imports = true` means mypy will not flag genuinely mistyped calls into unstubbed third-party modules; AutoDJ code itself is still fully checked.

Image runs as non-root user `autodj`; build requires network access to PyPI.

## Validation

- `docker build -t zpostgresql:latest -t zpostgresql:audit .` succeeds (build-time self-verification passes).
- `docker run --rm zpostgresql:latest` exits 0 (323 passed, 3 subtests passed).
- Local: `ruff check` passes, `ruff format --check` passes, `mypy camfrog_autodj` succeeds, `python -m pytest` passes 323 + 3 subtests.
