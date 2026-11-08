# Repository Inventory — cvsz/autodj

**Root:** `/mnt/d/data/camfrog-autodj`
**Baseline SHA:** `9a5e829870d6cf11450a6ec56ff063f37aa616f8`
**Working tree:** 2 modified (user-owned) files — `Final-Report.md`, `camfrog_autodj/gui.py` (preserved, not overwritten).

## Top-level files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Project config: Python >=3.11, deps, scripts, ruff/mypy/pytest config |
| `Makefile` | Dev targets: test, lint, fmt, typecheck, build, package, ci, full-validation |
| `config.default.toml` | Documented defaults (46 settings) |
| `config.example.toml` | Example config (relative `mpv_path`/`ytdlp_path`) |
| `config.toml` | Local config (user-owned, not overwritten) |
| `config.toml.bak` | Config backup (user-owned) |
| `AutoDJ.spec` | PyInstaller spec (mirrors `build.ps1`) |
| `build.ps1` / `build_exe.bat` / `build_installer.bat` | Windows build scripts |
| `installer.nsi` | NSIS installer script |
| `install.ps1` / `install.bat` | Automated Windows 11 installer |
| `app.ico` / `version_info.txt` | App icon + version metadata |
| `ads-list.json` | Auto-reply messages |
| `playlist.json` | Playlist data |
| `autodj.log` | Runtime log |
| `LICENSE`, `README.md`, `CHANGELOG.md`, `ROADMAP.md`, `SECURITY.md`, `GOVERNANCE.md`, `CONTRIBUTING.md`, `AUDIT.md`, `ABOUT.md`, `IMPLEMENTATION-CHECKLIST.md`, `AGENTS.md`, `ZEAZ-INTRODUCTION.md`, `ausi-master-prompt.md`, `CLAUDE.md`, `OPENCODE.md`, `Final-Report.md`, `AutoDJ-Final-Report.md` | Governance + docs |
| `.gitattributes`, `.gitignore`, `.editorconfig`, `.dockerignore`, `Dockerfile` | Repo tooling |
| `CODEOWNERS`, `codeql-config.yml`, `dependabot.yml`, `FUNDING.yml`, `linguist.yml`, `PULL_REQUEST_TEMPLATE.md`, `release.yml`, `SUPPORT.md` | GitHub config |

## Python package: `camfrog_autodj/` (29 modules)

`__init__.py`, `__main__.py`, `adapters/{base,console,logtail,uia}.py`, `commands.py`, `config.py`, `discover.py`, `doctor.py`, `engine.py`, `gui.py`, `launcher.py`, `library.py`, `messages.py`, `migrate.py`, `models.py`, `paths.py`, `player.py`, `playlist.py`, `playqueue.py`, `textutil.py`, `tts.py`, `visuals.py`, `webchat.py`, `windows.py`, `winmsg.py`, `clipkeys.py`, `mpv/{_internal,d3dcompiler_43.dll,mpv-register.bat,mpv-unregister.bat,mpv.com,mpv.exe}` (bundled mpv binary).

## Tests: `tests/` (24 files)

`fake_tk.py`, `playlist.json`, `test_autodj_enhancements.py`, `test_background_clip.py`, `test_bootstrap.py`, `test_concurrency.py`, `test_core.py`, `test_discover.py`, `test_executable_paths.py`, `test_gui_i18n.py`, `test_gui_logic.py`, `test_hardening.py`, `test_installer_data_safety.py`, `test_migration.py`, `test_play_flow.py`, `test_playlist_resolver.py`, `test_production_remediation.py`, `test_pytest_compat.py`, `test_v030_fixes.py`, `test_version_and_release.py`, `test_webchat_dump.py`, `test_windows_build_script.py`, `test_windows_qualification_scripts.py`.

## Tools: `tools/` (11 files)

`check_build_env.py`, `inspect_ui.py`, `make_cert.ps1`, `minipytest.py`, `mutate.sh`, `package.py`, `sign_exe.ps1`, `validate_playlists.py`, plus `camfrog-qualification/`, `windows-qualification/`.

## Scripts: `scripts/` (15 files)

`audit-repo.sh`, `audit-all-repos.sh`, `auto-fix-loop.sh`, `bootstrap.py`, `build_installer_linux.sh`, `build_installer_wrapper.ps1`, `build_installer.ps1`, `build_windows.ps1`, `build-all-hybrid.ps1`, `deploy-workflow-all-repos.sh`, `gh-switch-accounts.conf`, `gh-switch.sh`, `github_admin.py`, `validate_repo.py`.

## GitHub: `.github/`

`workflows/{ci,tests,release,codeql,dependency-review,auto-fix-open-prs,automated-audit-review-approve}.yml`, `ISSUE_TEMPLATE/`, `CODEOWNERS`, plus `ISSUE_TEMPLATE/`, `scripts/`.

## Branches (local)

`main` (current), plus feature/fix/docs/qual/release/style/sync/pr/test branches including `chore/sync-release-0.2.5-and-quality`, `docs/sync-all-documentation`, `feat/autodj-enhancements-and-fixes`, `fix/*`, `qual/*`, `release/v0.2.7`, `release/v0.2.8-production`, `pr80`. Remote `origin/main` tracked; `main` == `origin/main`.
