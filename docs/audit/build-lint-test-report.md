# Build, Lint and Test Report — cvsz/autodj

**Baseline SHA:** `9a5e829870d6cf11450a6ec56ff063f37aa616f8`
**Environment:** Linux (WSL), Python 3.11+, `pwsh` absent → Windows targets BLOCKED.

## Exact commands and results

| # | Command | Exit code | Result |
|---|---------|-----------|--------|
| 1 | `python -m compileall -q camfrog_autodj tests tools` | 0 | All modules compile |
| 2 | `python -m pytest -q -p no:faulthandler -p no:cacheprovider` | 0 | **325 passed, 3 subtests passed** (15.17s) |
| 3 | `ruff check camfrog_autodj tests tools` | 0 | All checks passed |
| 4 | `ruff format --check camfrog_autodj tests tools` | 0 | 56 files already formatted |
| 5 | `python -m mypy camfrog_autodj` | 0 | Success: no issues in 29 source files |
| 6 | `shellcheck scripts/*.sh tools/*.sh` | 0 | Pass (style notes: SC2181, SC2034 only) |
| 7 | `bash -n scripts/*.sh tools/*.sh` | 0 | All scripts syntactically valid |
| 8 | `python scripts/validate_repo.py` | 0 | Repository structure + local Markdown links valid |
| 9 | `git commit -S` (GPG test) + `git verify-commit HEAD` | 0 | **Good signature** from `cvsz (zcoder signing) <seaza@msn.com>` |
| 10 | `gh auth status` + `gh api user --jq .login` | 0 | **cvsz** active; `policedbc` available |
| 11 | `git grep` secret scan | 0 | No secrets/tokens/keys tracked |
| 12 | `python -c "import tomllib; ..."` on config*.toml | 0 | All TOML valid |
| 13 | YAML parse on `.github/workflows/*.yml` | 0 | All 7 workflow files valid |

## Makefile targets reviewed (not all executable here)

- `test`, `test-v`, `test-one`, `coverage`, `mutation-smoke` — `mutation-smoke` requires `tools/mutate.sh` which is **not present** (NOT APPLICABLE).
- `lint`, `fmt`, `typecheck` — executable; pass.
- `validate-playlists`, `fix-playlists` — use `tools/validate_playlists.py`.
- `validate-template` — `scripts/validate_repo.py`; passes.
- `full-validation` — lint + typecheck + validate-playlists + test + changelog-check + config-check.
- `build`, `build-clean`, `sign`, `build-all`, `installer`, `nsiswindows11`, `trustsign` — **Windows-only, BLOCKED**.
- `install-auto`, `build-all-linux` — Windows/Wine-only, BLOCKED.

## Notes

- No `|| echo warning` suppression used on critical operations.
- All genuine Ruff warnings fixed; only narrowly justified, documented suppressions remain (`pyproject.toml` `[tool.ruff.lint] ignore`).
- `changelog-check`: version `0.2.8` has a CHANGELOG entry.
- `config-check`: `config.toml` valid TOML with required keys.
