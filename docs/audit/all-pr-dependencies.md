# All Pull Request Dependencies — cvsz/autodj

Dependency-related changes across all PRs, and the dependency versions in effect on current `main`.

## Dependency-upgrade PRs (merged)

| PR | Dependency | Change | Advisory check |
|----|------------|--------|----------------|
| #80 | setuptools | `>=68` → `>=84.2.1` (`pyproject.toml` build-system requires) | No known advisory; required by current build |
| #106 | actions/checkout | 4.2.2 → 7.0.1 (SHA-pinned) | Pinned to immutable SHA |
| #107 | actions/setup-python | 5.6.0 → 7.1.0 (SHA-pinned) | Pinned to immutable SHA |
| #108 | actions/attest-build-provenance | 2.4.0 → 4.2.2 (SHA-pinned) | Pinned to immutable SHA |
| #82 | actions/upload-artifact | 4.6.2 → 7.0.2 (SHA-pinned) | Pinned to immutable SHA |
| #81 | actions/attest-build-provenance | 4.x → 4.2.2 (SHA-pinned) | Pinned to immutable SHA |
| #41 | softprops/action-gh-release | 2 → 3 (SHA-pinned) | Pinned to immutable SHA |
| #40 / #1 / #2 | github/codeql-action | 4.38.2 → 4.39.1 (SHA-pinned) | Pinned to immutable SHA |
| #83 | Various actions | P0 hardening — all action references SHA-pinned | Verified |

## Python dependencies (current `main`, `pyproject.toml`)

```
[project]
requires-python = ">=3.11"
dependencies:
  yt-dlp
  mutagen
  pyttsx3
  pywinauto; sys_platform == 'win32'
  pyperclip; sys_platform == 'win32'
[project.optional-dependencies]
dev = ["pytest"]
build = ["pyinstaller"]
build-system requires = ["setuptools>=84.2.1"]
```

- `pytest` (dev) — installed locally; 325 tests pass.
- `ruff`, `mypy`, `pyinstaller` — dev/build tooling, not runtime dependencies.
- All third-party deps ship without type stubs; `ignore_missing_imports = true` in mypy config so only AutoDJ's own code is type-checked.

## Dependency audit notes

- No Dependabot security advisory PRs are open; all Dependabot PRs were merged after compatibility review.
- Action versions are pinned to immutable SHAs (supply-chain policy); no floating tags.
- No `pip` dependency was blindly upgraded; each Dependabot PR was merged individually with its own CI run.
- No downgrades were used to conceal errors.
- Windows-specific deps (`pywinauto`, `pyperclip`) are gated behind `sys_platform == 'win32'` so Linux installs are unaffected.
