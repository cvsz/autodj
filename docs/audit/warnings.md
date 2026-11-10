# Warnings — CamfrogAutoDJ

**Repository:** github.com/cvsz/autodj  
**Baseline SHA:** `fb5e99a`

## Lint warnings

- `ruff check camfrog_autodj tests tools`: **pass, no warnings.**
- `ruff format --check`: **pass, 57 files formatted.**
- One import-sort fix applied to the new test file (`ruff check --fix`); re-verified clean.

## ShellCheck warnings (style only, not defects)

- `scripts/build_installer_linux.sh:77` — SC2181 (check exit code directly).
- `scripts/deploy-workflow-all-repos.sh:19` — SC2034 (`ACCOUNTS_FILE` unused).
- `scripts/gh-switch.sh:49` — SC2034 (`ORIG_URL` unused).

These are pre-existing style notes in multi-repo tooling scripts, outside the application core. No `|| echo warning` suppression was used; no lint failure was swallowed.

## mypy

Not executed as a gate (CI mypy step tolerates pre-existing issues due to missing stubs for pywinauto/pyttsx3/mutagen/yt_dlp/pyperclip). `mypy ignore_missing_imports = true` in `pyproject.toml`.
