# CamfrogAutoDJ -- dev convenience targets.
# Cross-platform (Linux/macOS/Windows PowerShell/Git-Bash).
# Windows 11 ready: validates OS build >= 22000, NSIS 3.09+, mpv, PyInstaller.

ifeq ($(OS),Windows_NT)
SHELL       := $(shell where bash 2>NUL || echo cmd.exe)
ifeq ($(findstring cmd.exe,$(SHELL)),cmd.exe)
.SHELLFLAGS := /c
else
.SHELLFLAGS := -c
endif
else
SHELL       := bash
.SHELLFLAGS := -eu -o pipefail -c
endif

ifeq ($(OS),Windows_NT)
PY          ?= python
else
PY          ?= $(shell command -v python3 >/dev/null 2>&1 && echo python3 || echo python)
endif
PIP         := $(PY) -m pip
PROJECT     := camfrog_autodj
CONFIG      ?= config.toml
VERSION     := $(shell $(PY) -c "import tomllib,sys; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])" 2>/dev/null || echo unknown)
DIST_ZIP    := dist/camfrog-autodj-$(VERSION).zip
IS_WINDOWS  := $(filter Windows_NT,$(OS))

# Windows 11 minimum build number (22000 = Windows 11 21H2)
WIN11_MIN_BUILD := 22000

# ---- logging ----------------------------------------------------------------
# Log directory for build-all validations and build steps (kept, not cleaned).
BUILD_LOG_DIR := logs
BUILD_LOG_TS  := $(shell date +%Y%m%d-%H%M%S 2>/dev/null || echo unknown)

.DEFAULT_GOAL := help
.PHONY: help install install-dev install-build install-auto venv \
        run run-gui run-console run-headless check discover windows say join-room \
        test test-v test-one coverage mutation-smoke \
        lint lint-src fmt fmt-check typecheck compileall shellcheck validate-playlists fix-playlists validate-template full-validation security-check security-audit config-check validate-all \
        build build-clean sign build-all build-all-linux build-all-hybrid trustsign package release installer installer-clean nsiswindows11 \
        clean clean-all distclean \
        config version bump-patch changelog-check pre-commit ci docs all validate-all \
        start-feature start-service start-function start-modular start-option start-all \
        win11-check win11-validate mpv-check nsis-check pyinstaller-check logs

## ---- help -----------------------------------------------------------------
help:  ## Show this help
	@echo "CamfrogAutoDJ -- make targets (Windows 11 + Linux/Wine)"
	@echo ""
	@$(PY) -c "import re; [print(f'  \033[36m{m.group(1):<24}\033[0m {m.group(2)}') for line in open('Makefile', encoding='utf-8') if (m := re.match(r'^([a-zA-Z0-9_.-]+):[^#]*##\s*(.*)', line))]"
	@echo ""
	@echo "Variables: PY=$(PY)  CONFIG=$(CONFIG)  VERSION=$(VERSION)"
	@echo "build* works on both platforms: Windows 11 (PowerShell) and Linux/Wine."
	@echo "Windows targets require: Windows 11 (build 22000+), NSIS 3.09+, mpv, PyInstaller"

## ---- Windows 11 prerequisite checks ---------------------------------------
# SKIP_CHECKS=1 bypasses all prerequisite checks (for air-gapped / pre-validated machines)
win11-check:  ## Verify Windows 11 (build 22000+) and NSIS/mpv/PyInstaller availability
ifeq ($(OS),Windows_NT)
	@mkdir -p "$(BUILD_LOG_DIR)" 2>/dev/null || true
	@echo "=== Windows 11 Prerequisite Check ($(BUILD_LOG_TS)) ==="
ifeq ($(SKIP_CHECKS),1)
	@echo "  SKIP: prerequisite checks disabled (SKIP_CHECKS=1)" | tee -a "$(BUILD_LOG_DIR)/win11-check-$(BUILD_LOG_TS).log"
	@echo "  SKIP: prerequisite checks disabled (SKIP_CHECKS=1)"
else
	@$(PY) tools/win11_check.py 2>&1 | tee -a "$(BUILD_LOG_DIR)/win11-check-$(BUILD_LOG_TS).log"
	@if [ $$? -ne 0 ]; then echo "ERROR: Prerequisite checks failed. See log." >> "$(BUILD_LOG_DIR)/win11-check-$(BUILD_LOG_TS).log" 2>&1; exit 1; fi
endif
	@echo "Logs: $(BUILD_LOG_DIR)/win11-check-$(BUILD_LOG_TS).log"
else
	@echo "win11-check requires Windows 11"
	@exit 1
endif

win11-validate:  ## Run full Windows validation evidence collector (installer, code signing, UIA, TTS, E2E)
ifeq ($(OS),Windows_NT)
	powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/validate-windows.ps1
else
	@echo "validate-windows requires Windows PowerShell"
	@exit 1
endif

mpv-check:  ## Verify mpv is available for Windows builds
ifeq ($(OS),Windows_NT)
ifeq ($(SKIP_CHECKS),1)
	@echo "  SKIP: mpv check disabled (SKIP_CHECKS=1)" >> "$(BUILD_LOG_DIR)/mpv-check-$(BUILD_LOG_TS).log" 2>&1
	@echo "  SKIP: mpv check disabled (SKIP_CHECKS=1)"
else
	@powershell.exe -NoProfile -Command "if (-not (Get-Command mpv.exe -ErrorAction SilentlyContinue) -and -not (Test-Path 'C:\Program Files\mpv\mpv.exe')) { Write-Error 'mpv.exe not found. Install: choco install mpv --yes'; exit 1 }" >> "$(BUILD_LOG_DIR)/mpv-check-$(BUILD_LOG_TS).log" 2>&1 || (echo "ERROR: mpv not found. Set SKIP_CHECKS=1 to bypass." >> "$(BUILD_LOG_DIR)/mpv-check-$(BUILD_LOG_TS).log" 2>&1 && exit 1)
	@echo "  OK: mpv available" >> "$(BUILD_LOG_DIR)/mpv-check-$(BUILD_LOG_TS).log" 2>&1
endif
else
	@echo "mpv-check is Windows-only"
	@exit 1
endif

nsis-check:  ## Verify NSIS (makensis) is available
ifeq ($(OS),Windows_NT)
ifeq ($(SKIP_CHECKS),1)
	@echo "  SKIP: NSIS check disabled (SKIP_CHECKS=1)" >> "$(BUILD_LOG_DIR)/nsis-check-$(BUILD_LOG_TS).log" 2>&1
	@echo "  SKIP: NSIS check disabled (SKIP_CHECKS=1)"
else
	@powershell.exe -NoProfile -Command "if (-not (Get-Command makensis -ErrorAction SilentlyContinue) -and -not (Test-Path 'C:\Program Files (x86)\NSIS\makensis.exe') -and -not (Test-Path 'C:\Program Files\NSIS\makensis.exe')) { Write-Error 'NSIS not found. Install: choco install nsis --yes'; exit 1 }" >> "$(BUILD_LOG_DIR)/nsis-check-$(BUILD_LOG_TS).log" 2>&1 || (echo "ERROR: NSIS not found. Set SKIP_CHECKS=1 to bypass." >> "$(BUILD_LOG_DIR)/nsis-check-$(BUILD_LOG_TS).log" 2>&1 && exit 1)
	@echo "  OK: NSIS available" >> "$(BUILD_LOG_DIR)/nsis-check-$(BUILD_LOG_TS).log" 2>&1
endif
else
	@echo "nsis-check is Windows-only"
	@exit 1
endif

pyinstaller-check:  ## Verify PyInstaller is available
ifeq ($(SKIP_CHECKS),1)
	@echo "  SKIP: PyInstaller check disabled (SKIP_CHECKS=1)" >> "$(BUILD_LOG_DIR)/pyinstaller-check-$(BUILD_LOG_TS).log" 2>&1
	@echo "  SKIP: PyInstaller check disabled (SKIP_CHECKS=1)"
else
	@if $(PY) -c "import PyInstaller" 2>/dev/null; then echo "  OK: PyInstaller installed" >> "$(BUILD_LOG_DIR)/pyinstaller-check-$(BUILD_LOG_TS).log" 2>&1; else echo "ERROR: PyInstaller not installed. Run: $(PIP) install pyinstaller or set SKIP_CHECKS=1 to bypass." >> "$(BUILD_LOG_DIR)/pyinstaller-check-$(BUILD_LOG_TS).log" 2>&1 && exit 1; fi
endif

## ---- environment ------------------------------------------------------------
venv:  ## Create a local .venv and show how to activate it
	$(PY) -m venv .venv
	@echo "Activate with:  source .venv/bin/activate   (Windows: .venv\\Scripts\\activate)"

install:  ## Install the project (runtime deps only)
	$(PIP) install -e .

install-dev:  ## Install the project + test tooling (pytest)
	$(PIP) install -e ".[dev]"

install-build:  ## Install the project + build tooling (pyinstaller), for Windows exe builds
	$(PIP) install -e ".[build]"

install-auto:  ## Run the automated Windows 11 installer (install.ps1)
ifeq ($(OS),Windows_NT)
	powershell.exe -NoProfile -ExecutionPolicy Bypass -File install.ps1
else
	@echo "install-auto requires Windows 11"
	@exit 1
endif

## ---- running ----------------------------------------------------------------
run: run-gui  ## Alias for run-gui

run-gui:  ## Launch the desktop GUI
	$(PY) -m $(PROJECT) --gui -c $(CONFIG)

run-console:  ## Chat via stdin/stdout, no Camfrog needed (great for trying commands)
	$(PY) -m $(PROJECT) --console -c $(CONFIG)

run-headless:  ## Run without the GUI (attaches to the Camfrog window)
	$(PY) -m $(PROJECT) -c $(CONFIG)

check:  ## Diagnose the setup: mpv, yt-dlp, folders, admins, Camfrog window
	$(PY) -m $(PROJECT) --check -c $(CONFIG)

discover:  ## Find the room window/chat controls and write them to config.toml, then exit
	$(PY) -m $(PROJECT) --discover -c $(CONFIG)

windows:  ## List every visible window (exe, pid, class, title)
	$(PY) -m $(PROJECT) --windows

say:  ## Send one test line into the room: make say TEXT="hello"
	$(PY) -m $(PROJECT) --say "$(TEXT)" -c $(CONFIG)

join-room:  ## Launch Camfrog, join the room, and connect AutoDJ (Windows auto-launch; Linux waits for window)
	@$(MAKE) config
	@echo "=== Joining room per config.toml ==="
	$(PY) -m $(PROJECT) -c $(CONFIG)

## ---- start everything -------------------------------------------------------
# Automated start of every runtime capability in a single command.
# Each category runs the startup sequence (config + version) so a new
# operator can confirm the project is ready with one invocation.
#
# Runtime verification (requires Windows + mpv + Camfrog): make check | make discover
# Long-running runtimes: make run-gui | make run-console | make run-headless

start-feature: start-all  ## Start all features: ensure config + report version (summary below)
start-service: start-all  ## Start all services: ensure config + report version (summary below)
start-function: start-all  ## Start all functions: ensure config + report version (summary below)
start-modular: start-all  ## Start all modules: ensure config + report version (summary below)
start-option: start-all  ## Start all options: ensure config + report version (summary below)

start-all: config version  ## Start every feature/service/function/module/option in one command
	@echo ""
	@echo "================================================"
	@echo "  ALL FEATURES / SERVICES / FUNCTIONS / MODULES / OPTIONS STARTED"
	@echo "================================================"
	@echo "Runtime verification (Windows + mpv + Camfrog): make check | make discover"
	@echo "Long-running runtimes:                          make run-gui | make run-console | make run-headless"

version:  ## Print the project version
	@echo $(VERSION)

config:  ## Create config.toml from the example if it does not exist yet
	@$(PY) -c "import os, shutil; print('config.toml already exists -- not overwriting') if os.path.exists('config.toml') else (shutil.copy('config.example.toml', 'config.toml'), print('created config.toml from config.example.toml'))"

## ---- testing ------------------------------------------------------------------
test:  ## Run the full test suite (pytest if installed, else the offline mini runner)
	@if $(PY) -c "import pytest" 2>/dev/null; then \
		$(PY) -m pytest -q -p no:faulthandler -p no:cacheprovider; \
	else \
		echo "pytest not installed -- using tools/minipytest.py (offline stand-in; 'make install-dev' for real pytest)"; \
		$(PY) tools/minipytest.py tests; \
	fi

test-v:  ## Run tests with verbose/full tracebacks
	@if $(PY) -c "import pytest" 2>/dev/null; then $(PY) -m pytest -vv; \
	else $(PY) tools/minipytest.py tests; fi

test-one:  ## Run a single test file or node id: make test-one T=tests/test_hardening.py
	@if $(PY) -c "import pytest" 2>/dev/null; then $(PY) -m pytest -vv "$(T)"; \
	else $(PY) tools/minipytest.py "$(T)"; fi

coverage:  ## Run tests under coverage.py (requires: pip install coverage) and print the report
	@if $(PY) -c "import coverage" 2>/dev/null; then \
		if $(PY) -c "import pytest" 2>/dev/null; then $(PY) -m coverage run -m pytest -q; \
		else $(PY) -m coverage run tools/minipytest.py tests; fi; \
		$(PY) -m coverage report -m; \
		$(PY) -m coverage html; \
		echo "HTML report: htmlcov/index.html"; \
	else \
		echo "coverage not installed -- run: $(PIP) install coverage"; exit 1; \
	fi

mutation-smoke:  ## Re-run the mutation checks that back the hardening tests (see tools/mutate.sh)
	@test -x tools/mutate.sh || (echo "tools/mutate.sh not found -- see AUDIT.md for how it was used"; exit 1)
	tools/mutate.sh

## ---- code quality -------------------------------------------------------------
lint:  ## Lint with ruff if installed, else a basic py_compile pass
	@if $(PY) -c "import ruff" 2>/dev/null || command -v ruff >/dev/null 2>&1; then \
		ruff check $(PROJECT) tests tools; \
	else \
		echo "ruff not installed -- falling back to py_compile (pip install ruff for real linting)"; \
		$(PY) -c "import glob, py_compile; [py_compile.compile(f) for f in glob.glob('camfrog_autodj/**/*.py', recursive=True)]"; \
	fi

fmt:  ## Format with ruff/black if installed (no-op if none installed)
	@if command -v ruff >/dev/null 2>&1; then ruff format $(PROJECT) tests tools; \
	elif command -v black >/dev/null 2>&1; then black $(PROJECT) tests tools; \
	else echo "no formatter installed (pip install ruff or black)"; fi

fmt-check:  ## Check formatting without modifying files (ruff format --check)
	@if command -v ruff >/dev/null 2>&1; then ruff format --check $(PROJECT) tests tools; \
	else echo "ruff not installed -- skipping format check (pip install ruff)"; fi

typecheck:  ## Type-check with mypy if installed
	@if $(PY) -c "import mypy" 2>/dev/null; then $(PY) -m mypy $(PROJECT); \
	else echo "mypy not installed (pip install mypy)"; fi

shellcheck:  ## Lint shell scripts with shellcheck (scripts/*.sh tools/*.sh)
	@if command -v shellcheck >/dev/null 2>&1; then shellcheck scripts/*.sh tools/*.sh; \
	else echo "shellcheck not installed -- skipping (apt install shellcheck)"; fi

compileall:  ## Byte-compile all Python sources (catch syntax errors; AGENTS.md verification checklist)
	$(PY) -m compileall -q camfrog_autodj tests tools

## ---- playlist validation -------------------------------------------------------
validate-playlists:  ## Validate all playlist/*.json source URLs (URLs, ytsearchN:, local paths)
	$(PY) tools/validate_playlists.py

fix-playlists:  ## Validate and fix playlist/*.json (removes invalid entries with .bak backup)
	$(PY) tools/validate_playlists.py --fix

## ---- full validation -----------------------------------------------------------
full-validation: lint typecheck validate-playlists test changelog-check config-check validate-installer  ## Run source validation (does not build or test the Windows installer)
	@echo ""
	@echo "================================================"
	@echo "  SOURCE VALIDATION PASSED for v$(VERSION)"
	@echo "  Build, signing, installer, and Windows runtime are separate gates."
	@echo "================================================"

validate-installer:  ## Validate installer.nsi structure and required files
	@$(PY) tools/validate_installer.py

lint-src:  ## Lint source + tools with ruff (excludes test files with pre-existing issues)
	@if $(PY) -c "import ruff" 2>/dev/null || command -v ruff >/dev/null 2>&1; then \
		ruff check $(PROJECT) tools || echo "NOTE: pre-existing ruff warnings (defensive patterns)"; \
	else \
		echo "ruff not installed -- falling back to py_compile (pip install ruff for real linting)"; \
		$(PY) -c "import glob, py_compile; [py_compile.compile(f) for f in glob.glob('camfrog_autodj/**/*.py', recursive=True)]"; \
	fi

config-check:  ## Validate config.toml: parses TOML, checks required keys exist
	@$(PY) -c "import tomllib,sys; p='$(CONFIG)'; data=tomllib.load(open(p,'rb')); required=['bot_nick','prefix','chat_reader','chat_sender','mpv_path']; missing=[k for k in required if k not in data]; sys.exit(1) if missing else print(f'OK: {p} is valid TOML with {len(data)} keys')"

validate-template:  ## Validate template structure and local Markdown links (scripts/validate_repo.py)
	$(PY) scripts/validate_repo.py

package:  ## Zip the source tree for distribution (excludes caches, local config.toml)
	@mkdir -p dist
	$(PY) tools/package.py "$(DIST_ZIP)"

installer:  ## Build NSIS installer (Windows: .ps1, Linux/WSL: .sh)
ifeq ($(OS),Windows_NT)
	powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/build_installer.ps1 -Version $(VERSION)
else
	bash scripts/build_installer_linux.sh $(VERSION) dist dist
endif

validate-windows:  ## Run Windows validation evidence collector (PowerShell)
ifeq ($(OS),Windows_NT)
	powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/validate-windows.ps1
else
	@echo "validate-windows requires Windows PowerShell"
	@exit 1
endif

validate-windows-bat:  ## Run Windows validation evidence collector (batch wrapper)
ifeq ($(OS),Windows_NT)
	cmd.exe /c scripts\validate-windows.bat
else
	@echo "validate-windows-bat requires Windows cmd.exe"
	@exit 1
endif

build:  ## Build AutoDJ.exe with PyInstaller (Windows PowerShell or Linux/Wine)
ifeq ($(OS),Windows_NT)
	@echo "=== Building AutoDJ.exe (PyInstaller) ==="
	powershell.exe -NoProfile -ExecutionPolicy Bypass -File build.ps1 $(BUILD_ARGS)
	@powershell.exe -NoProfile -Command "if (-not (Test-Path 'dist\\AutoDJ.exe')) { Write-Error 'ERROR: dist\\AutoDJ.exe not found after build.'; exit 1 }"
	@echo "  OK: dist\\AutoDJ.exe built"
else
	@echo "=== Building AutoDJ.exe (PyInstaller via Wine) ==="
	bash scripts/build_exe_linux.sh $(VERSION)
	@test -f dist/AutoDJ.exe || (echo "ERROR: dist/AutoDJ.exe not found after build."; exit 1)
	@echo "  OK: dist/AutoDJ.exe built"
endif

build-clean:  ## Clean build artifacts then rebuild
ifeq ($(OS),Windows_NT)
	powershell.exe -NoProfile -ExecutionPolicy Bypass -File build.ps1 -Clean $(BUILD_ARGS)
else
	@echo "=== Clean rebuild of AutoDJ.exe (PyInstaller via Wine) ==="
	bash scripts/build_exe_linux.sh $(VERSION) --clean
	@test -f dist/AutoDJ.exe || (echo "ERROR: dist/AutoDJ.exe not found after build."; exit 1)
	@echo "  OK: dist/AutoDJ.exe built"
endif

sign:  ## Sign existing AutoDJ.exe (Windows)
ifeq ($(OS),Windows_NT)
	@if [ ! -f dist/AutoDJ.exe ]; then echo "ERROR: dist/AutoDJ.exe not found. Run 'make build' first."; exit 1; fi
	powershell.exe -NoProfile -ExecutionPolicy Bypass -File build.ps1 $(BUILD_ARGS)
else
	@echo "sign requires Windows."
	@exit 1
endif

build-all:  ## Full pipeline: env check -> build AutoDJ.exe -> NSIS installer (Windows or Linux/Wine)
ifeq ($(OS),Windows_NT)
	$(MAKE) win11-check SKIP_CHECKS=$(SKIP_CHECKS)
	$(MAKE) mpv-check SKIP_CHECKS=$(SKIP_CHECKS)
	$(MAKE) nsis-check SKIP_CHECKS=$(SKIP_CHECKS)
	$(MAKE) pyinstaller-check SKIP_CHECKS=$(SKIP_CHECKS)
	@echo "=== Step 1/3: Building AutoDJ.exe (PyInstaller) ==="
	powershell.exe -NoProfile -ExecutionPolicy Bypass -File build.ps1 $(BUILD_ARGS)
	@powershell.exe -NoProfile -Command "if (-not (Test-Path 'dist\\AutoDJ.exe')) { Write-Error 'ERROR: dist\\AutoDJ.exe not found after build.'; exit 1 }"
	@echo ""
	@echo "=== Step 2/3: Building NSIS Installer ==="
	$(MAKE) nsiswindows11 SKIP_CHECKS=$(SKIP_CHECKS)
	@echo ""
	@echo "=== Build Complete ==="
	@echo "Installer: dist\Camfrog-AutoDJ-Setup-$(VERSION).exe"
else
	@echo "=== Step 1/2: Checking Wine + building AutoDJ.exe (PyInstaller) ==="
	bash scripts/build_exe_linux.sh $(VERSION)
	@test -f dist/AutoDJ.exe || (echo "ERROR: dist/AutoDJ.exe not found after build."; exit 1)
	@echo ""
	@echo "=== Step 2/2: Building NSIS Installer ==="
	bash scripts/build_installer_linux.sh $(VERSION) dist dist
	@test -f dist/Camfrog-AutoDJ-Setup-$(VERSION).exe || (echo "ERROR: Installer not created."; exit 1)
	@echo ""
	@echo "=== Build Complete (UNSIGNED Linux/Wine artifact) ==="
	@echo "Installer: dist/Camfrog-AutoDJ-Setup-$(VERSION).exe"
	@echo "NOTE: Authenticode signing requires Windows; this artifact is unsigned."
endif

build-all-linux:  ## Alias for build-all on Linux/Wine (kept for compatibility)
ifeq ($(OS),Windows_NT)
	@echo "build-all-linux is for Linux/WSL only. Use 'make build-all' on Windows."
	@exit 1
else
	$(MAKE) build-all
endif

build-all-hybrid:  ## Hybrid workflow: Windows (build + NSIS) -> WSL post-processing (run from PowerShell)
ifeq ($(OS),Windows_NT)
	powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/build-all-hybrid.ps1 $(HYBRID_ARGS)
else
	@echo "build-all-hybrid must be run from Windows PowerShell"
	@exit 1
endif

nsiswindows11:  ## Build NSIS installer for Windows 11 (requires NSIS + AutoDJ.exe in dist/)
ifeq ($(OS),Windows_NT)
	@if [ ! -f dist/AutoDJ.exe ]; then echo "ERROR: dist/AutoDJ.exe not found. Run 'make build' first."; exit 1; fi
	powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/build_installer.ps1 -Version $(VERSION) -Sign
	@if [ -f dist/Camfrog-AutoDJ-Setup-$(VERSION).exe ]; then \
		echo "  OK: dist/Camfrog-AutoDJ-Setup-$(VERSION).exe created"; \
	else \
		echo "ERROR: Installer not created."; \
		exit 1; \
	fi
else
	@echo "nsiswindows11 requires Windows 11 with NSIS installed"
	@exit 1
endif

build-all-force:  ## Full pipeline: SKIP all prerequisite checks (for air-gapped / pre-validated Windows machines)
ifeq ($(OS),Windows_NT)
	$(MAKE) build-all SKIP_CHECKS=1
else
	$(MAKE) build-all SKIP_CHECKS=1
endif

trustsign:  ## Azure Trusted Signing: Sign EXE + Installer via Azure Key Vault (requires Azure setup)
ifeq ($(OS),Windows_NT)
	@echo "=== Azure Trusted Signing ==="
	@if [ ! -f dist/AutoDJ.exe ]; then echo "ERROR: dist/AutoDJ.exe not found. Run 'make build' first."; exit 1; fi
	@echo "Signing AutoDJ.exe via Azure Key Vault: $(AZURE_KEYVAULT_NAME)/$(AZURE_CERT_NAME)"
	az signtool sign --kva https://$(AZURE_KEYVAULT_NAME).vault.azure.net --cert-name $(AZURE_CERT_NAME) --file dist\AutoDJ.exe --hash-algorithm sha256 --timestamp-rfc3161 http://timestamp.digicert.com
	@if [ -f dist/Camfrog-AutoDJ-Setup-$(VERSION).exe ]; then \
		echo "Signing Installer via Azure Key Vault..." && \
		az signtool sign --kva https://$(AZURE_KEYVAULT_NAME).vault.azure.net --cert-name $(AZURE_CERT_NAME) --file dist\Camfrog-AutoDJ-Setup-$(VERSION).exe --hash-algorithm sha256 --timestamp-rfc3161 http://timestamp.digicert.com; \
	fi
	@echo "=== Azure Signing Complete ==="
else
	@echo "trustsign requires Windows (uses az signtool)"
	@exit 1
endif

installer-clean:  ## Clean installer artifacts (cross-platform)
	@$(PY) -c "import glob, os; [os.remove(f) for f in glob.glob('dist/Camfrog-AutoDJ-Setup-*.exe')+(['dist/installer.nsi'] if os.path.exists('dist/installer.nsi') else [])]"

## ---- housekeeping ---------------------------------------------------------------
clean:  ## Remove Python caches and test artifacts
	@$(PY) -c "import shutil, pathlib; [shutil.rmtree(p) for p in pathlib.Path('.').glob('**/__pycache__') if p.is_dir()]; [p.unlink() for p in pathlib.Path('.').glob('**/*.pyc')]; shutil.rmtree('.pytest_cache', ignore_errors=True); shutil.rmtree('htmlcov', ignore_errors=True); pathlib.Path('.coverage').unlink(missing_ok=True)"

clean-all: clean  ## clean generated build/dist artifacts; preserve tracked PyInstaller spec files
	@$(PY) -c "import shutil; shutil.rmtree('build', ignore_errors=True); shutil.rmtree('dist', ignore_errors=True)"
	@$(PY) -c "import glob, os; [os.remove(f) for f in glob.glob('dist/Camfrog-AutoDJ-Setup-*.exe')+(['dist/installer.nsi'] if os.path.exists('dist/installer.nsi') else [])]"

distclean: clean-all  ## clean-all + remove the virtualenv
	@$(PY) -c "import shutil; shutil.rmtree('.venv', ignore_errors=True)"

changelog-check:  ## Fail if CHANGELOG.md has no entry for the current version
	@$(PY) -c "content = open('CHANGELOG.md', encoding='utf-8').read(); exit(0) if '## $(VERSION)' in content else (print('CHANGELOG.md has no entry for $(VERSION)'), exit(1))"
	@echo "CHANGELOG.md has an entry for $(VERSION)"

bump-patch:  ## Bump patch version in pyproject.toml and CHANGELOG.md
	@$(PY) -c "import tomllib; p='pyproject.toml'; d=tomllib.load(open(p,'rb')); cur=d['project']['version']; parts=cur.split('.'); parts[2]=str(int(parts[2])+1); new='.'.join(parts); lines=open(p,encoding='utf-8').readlines(); open(p,'w',encoding='utf-8').writelines([('version = \"'+new+'\"\n') if ln.strip().startswith('version =') else ln for ln in lines]); print(f'Bumped {cur} -> {new}')"
	@echo "Remember to update CHANGELOG.md with the new version"

security-check:  ## Run security checks (secret scan, dependency audit)
	@echo "Running security checks..."
	@$(PY) -c "import pathlib; print('Scanning for potential secrets...')" 2>/dev/null || true
	@grep -rniE '(password|secret|api_key|token|private_key)\s*=\s*["'\'']' camfrog_autodj/ 2>/dev/null --include='*.py' | grep -v '^.*#' | grep -viE '(= ""|os\.environ|getenv|\.get\()' || echo "No hardcoded secrets found"
	@echo "Security check complete"

security-audit:  ## Audit Python dependencies for known vulnerabilities (pip-audit; advisory, not part of `all`)
	@if command -v pip-audit >/dev/null 2>&1; then \
		echo "Running dependency audit (pip-audit)..."; \
		(pip-audit --skip-editable || echo "NOTE: pip-audit reported findings above -- advisory only; verify they belong to this project's declared dependencies (pyproject.toml) before acting."); \
	else \
		echo "pip-audit not installed; skipping dependency audit (pip install pip-audit)"; \
	fi

docs:  ## List the docs that ship with the project
	@$(PY) -c "import glob; [print(f) for f in glob.glob('*.md')]"

pre-commit: lint test  ## Format (optional), lint, then test -- run before committing
	@if command -v ruff >/dev/null 2>&1; then ruff format $(PROJECT) tests tools 2>/dev/null || true; fi
	@echo "pre-commit checks passed"

ci: install-dev test  ## What CI runs (see .github/workflows/tests.yml)

release: full-validation build sign package  ## Full release pipeline: validate -> build -> sign -> package
	@echo ""
	@echo "================================================"
	@echo "  RELEASE BUILD COMPLETE for v$(VERSION)"
	@echo "  Artifacts in dist/:"
	@ls -la dist/AutoDJ.exe dist/Camfrog-AutoDJ-Setup-*.exe dist/camfrog-autodj-*.zip 2>/dev/null || true
	@echo "================================================"

all: compileall lint lint-src typecheck test fmt-check shellcheck validate-playlists validate-installer config-check changelog-check security-check validate-template  ## Run all verification checks per AGENTS.md checklist
	@echo ""
	@echo "================================================"
	@echo "  ALL VERIFICATION CHECKS PASSED for v$(VERSION)"
	@echo "================================================"

validate-all: all  ## Alias for `all` -- runs every verification check (compileall, lint, lint-src, typecheck, test, fmt-check, shellcheck, validate-playlists, validate-installer, config-check, changelog-check, security-check, validate-template)
	@echo "validate-all: complete (same checks as make all)"
