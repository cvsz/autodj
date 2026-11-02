# Camfrog AutoDJ — Validation Evidence Report

**Repository:** `cvsz/autodj`  
**Base Commit SHA (`main`):** `572aad9` (Merge PR #56)  
**Date:** 2026-11-02  
**Auditor:** ZEAZDEV Super Ultra AI ORC  

---

## 1. Test Suite Evidence

### Command and Result

```
python -m pytest -q -p no:faulthandler -p no:cacheprovider
```

**Result:** 175 passed, 3 subtests passed in ~4 seconds

### Test Files and Coverage

| Test File | Purpose |
|-----------|---------|
| `tests/test_core.py` | Core engine: queue, commands, parsing, host validation, aliases |
| `tests/test_hardening.py` | Regression tests for v0.2.0 audit findings (F1-F13) + new authorization tests |
| `tests/test_playlist_resolver.py` | Playlist yt-dlp TLS and resolution tests |
| `tests/test_gui_logic.py` | GUI logic against strict fake Tk |
| `tests/test_gui_i18n.py` | GUI internationalization (EN/TH) |
| `tests/test_installer_data_safety.py` | NSIS installer data preservation on upgrade/uninstall |
| `tests/test_play_flow.py` | Play flow end-to-end tests |
| `tests/test_version_and_release.py` | Version consistency across pyproject.toml, __init__.py, version_info.txt |
| `tests/test_webchat_dump.py` | Web chat dump parsing (shaped after real room dump) |
| `tests/test_executable_paths.py` | Executable path resolution tests |
| `tests/test_discover.py` | Auto-discovery tests |
| `tests/test_background_clip.py` | Background clipboard tests |
| `tests/test_pytest_compat.py` | Pytest compatibility tests |
| `tests/test_v030_fixes.py` | v0.2.3 regression tests |
| `tests/fake_tk.py` | Strict fake Tk for GUI logic tests |
| `tests/conftest.py` | Test configuration and fixtures |

### New Authorization Tests Added

Added to `tests/test_hardening.py`:
1. `test_admin_authorization_is_case_insensitive` — Admin nicks match case-insensitively
2. `test_local_console_is_always_admin` — Local console trusted even with no admins configured
3. `test_non_admin_cannot_run_admin_command` — Non-admin gets "admin only" reply
4. `test_admin_can_run_admin_command` — Admin can execute admin commands
5. `test_blocked_user_cannot_be_admin` — Blocked admin self-block rejected
6. `test_blocked_user_ignored_silently` — Blocked users produce no room noise

---

## 2. CI Workflow Evidence

### `.github/workflows/tests.yml`

- **Triggers:** push, pull_request
- **Matrix:** Windows/Ubuntu × Python 3.11/3.12
- **Steps:** Checkout → Setup Python → Install deps → Run tests
- **Permissions:** `contents: read`
- **Concurrency:** Group cancel-in-progress

### `.github/workflows/ci.yml`

- **Triggers:** push to main, pull_request
- **Jobs:** `repository-baseline` (validate_repo.py, bootstrap tests, secret scan, YAML validation)
- **Permissions:** `contents: read`

### `.github/workflows/release.yml` (Remediated)

- **Triggers:** push tags matching `v*`
- **Job 1 — `validate-release`** (ubuntu-latest):
  - Checkout, Setup Python, Install deps (pytest, ruff, mypy)
  - Run unit tests
  - Ruff lint (`ruff check .`)
  - Strict mypy typecheck (`mypy camfrog_autodj`)
  - Secret file scan
  - Outputs `go=true` only if all pass
- **Job 2 — `build-installer`** (windows-latest, `needs: validate-release`):
  - Checkout, Setup Python, Install deps (pyinstaller, cyclonedx-bom)
  - Install NSIS (choco)
  - Build AutoDJ.exe (`build.ps1 -Clean -NoSign`)
  - Build NSIS installer (`makensis`)
  - Generate CycloneDX SBOM
  - Generate SHA256 checksums
  - Attest build provenance (`actions/attest-build-provenance@v2`)
  - Upload artifacts (90-day retention)
- **No automatic release publication** — manual creation required

### `.github/workflows/codeql.yml` (Remediated)

- **Languages:** `python` (was `actions`)
- **Triggers:** push to main, pull_request to main, weekly schedule
- **Permissions:** `contents: read`, `security-events: write`

### `.github/workflows/dependency-review.yml`

- **Triggers:** pull_request to main
- **Action:** `actions/dependency-review-action@v5.0.0` (pinned to full SHA)
- **Permissions:** `contents: read`

---

## 3. Protected Branch Evidence

**Push to `main` was attempted and rejected:**

```
remote: error: GH006: Protected branch update failed for refs/heads/main.
remote: - Changes must be made through a pull request.
remote: - 3 of 3 required status checks are expected.
```

This confirms:
- `main` is a protected branch
- Changes require a pull request
- 3 required status checks are enforced

---

## 4. Configuration Validation Evidence

### Version Consistency (`test_versions_agree`)

Verifies that `pyproject.toml`, `camfrog_autodj/__init__.py`, and `version_info.txt` all declare the same version (`0.2.6`).

**Result:** PASSED

### Config Example Validity (`test_shipped_example_config_is_valid`)

Verifies that `config.example.toml` loads without `ConfigError`.

**Result:** PASSED

### Config Value Validation (`test_config_value_validation`)

Parametrized test rejecting:
- `admins = "zdevz"` (string instead of list)
- `lang = "de"` (invalid choice)
- `volume = 150` (out of range)
- `volume = "loud"` (wrong type)
- `send_mode = "sideways"` (invalid choice)
- `view_kind = 3` (wrong type)
- `window_title_re = "(unclosed"` (invalid regex)
- `prefix = ""` (empty prefix)
- `shuffle = "yes"` (wrong type)

**Result:** ALL PASSED

---

## 5. Installer Safety Evidence

### `tests/test_installer_data_safety.py`

1. `test_installer_preserves_existing_user_config_on_upgrade`:
   - Asserts `IfFileExists "$INSTDIR\config.toml" config_exists` in installer.nsi
   - Asserts `File /oname=config.toml config.example.toml` in installer.nsi

2. `test_uninstaller_removes_only_application_owned_files`:
   - Asserts `RMDir /r "$INSTDIR"` NOT in uninstall section (no bulk deletion)
   - Asserts `Delete "$INSTDIR\AutoDJ.exe"` in uninstall section
   - Asserts `RMDir "$INSTDIR"` in uninstall section
   - Asserts "Keep config.toml, playlist.json, logs, playlists" comment in uninstall

**Result:** PASSED

---

## 6. Items NOT Verified (Require External Environment)

| Item | Reason |
|------|--------|
| CI workflow execution on remediation branch | No push to remote; CI not triggered |
| CodeQL analysis results | CodeQL requires GitHub Actions execution |
| Dependabot PR generation | Dependabot requires GitHub App installation |
| Windows installer compilation | Requires Windows runner with NSIS and choco |
| Code-signing verification | No code-signing certificate configured |
| GPG tag signing | No GPG key configured in this environment |
| PowerShell installer script testing | Linux environment cannot execute .ps1 |
| Real Camfrog / mpv / yt-dlp integration | Not available in this environment |
| GUI smoke test (real Tk) | No display available in this environment |

---

## 7. Evidence Summary

| Category | Status | Evidence |
|----------|--------|----------|
| Unit tests | PASSED | 175 passed, 3 subtests |
| Regression tests | PASSED | All F1-F13 hardening tests pass |
| Authorization tests | PASSED | 6 new tests pass |
| Config validation | PASSED | All invalid configs rejected |
| Version consistency | PASSED | pyproject.toml, __init__.py, version_info.txt in sync |
| Installer safety | PASSED | NSIS content safety tests pass |
| Protected branch | VERIFIED | Push rejected (GH006), 3 required checks |
| CI workflows | UPDATED | Release workflow gated; CodeQL uses Python; lint/typecheck fail on error |
| Secret scan | PASSED | No tracked secret files |
| Dependabot | UPDATED | pip ecosystem added |
| CODEOWNERS | UPDATED | Independent review for security-sensitive paths |
