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

PY          ?= python3
PIP         := $(PY) -m pip
PROJECT     := camfrog_autodj
CONFIG      ?= config.toml
VERSION     := $(shell $(PY) -c "import tomllib,sys; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])" 2>/dev/null || echo unknown)
DIST_ZIP    := dist/camfrog-autodj-$(VERSION).zip
IS_WINDOWS  := $(filter Windows_NT,$(OS))

.DEFAULT_GOAL := help
.PHONY: help install install-dev install-build venv \
        run run-gui run-console check discover windows say \
        test test-v test-one coverage mutation-smoke \
        lint fmt typecheck \
        build build-clean sign package release \
        clean clean-all distclean \
        config version bump-patch \
        docs changelog-check pre-commit ci

## ---- help -----------------------------------------------------------------
help:  ## Show this help
	@echo "Camfrog AutoDJ -- make targets"
	@echo ""
	@$(PY) -c "import re; [print(f'  \033[36m{m.group(1):<18}\033[0m {m.group(2)}') for line in open('Makefile', encoding='utf-8') if (m := re.match(r'^([a-zA-Z0-9_.-]+):[^#]*##\s*(.*)', line))]"
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

fmt:  ## Format with ruff/black if installed
	@if command -v ruff >/dev/null 2>&1; then ruff format $(PROJECT) tests tools; \
	elif command -v black >/dev/null 2>&1; then black $(PROJECT) tests tools; \
	else echo "no formatter installed (pip install ruff or black)"; fi

typecheck:  ## Type-check with mypy if installed
	@if $(PY) -c "import mypy" 2>/dev/null; then $(PY) -m mypy $(PROJECT); \
	else echo "mypy not installed (pip install mypy)"; fi

## ---- Windows exe build + sign (cross-platform: Windows 11 + WSL2 Ubuntu 26.04) -------------
PFX         ?=
PASSWORD    ?=
THUMBPRINT  ?=
SUBJECT     ?=
NOSIGN      ?=
SIGN_ARGS   := $(if $(PFX),-Pfx "$(PFX)") $(if $(PASSWORD),-Password "$(PASSWORD)") \
               $(if $(THUMBPRINT),-Thumbprint "$(THUMBPRINT)") $(if $(SUBJECT),-Subject "$(SUBJECT)") \
               $(if $(NOSIGN),-NoSign)

ifeq ($(OS),Windows_NT)
HAS_WIN_HOST := 1
else
HAS_WIN_HOST := $(shell command -v powershell.exe >/dev/null 2>&1 && echo 1 || echo 0)
endif

build:  ## Build dist/AutoDJ.exe and auto-sign it (Windows 11 or WSL2 + Ubuntu 26.04)
ifeq ($(HAS_WIN_HOST),1)
	powershell.exe -NoProfile -ExecutionPolicy Bypass -File build.ps1 $(SIGN_ARGS)
else
	@echo "build requires Windows 11 or WSL2 with powershell.exe available."
	@exit 1
endif

build-clean:  ## Same as build, but wipes build/, dist/, AutoDJ.spec first
ifeq ($(HAS_WIN_HOST),1)
	powershell.exe -NoProfile -ExecutionPolicy Bypass -File build.ps1 -Clean $(SIGN_ARGS)
else
	@echo "build-clean requires Windows 11 or WSL2 with powershell.exe available."
	@exit 1
endif

sign:  ## Re-sign an already-built dist/AutoDJ.exe (Windows 11 or WSL2 + Ubuntu 26.04)
ifeq ($(HAS_WIN_HOST),1)
	powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools/sign_exe.ps1 $(SIGN_ARGS)
else
	@echo "sign requires Windows 11 or WSL2 with powershell.exe available."
	@exit 1
endif

release: changelog-check test build package  ## Full pipeline: check CHANGELOG, test, build dist/AutoDJ.exe (auto-signed), zip the source
	@echo "release $(VERSION) ready: dist/AutoDJ.exe (signed unless NOSIGN=1) + $(DIST_ZIP)"

package:  ## Zip the source tree for distribution (excludes caches, local config.toml)
	@mkdir -p dist
	$(PY) tools/package.py "$(DIST_ZIP)"

installer:  ## Build NSIS installer (Windows: .ps1, Linux/WSL: .sh)
ifeq ($(OS),Windows_NT)
	powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/build_installer.ps1 -Version $(VERSION)
else
	bash scripts/build_installer_linux.sh $(VERSION) dist dist
endif

installer-clean:  ## Clean installer artifacts
	@rm -f dist/Camfrog-AutoDJ-Setup-*.exe dist/installer.nsi

## ---- housekeeping ---------------------------------------------------------------
clean:  ## Remove Python caches and test artifacts
	@$(PY) -c "import shutil, pathlib; [shutil.rmtree(p) for p in pathlib.Path('.').glob('**/__pycache__') if p.is_dir()]; [p.unlink() for p in pathlib.Path('.').glob('**/*.pyc')]; shutil.rmtree('.pytest_cache', ignore_errors=True); shutil.rmtree('htmlcov', ignore_errors=True); pathlib.Path('.coverage').unlink(missing_ok=True)"

clean-all: clean  ## clean + remove build/dist/spec from a Windows build
	@$(PY) -c "import shutil; shutil.rmtree('build', ignore_errors=True); shutil.rmtree('dist', ignore_errors=True); [p.unlink() for p in pathlib.Path('.').glob('*.spec')]"

distclean: clean-all  ## clean-all + remove the virtualenv
	@$(PY) -c "import shutil; shutil.rmtree('.venv', ignore_errors=True)"

changelog-check:  ## Fail if CHANGELOG.md has no entry for the current version
	@$(PY) -c "content = open('CHANGELOG.md', encoding='utf-8').read(); exit(0) if '## $(VERSION)' in content else (print('CHANGELOG.md has no entry for $(VERSION)'), exit(1))"
	@echo "CHANGELOG.md has an entry for $(VERSION)"

docs:  ## List the docs that ship with the project
	@$(PY) -c "import glob; [print(f) for f in glob.glob('*.md')]"

pre-commit: fmt lint test  ## Format, lint, then test -- run before committing

ci: install-dev test  ## What CI runs (see .github/workflows/tests.yml)