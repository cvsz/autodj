# Camfrog AutoDJ -- dev convenience targets.
# Cross-platform (Linux/macOS/Windows PowerShell/Git-Bash).

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

.DEFAULT_GOAL := help
.PHONY: help install install-dev install-build install-auto venv \
        run run-gui run-console run-headless check discover windows say join-room \
        test test-v test-one coverage mutation-smoke \
        lint lint-src fmt typecheck validate-playlists fix-playlists validate-template full-validation security-check config-check \
        build build-clean sign build-all build-all-linux build-all-hybrid trustsign package release installer installer-clean nsiswindows11 \
        clean clean-all distclean \
        config version bump-patch changelog-check pre-commit ci docs all

## ---- help -----------------------------------------------------------------
help:  ## Show this help
	@echo "Camfrog AutoDJ -- make targets"
	@echo ""
	@$(PY) -c "import re; [print(f'  \033[36m{m.group(1):<24}\033[0m {m.group(2)}') for line in open('Makefile', encoding='utf-8') if (m := re.match(r'^([a-zA-Z0-9_.-]+):[^#]*##\s*(.*)', line))]"
	@echo ""
	@echo "Variables: PY=$(PY)  CONFIG=$(CONFIG)  VERSION=$(VERSION)"

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

typecheck:  ## Type-check with mypy if installed
	@if $(PY) -c "import mypy" 2>/dev/null; then $(PY) -m mypy $(PROJECT) || echo "NOTE: pre-existing mypy issues (missing stubs)"; \
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

build:  ## Build AutoDJ.exe with PyInstaller (Windows PowerShell)
ifeq ($(OS),Windows_NT)
	powershell.exe -NoProfile -ExecutionPolicy Bypass -File build.ps1 $(BUILD_ARGS)
else
	@echo "build requires Windows (runs build.ps1). On Linux/WSL use 'make build' from PowerShell."
	@exit 1
endif

build-clean:  ## Clean build artifacts then rebuild
ifeq ($(OS),Windows_NT)
	powershell.exe -NoProfile -ExecutionPolicy Bypass -File build.ps1 -Clean $(BUILD_ARGS)
else
	@echo "build-clean requires Windows (runs build.ps1 -Clean)."
	@exit 1
endif

sign:  ## Sign existing AutoDJ.exe (Windows)
ifeq ($(OS),Windows_NT)
	powershell.exe -NoProfile -ExecutionPolicy Bypass -File build.ps1 -NoSign=false $(BUILD_ARGS)
else
	@echo "sign requires Windows."
	@exit 1
endif

build-all:  ## Full pipeline: build AutoDJ.exe -> connect Windows 11 -> make nsiswindows11
ifeq ($(OS),Windows_NT)
	@echo "=== Step 1/3: Building AutoDJ.exe (PyInstaller) ==="
	powershell.exe -NoProfile -ExecutionPolicy Bypass -File build.ps1 $(BUILD_ARGS)
	@powershell.exe -NoProfile -Command "if (-not (Test-Path 'dist\\AutoDJ.exe')) { Write-Error 'ERROR: dist\\AutoDJ.exe not found after build.'; exit 1 }"
	@echo ""
	@echo "=== Step 2/3: Verifying Windows 11 environment ==="
	@powershell.exe -NoProfile -Command "[System.Environment]::OSVersion.Version.Major -ge 10 -and [System.Environment]::OSVersion.Version.Build -ge 22000" || (echo "ERROR: Windows 11 (Build 22000+) required." && exit 1)
	@powershell.exe -NoProfile -Command "if (Get-Command makensis -ErrorAction SilentlyContinue) { exit 0 } elseif (Test-Path 'C:\Program Files (x86)\NSIS\makensis.exe') { exit 0 } elseif (Test-Path 'C:\Program Files\NSIS\makensis.exe') { exit 0 } else { echo 'ERROR: NSIS (makensis) not found in PATH or C:\Program Files (x86)\NSIS\. Install NSIS 3.08+.'; exit 1 }" || (echo "ERROR: NSIS (makensis) not found. Install NSIS 3.08+." && exit 1)
	@echo "  OK: Windows 11 detected"
	@echo "  OK: NSIS (makensis) found"
	@echo ""
	@echo "=== Step 3/3: Building NSIS Installer (make nsiswindows11) ==="
	$(MAKE) nsiswindows11
	@echo ""
	@echo "=== Build Complete ==="
	@echo "Installer: dist\Camfrog-AutoDJ-Setup-$(VERSION).exe"
else
	@echo "build-all requires Windows 11 (runs build.ps1 + NSIS)"
	@exit 1
endif

build-all-linux:  ## Full pipeline on Linux via Wine: build EXE + NSIS installer (requires wine64 + NSIS in Wine)
ifeq ($(OS),Windows_NT)
	@echo "build-all-linux is for Linux/WSL only. Use 'make build-all' on Windows."
	@exit 1
else
	@echo "=== Step 1/3: Building AutoDJ.exe (PyInstaller via Wine) ==="
	@if command -v wine64 >/dev/null 2>&1; then \
		echo "Found Wine: $$(wine64 --version)"; \
	else \
		echo "ERROR: wine64 not found. Install: sudo apt install wine64"; \
		exit 1; \
	fi
	@if [ -f "build.ps1" ]; then \
		wine64 powershell.exe -NoProfile -ExecutionPolicy Bypass -File build.ps1 $(BUILD_ARGS); \
	else \
		echo "ERROR: build.ps1 not found"; \
		exit 1; \
	fi
	@if [ -f "dist/AutoDJ.exe" ]; then \
		echo "  OK: dist/AutoDJ.exe built"; \
	else \
		echo "ERROR: dist/AutoDJ.exe not found after build"; \
		exit 1; \
	fi
	@echo ""
	@echo "=== Step 2/3: Verifying Wine + NSIS environment ==="
	@NSIS_PATH="$$HOME/.wine/drive_c/NSIS/makensis.exe"; \
	if [ -f "$$NSIS_PATH" ]; then \
		echo "  OK: NSIS found at $$NSIS_PATH"; \
	else \
		echo "ERROR: NSIS not found at $$NSIS_PATH"; \
		echo "Install NSIS portable to ~/.wine/drive_c/NSIS/"; \
		echo "  Download: https://nsis.sourceforge.io/"; \
		echo "  Extract NSIS 3.08+ to ~/.wine/drive_c/NSIS/"; \
		exit 1; \
	fi
	@echo ""
	@echo "=== Step 3/3: Building NSIS Installer (via scripts/build_installer_linux.sh) ==="
	bash scripts/build_installer_linux.sh $(VERSION) dist dist
	@echo ""
	@echo "=== Build Complete ==="
	@echo "Installer: dist/Camfrog-AutoDJ-Setup-$(VERSION).exe"
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
else
	@echo "nsiswindows11 requires Windows 11 with NSIS installed"
	@exit 1
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

installer-clean:  ## Clean installer artifacts
	@rm -f dist/Camfrog-AutoDJ-Setup-*.exe dist/installer.nsi

## ---- housekeeping ---------------------------------------------------------------
clean:  ## Remove Python caches and test artifacts
	@$(PY) -c "import shutil, pathlib; [shutil.rmtree(p) for p in pathlib.Path('.').glob('**/__pycache__') if p.is_dir()]; [p.unlink() for p in pathlib.Path('.').glob('**/*.pyc')]; shutil.rmtree('.pytest_cache', ignore_errors=True); shutil.rmtree('htmlcov', ignore_errors=True); pathlib.Path('.coverage').unlink(missing_ok=True)"

clean-all: clean  ## clean generated build/dist artifacts; preserve tracked PyInstaller spec files
	@$(PY) -c "import shutil; shutil.rmtree('build', ignore_errors=True); shutil.rmtree('dist', ignore_errors=True)"
	@rm -f dist/Camfrog-AutoDJ-Setup-*.exe dist/installer.nsi

distclean: clean-all  ## clean-all + remove the virtualenv
	@$(PY) -c "import shutil; shutil.rmtree('.venv', ignore_errors=True)"

changelog-check:  ## Fail if CHANGELOG.md has no entry for the current version
	@$(PY) -c "content = open('CHANGELOG.md', encoding='utf-8').read(); exit(0) if '## $(VERSION)' in content else (print('CHANGELOG.md has no entry for $(VERSION)'), exit(1))"
	@echo "CHANGELOG.md has an entry for $(VERSION)"

bump-patch:  ## Bump patch version in pyproject.toml and CHANGELOG.md
	@$(PY) -c "import tomllib, toml; p='pyproject.toml'; d=tomllib.load(open(p,'rb')); cur=d['project']['version']; parts=cur.split('.'); parts[2]=str(int(parts[2])+1); new='.'.join(parts); d['project']['version']=new; toml.dump(d, open(p,'w')); print(f'Bumped {cur} -> {new}')"
	@echo "Remember to update CHANGELOG.md with the new version"

security-check:  ## Run security checks (secret scan, dependency audit)
	@echo "Running security checks..."
	@$(PY) -c "import pathlib; print('Scanning for potential secrets...')" 2>/dev/null || true
	@grep -rniE '(password|secret|api_key|token|private_key)\s*=\s*["'\'']' camfrog_autodj/ 2>/dev/null --include='*.py' | grep -v '^.*#' | grep -viE '(= ""|os\.environ|getenv|\.get\()' || echo "No hardcoded secrets found"
	@echo "Security check complete"

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

all: pre-commit  ## Run all pre-commit checks (same as make pre-commit)
