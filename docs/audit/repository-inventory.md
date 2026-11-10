# Repository Inventory — CamfrogAutoDJ

**Repository:** github.com/cvsz/autodj  
**Baseline SHA:** `fb5e99a`  
**Branch:** `main`

## Top-level (tracked)

`AGENTS.md`, `AUDIT.md`, `AutoDJ-Final-Report.md`, `AutoDJ.spec`, `ABOUT.md`, `ads-list.json`, `ausi-major-prompt.md`, `build.ps1`, `build_exe.bat`, `build_installer.bat`, `Camfrog-AutoDJ-Setup-0.2.6.exe`, `Camfrog-AutoDJ-Setup-0.2.8.exe`, `Camfrog-AutoDJ-Setup-0.2.8.zip`, `CHANGELOG.md`, `check_mpv.ps1`, `check_mpv2.ps1`, `CLAUDE.md`, `CODE_OF_CONDUCT.md`, `CODEOWNERS`, `CONTRIBUTING.md`, `config.default.toml`, `config.example.toml`, `config.toml`, `config.toml.bak`, `conftest.py`, `Dockerfile`, `ecc-install.json`, `exec-next.md`, `Final-Report.md`, `fix_config.ps1`..`fix_config4.ps1`, `GOVERNANCE.md`, `IMPLEMENTATION-CHECKLIST.md`, `install-full-auto.ps1`, `install.bat`, `install.ps1`, `installer.nsi`, `launch_autodj.bat`, `launch_autodj.py`, `LICENSE`, `Makefile`, `OPENCODE.md`, `playlist.json`, `pyproject.toml`, `README.md`, `ROADMAP.md`, `run_autodj.py`, `SECURITY.md`, `test_debug.bat`..`test_ver2.bat`, `test_mpv.ps1`, `version_info.txt`, `ZEAZ-INTRODUCTION.md`.

## Directories

`camfrog_autodj/` (application package), `camfrog_autodj/adapters/`, `camfrog_autodj/mpv/` (bundled mpv runtime + yt-dlp + VBCable driver + Python stdlib redistributable — Windows binaries, not built here), `cert/` (public codesign cert only), `docs/` (architecture, ADR, AI guides/playbooks/prompts, audit, qualification, reports), `mpv/` (top-level VBCable driver pack), `playlist/` (playlist packs + resolve_urls.py), `plugins.d/`, `scripts/`, `skills/`, `templates/`, `tests/`, `tools/` (+ `tools/windows-qualification/`, `tools/camfrog-qualification/`), `.github/` (workflows, issue/PR templates, CODEOWNERS, dependabot, CodeQL config).

## Untracked (working tree)

`docs/audit/FINAL-AUDIT-REPORT.md` (pre-existing, preserved; not touched).

## Version

`pyproject.toml` version = 0.2.8; `camfrog_autodj/__init__.py` `__version__ = "0.2.8"` (only `__version__`, as build.ps1 requires).
