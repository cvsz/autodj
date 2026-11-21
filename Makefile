# AutoDJ -- dev convenience targets.
# Cross-platform (Linux/macOS/Windows PowerShell/Git-Bash).
# Windows 11 ready: validates OS build >= 22000, NSIS 3.13+, mpv.exe, PyInstaller.
# Recipes use POSIX sh syntax ([ -f ], mkdir -p, ...); on Windows SHELL is set
# to Git Bash below, so `make build-all` works without extra flags.

# Variables
# PY: python3 on Linux/macOS; "python" on Windows (where "python3" is only the
# Microsoft Store alias). Override with: make PY=py  (the Windows py launcher)
BUILD_DIR ?= build
DIST_DIR ?= dist
LOG_DIR ?= logs
BUILD_LOG_DIR ?= $(LOG_DIR)/build
BUILD_LOG_TS ?= $(shell date +%Y%m%d%H%M%S)

ifeq ($(OS),Windows_NT)
PY          ?= python
# POSIX recipes need Git Bash on Windows. GNU Make only honours SHELL as a
# Unix-style shell when it comes from the environment or command line, and
# $(shell date) needs Git's usr/bin on PATH. From PowerShell:
#   $env:PATH = "C:\Program Files\Git\usr\bin;$env:PATH"
#   $env:SHELL = "C:/Program Files/Git/bin/bash.exe"
#   make build-all
MPV_BUNDLE_EXE ?= D:/data/autodj-installer/mpv/mpv.exe
# Without a POSIX shell, make falls back to cmd.exe: every `2>/dev/null` probe
# fails, so RUFF came out empty and `make lint` silently ran py_compile only.
# Warn but do not stop: Windows-only targets (powershell.exe, etc.) still work
# in cmd.exe; only POSIX-dependent recipes (lint, test, ...) need Git Bash.
ifneq ($(shell echo posix-ok 2>/dev/null),posix-ok)
$(warning NOTE: Git Bash not detected; make will run in cmd.exe. Windows-only targets (build, portable, installer, sign) still work. POSIX targets (lint, test, coverage, ...) need Git Bash.)
endif
else
PY          ?= $(shell command -v python3 >/dev/null 2>&1 && echo python3 || echo python)
endif
PIP         := $(PY) -m pip
PROJECT     := autodj
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
        run run-gui run-console run-headless check discover windows say \
        test test-v test-one coverage mutation-smoke \
        lint lint-src fmt typecheck validate-playlists fix-playlists validate-template validate-installer full-validation security-check config-check config version bump-patch changelog-check pre-commit ci docs \
        build build-clean portable portable-zip sign build-all build-all-force build-all-linux build-all-hybrid trustsign package release installer installer-clean nsiswindows11 \
        validate-windows validate-windows-bat \
        clean clean-all distclean

help:  ## Show this help
	@echo "AutoDJ -- make targets (Windows 11 + Linux/Wine)"
	@echo ""
	@$(PY) -c "import re; [print(f'  \033[36m{m.group(1):<24}\033[0m {m.group(2)}') for line in open('$(firstword $(MAKEFILE_LIST))', encoding='utf-8') if (m := re.match(r'^([a-zA-Z0-9_.-]+):[^#]*##\s*(.*)', line))]"
	@echo ""
	@echo "Variables: PY=$(PY)  CONFIG=$(CONFIG)  VERSION=$(VERSION)"
	@echo "build* works on both platforms: Windows 11 (PowerShell) and Linux/Wine."
	@echo "Windows targets require: Windows 11 (build 22000+), NSIS 3.13+, mpv.exe, PyInstaller"

# SKIP_CHECKS=1 bypasses all prerequisite checks (for air-gapped / pre-validated machines)
logs:  ## Create the build log directory
	@mkdir -p "$(BUILD_LOG_DIR)"

win11-check: logs  ## Verify Windows 11 (build 22000+) and NSIS/mpv/PyInstaller availability
ifeq ($(OS),Windows_NT)
	@echo "=== Windows 11 Prerequisite Check ($(BUILD_LOG_TS)) ==="
ifeq ($(SKIP_CHECKS),1)
	@echo "  SKIP: prerequisite checks disabled (SKIP_CHECKS=1)" | tee -a "$(BUILD_LOG_DIR)/win11-check-$(BUILD_LOG_TS).log"
else
	@powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/win11-check.ps1 -MinBuild $(WIN11_MIN_BUILD) >>"$(BUILD_LOG_DIR)/win11-check-$(BUILD_LOG_TS).log" 2>&1 || (echo "ERROR: Windows 11 check failed (details in the log below). Set SKIP_CHECKS=1 to bypass." | tee -a "$(BUILD_LOG_DIR)/win11-check-$(BUILD_LOG_TS).log" && exit 1)
	@echo "  OK: Windows 11 detected" >> "$(BUILD_LOG_DIR)/win11-check-$(BUILD_LOG_TS).log" 2>&1
	@powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/nsis-check.ps1 >> "$(BUILD_LOG_DIR)/win11-check-$(BUILD_LOG_TS).log" 2>&1 || (echo "ERROR: NSIS not found (details in the log). Set SKIP_CHECKS=1 to bypass." | tee -a "$(BUILD_LOG_DIR)/win11-check-$(BUILD_LOG_TS).log" && exit 1)
	@powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/mpv-check.ps1 -BundleExe "$(MPV_BUNDLE_EXE)" >> "$(BUILD_LOG_DIR)/win11-check-$(BUILD_LOG_TS).log" 2>&1
	@powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/pyinstaller-check.ps1 -Python "$(PY)" >> "$(BUILD_LOG_DIR)/win11-check-$(BUILD_LOG_TS).log" 2>&1
endif
else
	@echo "win11-check is Windows-only"
	@exit 1
endif
	@echo "Logs: $(BUILD_LOG_DIR)/win11-check-$(BUILD_LOG_TS).log"

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
	@powershell.exe -NoProfile -Command "if (-not (Get-Command mpv.exe -ErrorAction SilentlyContinue) -and -not (Test-Path 'C:\Program Files\mpv\mpv.exe') -and -not (Test-Path '$(MPV_BUNDLE_EXE)')) { Write-Error 'mpv.exe not found (also checked $(MPV_BUNDLE_EXE)). Install: choco install mpv --yes'; exit 1 }" >> "$(BUILD_LOG_DIR)/mpv-check-$(BUILD_LOG_TS).log" 2>&1 || (echo "ERROR: mpv not found. Set SKIP_CHECKS=1 to bypass." | tee -a "$(BUILD_LOG_DIR)/mpv-check-$(BUILD_LOG_TS).log" && exit 1)
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
	@test -f tools/mutate.sh || (echo "tools/mutate.sh not found"; exit 1)
	bash tools/mutate.sh

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
	else echo "ERROR: mypy not installed (pip install mypy)"; exit 1; fi

## ---- playlist validation -------------------------------------------------------
validate-playlists:  ## Validate all playlist/*.json source URLs (URLs, ytsearchN:, local paths)
	$(PY) tools/validate_playlists.py

fix-playlists:  ## Validate and fix playlist/*.json (removes invalid entries with .bak backup)
	$(PY) tools/validate_playlists.py --fix

## ---- full validation -----------------------------------------------------------
full-validation: lint typecheck validate-playlists test changelog-check config-check  ## Run source validation (does not build or test the Windows installer)
	@echo ""
	@echo "================================================"
	@echo "  SOURCE VALIDATION PASSED for v$(VERSION)"
	@echo "  Build, signing, installer, and Windows runtime are separate gates."
	@echo "================================================"

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

build:  ## Build AutoDJ.exe with PyInstaller (Windows PowerShell; Linux/WSL uses Wine builder)
ifeq ($(OS),Windows_NT)
	powershell.exe -NoProfile -ExecutionPolicy Bypass -File build.ps1 $(BUILD_ARGS)
else
	bash scripts/build_exe_linux.sh $(VERSION) $(BUILD_ARGS)
endif

portable:  ## Build the portable AutoDJ.exe distribution (dist/AutoDJ.exe + dist/mpv/, config.toml) — no installer
ifeq ($(OS),Windows_NT)
	powershell.exe -NoProfile -ExecutionPolicy Bypass -File build.ps1 -NoSign $(BUILD_ARGS)
	@if not exist dist\AutoDJ.exe (echo ERROR: dist\AutoDJ.exe not found after build. & exit /b 1)
	powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$$s=New-Object -ComObject WScript.Shell; $$e=(Resolve-Path 'dist\AutoDJ.exe').Path; $$d=(Resolve-Path 'dist').Path; $$c=$$s.CreateShortcut($$d+'\AutoDJ-Check.lnk'); $$c.TargetPath=$$e; $$c.Arguments='--check'; $$c.WorkingDirectory=$$d; $$c.Save(); $$c=$$s.CreateShortcut($$d+'\Start-AutoDJ.lnk'); $$c.TargetPath=$$e; $$c.Arguments='--gui'; $$c.WorkingDirectory=$$d; $$c.Save()" 2>nul
	mpv\mpv-register.bat /S
	python tools\make_client_shortcuts.py
	@if exist dist-readme.txt copy dist-readme.txt dist\readme.txt >nul
	@echo ""
	@echo "=== Portable build complete ==="
	@echo "Run: dist\start.bat      (double-click to open AutoDJ GUI)"
	@echo "Check: dist\check.bat    (double-click to verify setup)"
	@echo "Files: dist/AutoDJ.exe  dist/mpv/  dist/config.toml  dist/readme.txt"
else
	bash scripts/build_exe_linux.sh $(VERSION) $(BUILD_ARGS)
	@if [ ! -f "dist/AutoDJ.exe" ]; then echo "ERROR: dist/AutoDJ.exe not found after build."; exit 1; fi
	@echo ""
	@echo "=== Portable build complete ==="
	@echo "Run: dist/AutoDJ.exe --gui"
	@echo "Files: dist/AutoDJ.exe  dist/mpv/  dist/config.toml"
endif

portable-zip: portable  ## Build portable dist and zip it for distribution (dist/camfrog-autodj-portable-<ver>.zip)
	@mkdir -p dist
	$(PY) -c "import zipfile, os, pathlib; z='dist/camfrog-autodj-portable-$(VERSION).zip'; base=pathlib.Path('dist'); zf=zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED); [zf.write(p, os.path.relpath(p, base)) for p in base.rglob('*') if p.is_file()]; zf.close()"
	@echo "Portable zip: dist/camfrog-autodj-portable-$(VERSION).zip"

build-clean:  ## Clean build artifacts then rebuild
ifeq ($(OS),Windows_NT)
	powershell.exe -NoProfile -ExecutionPolicy Bypass -File build.ps1 -Clean $(BUILD_ARGS)
else
	bash scripts/build_exe_linux.sh $(VERSION) --clean $(BUILD_ARGS)
endif

sign:  ## Sign existing AutoDJ.exe (Windows)
ifeq ($(OS),Windows_NT)
	@if [ ! -f dist/AutoDJ.exe ]; then echo "ERROR: dist/AutoDJ.exe not found. Run 'make build' first."; exit 1; fi
	powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools/sign_exe.ps1 -File dist\AutoDJ.exe $(SIGN_ARGS)
else
	@echo "sign requires Windows."
	@exit 1
endif

build-all:  ## Full pipeline: build AutoDJ.exe -> connect Windows 11 -> make nsiswindows11
ifeq ($(OS),Windows_NT)
	$(MAKE) win11-check SKIP_CHECKS=$(SKIP_CHECKS)
	$(MAKE) mpv-check SKIP_CHECKS=$(SKIP_CHECKS)
	$(MAKE) nsis-check SKIP_CHECKS=$(SKIP_CHECKS)
	$(MAKE) pyinstaller-check SKIP_CHECKS=$(SKIP_CHECKS)
	@echo "=== Step 1/2: Building AutoDJ.exe (PyInstaller) ==="
	powershell.exe -NoProfile -ExecutionPolicy Bypass -File build.ps1 $(BUILD_ARGS)
	@if [ ! -f dist/AutoDJ.exe ]; then echo "ERROR: dist/AutoDJ.exe not found after build."; exit 1; fi
	@echo ""
	@echo "=== Step 2/2: Building NSIS Installer ==="
	$(MAKE) nsiswindows11 SKIP_CHECKS=$(SKIP_CHECKS)
	@echo ""
	@echo "=== Build Complete ==="
	@echo "Installer: dist\\Camfrog-AutoDJ-Setup-$(VERSION).exe"
else
	@echo "=== Step 1/2: Building AutoDJ.exe (Linux/Wine builder) ==="
	bash scripts/build_exe_linux.sh $(VERSION) $(BUILD_ARGS)
	@if [ ! -f "dist/AutoDJ.exe" ]; then echo "ERROR: dist/AutoDJ.exe not found after build."; exit 1; fi
	@echo ""
	@echo "=== Step 2/2: Building NSIS Installer (Linux/Wine builder) ==="
	bash scripts/build_installer_linux.sh $(VERSION) dist dist
	@echo ""
	@echo "=== Build Complete ==="
	@echo "Installer: dist/Camfrog-AutoDJ-Setup-$(VERSION).exe"
endif

build-all-linux:  ## Full pipeline on Linux via Wine (alias for build-all on Linux)
ifeq ($(OS),Windows_NT)
	$(MAKE) build-all $(BUILD_ARGS)
else
	$(MAKE) build-all $(BUILD_ARGS)
endif

build-all-hybrid:  ## Hybrid workflow: Windows (build + NSIS) -> WSL post-processing (run from PowerShell)
ifeq ($(OS),Windows_NT)
	@if [ ! -f scripts/build-all-hybrid.ps1 ]; then echo "scripts/build-all-hybrid.ps1 is a local helper (not in git); use 'make build-all' instead."; exit 1; fi
	powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/build-all-hybrid.ps1 $(HYBRID_ARGS)
else
	@echo "build-all-hybrid must be run from Windows PowerShell"
	@exit 1
endif

nsiswindows11:  ## Build NSIS installer for Windows 11 (requires NSIS + AutoDJ.exe in dist/)
ifeq ($(OS),Windows_NT)
	@if [ ! -f dist/AutoDJ.exe ]; then echo "ERROR: dist/AutoDJ.exe not found. Run 'make build' first."; exit 1; fi
	powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/build_installer.ps1 -Version $(VERSION) -Sign
else
	@echo "nsiswindows11 requires Windows 11 with NSIS installed"
	@exit 1
endif

validate-installer:  ## Static checks of installer.nsi / build scripts (no Windows needed)
	$(PY) tools/validate_installer.py

validate-windows: win11-validate  ## Alias of win11-validate

validate-windows-bat:  ## Run scripts/validate-windows.bat (Windows cmd)
ifeq ($(OS),Windows_NT)
	cmd.exe /c scripts\\validate-windows.bat
else
	@echo "validate-windows-bat requires Windows"
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
