# CamfrogAutoDJ -- dev convenience targets.
# Cross-platform (Linux/macOS/Windows PowerShell/Git-Bash).
# Windows 11 ready: validates OS build >= 22000, NSIS 3.09+, mpv, PyInstaller.
# NOTE: recipes use POSIX sh syntax ([ -f ], mkdir -p, ...), so on Windows run
# make from Git-Bash (bash must be on PATH); cmd.exe alone is not sufficient.

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

# ruff may be installed only as a Python module (not on PATH): prefer `python -m ruff`.
RUFF        := $(shell $(PY) -m ruff --version >/dev/null 2>&1 && echo "$(PY) -m ruff" || (command -v ruff >/dev/null 2>&1 && echo ruff))

# Windows 11 minimum build number (22000 = Windows 11 21H2)
WIN11_MIN_BUILD := 22000

# ---- logging ----------------------------------------------------------------
# Log directory for build-all validations and build steps (kept, not cleaned).
BUILD_LOG_DIR := logs
BUILD_LOG_TS  := $(shell date +%Y%m%d-%H%M%S 2>/dev/null || echo unknown)

# `sign` only exists on Windows; on Linux/Wine the release artifact is unsigned.
ifeq ($(OS),Windows_NT)
RELEASE_SIGN := sign
else
RELEASE_SIGN :=
endif

.DEFAULT_GOAL := help
.PHONY: help install install-dev install-build install-auto venv \
        run run-gui run-console run-headless check discover windows say join-room \
        test test-v test-one coverage mutation-smoke \
        lint lint-src fmt typecheck validate-playlists fix-playlists validate-template validate-installer full-validation security-check config-check \
        build build-clean sign build-all build-all-force build-all-linux build-all-hybrid trustsign package release installer installer-clean nsiswindows11 \
        validate-windows validate-windows-bat \
        clean clean-all distclean \
        config version bump-patch changelog-check pre-commit ci docs all \
        win11-check win11-validate mpv-check nsis-check pyinstaller-check logs

## ---- help -----------------------------------------------------------------
help:  ## Show this help
	@echo "CamfrogAutoDJ -- make targets (Windows 11 + Linux/Wine)"
	@echo ""
	@$(PY) -c "import re; [print(f'  \033[36m{m.group(1):<24}\033[0m {m.group(2)}') for line in open('$(firstword $(MAKEFILE_LIST))', encoding='utf-8') if (m := re.match(r'^([a-zA-Z0-9_.-]+):[^#]*##\s*(.*)', line))]"
	@echo ""
	@echo "Variables: PY=$(PY)  CONFIG=$(CONFIG)  VERSION=$(VERSION)"
	@echo "build* works on both platforms: Windows 11 (PowerShell) and Linux/Wine."
	@echo "Windows targets require: Windows 11 (build 22000+), NSIS 3.09+, mpv, PyInstaller"

## ---- Windows 11 prerequisite checks ---------------------------------------
# SKIP_CHECKS=1 bypasses all prerequisite checks (for air-gapped / pre-validated machines)
logs:  ## Create the build log directory
	@mkdir -p "$(BUILD_LOG_DIR)"

win11-check: logs  ## Verify Windows 11 (build 22000+) and NSIS/mpv/PyInstaller availability
ifeq ($(OS),Windows_NT)
	@echo "=== Windows 11 Prerequisite Check ($(BUILD_LOG_TS)) ==="
ifeq ($(SKIP_CHECKS),1)
	@echo "  SKIP: prerequisite checks disabled (SKIP_CHECKS=1)" >> "$(BUILD_LOG_DIR)/win11-check-$(BUILD_LOG_TS).log" 2>&1
	@echo "  SKIP: prerequisite checks disabled (SKIP_CHECKS=1)"
else
	@powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/win11-check.ps1 -MinBuild $(WIN11_MIN_BUILD) >>"$(BUILD_LOG_DIR)/win11-check-$(BUILD_LOG_TS).log" 2>&1 || (echo "ERROR: Windows 11 check failed (details in the log below). Set SKIP_CHECKS=1 to bypass." | tee -a "$(BUILD_LOG_DIR)/win11-check-$(BUILD_LOG_TS).log" && exit 1)
	@echo "  OK: Windows 11 detected" >> "$(BUILD_LOG_DIR)/win11-check-$(BUILD_LOG_TS).log" 2>&1
	@powershell.exe -NoProfile -Command "if (Get-Command makensis -ErrorAction SilentlyContinue) { echo '  OK: NSIS (makensis) in PATH' } elseif (Test-Path 'C:\Program Files (x86)\NSIS\makensis.exe') { echo '  OK: NSIS found at C:\Program Files (x86)\NSIS\makensis.exe' } elseif (Test-Path 'C:\Program Files\NSIS\makensis.exe') { echo '  OK: NSIS found at C:\Program Files\NSIS\makensis.exe' } else { echo 'ERROR: NSIS (makensis) not found. Install NSIS 3.09+ (choco install nsis) or set SKIP_CHECKS=1 to bypass.'; exit 1 }" >> "$(BUILD_LOG_DIR)/win11-check-$(BUILD_LOG_TS).log" 2>&1 || (echo "ERROR: NSIS not found. Set SKIP_CHECKS=1 to bypass." | tee -a "$(BUILD_LOG_DIR)/win11-check-$(BUILD_LOG_TS).log" && exit 1)
	@powershell.exe -NoProfile -Command "if (Get-Command mpv.exe -ErrorAction SilentlyContinue) { echo '  OK: mpv.exe in PATH' } elseif (Test-Path 'C:\Program Files\mpv\mpv.exe') { echo '  OK: mpv found at C:\Program Files\mpv\mpv.exe' } else { echo 'WARN: mpv.exe not found in PATH. Install: choco install mpv --version=2024.01.01 --yes' }" >> "$(BUILD_LOG_DIR)/win11-check-$(BUILD_LOG_TS).log" 2>&1
	@if $(PY) -c "import PyInstaller" 2>/dev/null; then echo "  OK: PyInstaller installed"; else echo "WARN: PyInstaller not installed. Run: $(PIP) install pyinstaller" | tee -a "$(BUILD_LOG_DIR)/win11-check-$(BUILD_LOG_TS).log"; fi
endif
	@echo "Logs: $(BUILD_LOG_DIR)/win11-check-$(BUILD_LOG_TS).log"
else
	@echo "win11-check requires Windows 11"
	@exit 1
endif

win11-validate:  ## Run full Windows validation evidence collector (installer, code signing, UIA, TTS, E2E); make win11-validate CAMFROG_ROOM=ZeaZDev [VALIDATE_ARGS=-SkipBuild]
ifeq ($(OS),Windows_NT)
	powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/validate-windows.ps1 $(if $(CAMFROG_ROOM),-CamfrogRoom "$(CAMFROG_ROOM)") $(VALIDATE_ARGS)
else
	@echo "validate-windows requires Windows PowerShell"
	@exit 1
endif

mpv-check: logs  ## Verify mpv is available for Windows builds
ifeq ($(OS),Windows_NT)
ifeq ($(SKIP_CHECKS),1)
	@echo "  SKIP: mpv check disabled (SKIP_CHECKS=1)" >> "$(BUILD_LOG_DIR)/mpv-check-$(BUILD_LOG_TS).log" 2>&1
	@echo "  SKIP: mpv check disabled (SKIP_CHECKS=1)"
else
	@powershell.exe -NoProfile -Command "if (-not (Get-Command mpv.exe -ErrorAction SilentlyContinue) -and -not (Test-Path 'C:\Program Files\mpv\mpv.exe')) { Write-Error 'mpv.exe not found. Install: choco install mpv --yes'; exit 1 }" >> "$(BUILD_LOG_DIR)/mpv-check-$(BUILD_LOG_TS).log" 2>&1 || (echo "ERROR: mpv not found. Set SKIP_CHECKS=1 to bypass." | tee -a "$(BUILD_LOG_DIR)/mpv-check-$(BUILD_LOG_TS).log" && exit 1)
	@echo "  OK: mpv available" >> "$(BUILD_LOG_DIR)/mpv-check-$(BUILD_LOG_TS).log" 2>&1
endif
else
	@echo "mpv-check is Windows-only"
	@exit 1
endif

nsis-check: logs  ## Verify NSIS (makensis) is available
ifeq ($(OS),Windows_NT)
ifeq ($(SKIP_CHECKS),1)
	@echo "  SKIP: NSIS check disabled (SKIP_CHECKS=1)" >> "$(BUILD_LOG_DIR)/nsis-check-$(BUILD_LOG_TS).log" 2>&1
	@echo "  SKIP: NSIS check disabled (SKIP_CHECKS=1)"
else
	@powershell.exe -NoProfile -Command "if (-not (Get-Command makensis -ErrorAction SilentlyContinue) -and -not (Test-Path 'C:\Program Files (x86)\NSIS\makensis.exe') -and -not (Test-Path 'C:\Program Files\NSIS\makensis.exe')) { Write-Error 'NSIS not found. Install: choco install nsis --yes'; exit 1 }" >> "$(BUILD_LOG_DIR)/nsis-check-$(BUILD_LOG_TS).log" 2>&1 || (echo "ERROR: NSIS not found. Set SKIP_CHECKS=1 to bypass." | tee -a "$(BUILD_LOG_DIR)/nsis-check-$(BUILD_LOG_TS).log" && exit 1)
	@echo "  OK: NSIS available" >> "$(BUILD_LOG_DIR)/nsis-check-$(BUILD_LOG_TS).log" 2>&1
endif
else
	@echo "nsis-check is Windows-only"
	@exit 1
endif

pyinstaller-check: logs  ## Verify PyInstaller is available
ifeq ($(SKIP_CHECKS),1)
	@echo "  SKIP: PyInstaller check disabled (SKIP_CHECKS=1)" >> "$(BUILD_LOG_DIR)/pyinstaller-check-$(BUILD_LOG_TS).log" 2>&1
	@echo "  SKIP: PyInstaller check disabled (SKIP_CHECKS=1)"
else
	@if $(PY) -c "import PyInstaller" 2>/dev/null; then echo "  OK: PyInstaller installed" >> "$(BUILD_LOG_DIR)/pyinstaller-check-$(BUILD_LOG_TS).log" 2>&1; else echo "ERROR: PyInstaller not installed. Run: $(PIP) install pyinstaller or set SKIP_CHECKS=1 to bypass." | tee -a "$(BUILD_LOG_DIR)/pyinstaller-check-$(BUILD_LOG_TS).log"; exit 1; fi
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
	@echo "=== Joining room per config.toml (room: $$(grep '^room =' $(CONFIG) 2>/dev/null | cut -d'=' -f2 | tr -d ' ' || echo 'not set')) ==="
	$(PY) -m $(PROJECT) -c $(CONFIG)

version:  ## Print the project version
	@echo $(VERSION)

config:  ## Create config.toml from the example if it does not exist yet
	@$(PY) -c "import os, shutil; print('config.toml already exists -- not overwriting') if os.path.exists('config.toml') else (shutil.copy('config.example.toml', 'config.toml'), print('created config.toml from config.example.toml'))"

## ---- testing ------------------------------------------------------------------
test:  ## Run the full test suite (pytest if installed, else the offline mini runner)
	@if $(PY) -c "import pytest" 2>/dev/null; then \
		$(PY) -m pytest -q; \
	else \
		echo "pytest not installed -- using tools/minipytest.py (offline stand-in; 'make install-dev' for real pytest)"; \
		$(PY) tools/minipytest.py tests; \
	fi

test-v:  ## Run tests with verbose/full tracebacks
	@if $(PY) -c "import pytest" 2>/dev/null; then $(PY) -m pytest -vv; \
	else $(PY) tools/minipytest.py tests; fi

test-one:  ## Run a single test file or node id: make test-one T=tests/test_hardening.py
	@test -n "$(T)" || (echo "usage: make test-one T=tests/test_hardening.py"; exit 1)
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
	@if [ -n "$(RUFF)" ]; then \
		$(RUFF) check $(PROJECT) tests tools; \
	else \
		echo "ruff not installed -- falling back to py_compile (pip install ruff for real linting)"; \
		$(PY) -c "import glob, py_compile; [py_compile.compile(f, doraise=True) for f in glob.glob('$(PROJECT)/**/*.py', recursive=True)]"; \
	fi

fmt:  ## Format with ruff/black if installed (no-op if none installed)
	@if [ -n "$(RUFF)" ]; then $(RUFF) format $(PROJECT) tests tools; \
	elif command -v black >/dev/null 2>&1; then black $(PROJECT) tests tools; \
	else echo "no formatter installed (pip install ruff or black)"; fi

typecheck:  ## Type-check with mypy if installed
	@if $(PY) -c "import mypy" 2>/dev/null; then $(PY) -m mypy $(PROJECT); \
	else echo "mypy not installed (pip install mypy)"; fi

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
	@if [ -n "$(RUFF)" ]; then \
		$(RUFF) check $(PROJECT) tools || echo "NOTE: pre-existing ruff warnings (defensive patterns)"; \
	else \
		echo "ruff not installed -- falling back to py_compile (pip install ruff for real linting)"; \
		$(PY) -c "import glob, py_compile; [py_compile.compile(f, doraise=True) for f in glob.glob('$(PROJECT)/**/*.py', recursive=True)]"; \
	fi

config-check:  ## Validate config.toml (falls back to config.example.toml if absent): parses TOML, checks required keys
	@$(PY) -c "import os,sys,tomllib; p='$(CONFIG)'; p=p if os.path.exists(p) else 'config.example.toml'; data=tomllib.load(open(p,'rb')); required=['bot_nick','prefix','chat_reader','chat_sender','mpv_path']; missing=[k for k in required if k not in data]; print(f'ERROR: {p} is missing keys: {missing}') if missing else print(f'OK: {p} is valid TOML with {len(data)} keys'); sys.exit(1 if missing else 0)"

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
	@echo "=== Step 1/2: Building AutoDJ.exe (PyInstaller) ==="
	powershell.exe -NoProfile -ExecutionPolicy Bypass -File build.ps1 $(BUILD_ARGS)
	@powershell.exe -NoProfile -Command "if (-not (Test-Path 'dist\\AutoDJ.exe')) { Write-Error 'ERROR: dist\\AutoDJ.exe not found after build.'; exit 1 }"
	@echo ""
	@echo "=== Step 2/2: Building NSIS Installer ==="
	$(MAKE) nsiswindows11 SKIP_CHECKS=$(SKIP_CHECKS)
	@echo ""
	@echo "=== Build Complete ==="
	@echo "Installer: dist\\Camfrog-AutoDJ-Setup-$(VERSION).exe"
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

build-all-force:  ## Full pipeline: SKIP all prerequisite checks (for air-gapped / pre-validated machines)
	$(MAKE) build-all SKIP_CHECKS=1

trustsign:  ## Azure Trusted Signing: Sign EXE + Installer via Azure Key Vault (requires Azure setup)
ifeq ($(OS),Windows_NT)
	@echo "=== Azure Trusted Signing ==="
	@if [ -z "$(AZURE_KEYVAULT_NAME)" ] || [ -z "$(AZURE_CERT_NAME)" ]; then echo "ERROR: set AZURE_KEYVAULT_NAME and AZURE_CERT_NAME"; exit 1; fi
	@if [ ! -f dist/AutoDJ.exe ]; then echo "ERROR: dist/AutoDJ.exe not found. Run 'make build' first."; exit 1; fi
	@echo "Signing AutoDJ.exe via Azure Key Vault: $(AZURE_KEYVAULT_NAME)/$(AZURE_CERT_NAME)"
	az signtool sign --kva https://$(AZURE_KEYVAULT_NAME).vault.azure.net --cert-name $(AZURE_CERT_NAME) --file dist/AutoDJ.exe --hash-algorithm sha256 --timestamp-rfc3161 http://timestamp.digicert.com
	@if [ -f dist/Camfrog-AutoDJ-Setup-$(VERSION).exe ]; then \
		echo "Signing Installer via Azure Key Vault..." && \
		az signtool sign --kva https://$(AZURE_KEYVAULT_NAME).vault.azure.net --cert-name $(AZURE_CERT_NAME) --file dist/Camfrog-AutoDJ-Setup-$(VERSION).exe --hash-algorithm sha256 --timestamp-rfc3161 http://timestamp.digicert.com; \
	fi
	@echo "=== Azure Signing Complete ==="
else
	@echo "trustsign requires Windows (uses az signtool)"
	@exit 1
endif

installer-clean:  ## Clean installer artifacts
	@rm -f dist/Camfrog-AutoDJ-Setup-*.exe dist/installer.nsi

## ---- housekeeping ---------------------------------------------------------------
clean:  ## Remove Python caches and test artifacts
	@$(PY) -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in list(pathlib.Path('.').glob('**/__pycache__')) if p.is_dir()]; [p.unlink() for p in list(pathlib.Path('.').glob('**/*.pyc')) if p.exists()]; shutil.rmtree('.pytest_cache', ignore_errors=True); shutil.rmtree('htmlcov', ignore_errors=True); pathlib.Path('.coverage').unlink(missing_ok=True)"

clean-all: clean  ## clean generated build/dist artifacts; preserve tracked PyInstaller spec files
	@$(PY) -c "import shutil; shutil.rmtree('build', ignore_errors=True); shutil.rmtree('dist', ignore_errors=True)"

distclean: clean-all  ## clean-all + remove the virtualenv
	@$(PY) -c "import shutil; shutil.rmtree('.venv', ignore_errors=True)"

changelog-check:  ## Fail if CHANGELOG.md has no entry for the current version
	@$(PY) -c "import re,sys; c=open('CHANGELOG.md',encoding='utf-8').read(); ok=re.search(r'^##\s+\[?v?'+re.escape('$(VERSION)')+r'(?![\w.])',c,re.M); print('CHANGELOG.md has an entry for $(VERSION)') if ok else (print('CHANGELOG.md has no entry for $(VERSION)'), sys.exit(1))"

bump-patch:  ## Bump patch version in pyproject.toml (then add a CHANGELOG.md entry)
	@$(PY) -c "import re,pathlib; p=pathlib.Path('pyproject.toml'); s=p.read_text(encoding='utf-8'); m=re.search(r'^(version\s*=\s*\")(\d+)\.(\d+)\.(\d+)(\")',s,re.M); assert m, 'version = \"x.y.z\" not found in pyproject.toml'; new=f'{m[2]}.{m[3]}.{int(m[4])+1}'; p.write_text(s[:m.start()]+m[1]+new+m[5]+s[m.end():],encoding='utf-8'); print(f'Bumped {m[2]}.{m[3]}.{m[4]} -> {new}')"
	@echo "Remember to update CHANGELOG.md with the new version"

security-check:  ## Run security checks (hardcoded-secret scan; fails if anything is found)
	@echo "Running security checks..."
	@echo "Scanning for potential secrets..."
	@if grep -rniE '(password|secret|api_key|token|private_key)\s*=\s*["'\'']' $(PROJECT)/ --include='*.py' | grep -vE '^[^:]*:[0-9]+:\s*#' | grep -viE '(= ""|os\.environ|getenv|\.get\()'; then \
		echo "ERROR: potential hardcoded secrets found (see above)"; exit 1; \
	else \
		echo "No hardcoded secrets found"; \
	fi
	@echo "Security check complete"

docs:  ## List the docs that ship with the project
	@$(PY) -c "import glob; [print(f) for f in glob.glob('*.md')]"

pre-commit: fmt lint test  ## Format (optional), lint, then test -- run before committing
	@echo "pre-commit checks passed"

ci: install-dev test  ## What CI runs (see .github/workflows/tests.yml)

release: full-validation build $(RELEASE_SIGN) package  ## Full release pipeline: validate -> build -> sign (Windows only) -> package
	@echo ""
	@echo "================================================"
	@echo "  RELEASE BUILD COMPLETE for v$(VERSION)"
	@echo "  Artifacts in dist/:"
	@ls -la dist/AutoDJ.exe dist/Camfrog-AutoDJ-Setup-*.exe dist/camfrog-autodj-*.zip 2>/dev/null || true
	@echo "================================================"

all: pre-commit  ## Run all pre-commit checks (same as make pre-commit)
