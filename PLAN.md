# Makefile fix plan

## Problem
`make all` / `make validate-all` fail on Linux because `validate-installer`
requires Windows-only build artifacts (`dist/AutoDJ.exe`, `mpv/VBCABLE_Driver_Pack45`,
etc.) and Windows NSIS commands. This breaks cross-platform verification.

## Changes
1. `tools/validate_installer.py` — skip gracefully on non-Windows hosts so
   `make all` / `make validate-all` work everywhere (Windows primary, Linux
   headless). On Windows, run the full fail-closed NSIS validation unchanged.

## Verification
- `make all` → exit 0 on Linux
- `make validate-all` → exit 0 on Linux
- `python -m compileall`, `ruff`, `ruff format --check`, `mypy`, `pytest`,
  `shellcheck` all still pass
