#!/bin/bash
# CamfrogAutoDJ - AutoDJ.exe builder for Linux/WSL (Wine + Windows Python).
#
# Builds the SAME Windows AutoDJ.exe as build.ps1 does on Windows: it
# regenerates AutoDJ.spec from the shared PyInstaller flags
# (tools/generate_spec.py), runs PyInstaller with the Windows Python that
# lives inside the Wine prefix, then stages the runtime/installer files
# next to the exe (config, mpv/, docs set) exactly like build.ps1.
#
# The artifact is UNSIGNED -- Authenticode signing requires the Windows
# certificate store. Do not ship a Linux-built exe as a release without
# signing it on Windows (make sign / build.ps1 / az signtool).
#
# Prerequisites (once):
#   sudo apt install wine            # or wine64; both are accepted here
#   # Windows Python inside the Wine prefix (NOT the system Python):
#   wine python-3.11.9-amd64.exe /quiet InstallAllUsers=1 TargetDir=C:\Python311
#   wine C:\Python311\python.exe -m pip install pyinstaller
#   wine C:\Python311\python.exe -m pip install -e .   # project runtime deps
# Override the interpreter with:  WINE_PYTHON='C:\Python311\python.exe'
# Skip the Wine smoke test with:  AUTODJ_SKIP_SMOKE=1

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WINEPREFIX="${WINEPREFIX:-$HOME/.wine}"
GEN_PYTHON="${PYTHON:-python3}"

# Optional arguments:  build_exe_linux.sh [VERSION] [--clean]
#   VERSION  informational only (Makefile passes $(VERSION)); the exe's real
#            version comes from version_info.txt / pyproject.toml.
#   --clean  remove build/ and dist/ first (mirrors build.ps1 -Clean)
CLEAN=0
POSITIONAL=()
for arg in "$@"; do
    case "$arg" in
        --clean) CLEAN=1 ;;
        *) POSITIONAL+=("$arg") ;;
    esac
done
VERSION="${POSITIONAL[0]:-}"

echo "=========================================="
echo "CamfrogAutoDJ - AutoDJ.exe builder (Linux/Wine)"
echo "=========================================="
echo

# --- 1. Wine --------------------------------------------------------------------------
# WINE_BIN can be overridden (tests do this with a fake wine).
WINE_BIN="${WINE_BIN:-$(command -v wine || command -v wine64 || true)}"
if [[ -z "$WINE_BIN" ]]; then
    echo "ERROR: wine not found. AutoDJ.exe is a Windows binary; building it on"
    echo "Linux needs Wine. Install with:"
    echo "  sudo apt install wine          # or: sudo apt install wine64"
    exit 1
fi
echo "Found Wine: $("$WINE_BIN" --version 2>/dev/null | head -1)"

# --- 2. Windows Python inside the Wine prefix -----------------------------------------
WINE_PYTHON="${WINE_PYTHON:-}"
if [[ -z "$WINE_PYTHON" ]]; then
    for candidate in "$WINEPREFIX"/drive_c/Python*/python.exe \
                     "$WINEPREFIX/drive_c/Program Files"/Python*/python.exe; do
        if [[ -f "$candidate" ]]; then
            WINE_PYTHON="$candidate"
            break
        fi
    done
fi
if [[ -z "$WINE_PYTHON" ]]; then
    echo "ERROR: Windows Python not found in the Wine prefix ($WINEPREFIX/drive_c)."
    echo "AutoDJ.exe must be built by the Windows Python, not the system one."
    echo "Install it once:"
    echo "  1. Download the Python 3.11 x86_64 installer: https://www.python.org/downloads/windows/"
    echo "  2. wine <installer>.exe /quiet InstallAllUsers=1 TargetDir=C:\\Python311"
    echo "  3. wine C:\\Python311\\python.exe -m pip install pyinstaller"
    echo "  4. wine C:\\Python311\\python.exe -m pip install -e ."
    echo "Or point WINE_PYTHON at an existing interpreter, e.g.:"
    echo "  WINE_PYTHON='C:\\Python311\\python.exe' bash scripts/build_exe_linux.sh"
    exit 1
fi
echo "Found Windows Python: $WINE_PYTHON"

# --- 3. PyInstaller + project deps in that interpreter --------------------------------
if ! "$WINE_BIN" "$WINE_PYTHON" -m PyInstaller --version >/dev/null 2>&1; then
    echo "ERROR: PyInstaller is not installed in the Windows Python (WINE_PYTHON=$WINE_PYTHON)."
    echo "  Install it: wine $WINE_PYTHON -m pip install pyinstaller"
    exit 1
fi
echo "Found PyInstaller in the Windows Python"

# The Windows Python must see this project through a Wine drive (z: maps / by
# default; without it PyInstaller cannot find the sources).
if [[ ! -e "$WINEPREFIX/dosdevices/z:" ]]; then
    echo "ERROR: Wine drive z: not found in $WINEPREFIX/dosdevices."
    echo "The Windows Python reaches this project through z:; recreate the drive with:"
    echo "  ln -s / \"$WINEPREFIX/dosdevices/z:\""
    exit 1
fi

# Same pre-build dependency check build.ps1 runs (fails before wasting a build).
if ! "$WINE_BIN" "$WINE_PYTHON" tools/check_build_env.py; then
    echo "ERROR: the Windows Python is missing packages (see above): the exe would"
    echo "start but fail at run time. Install the project deps into that interpreter"
    echo "(WINE_PYTHON=$WINE_PYTHON):"
    echo "  wine $WINE_PYTHON -m pip install -e ."
    exit 1
fi

# --- 4. build -------------------------------------------------------------------------
cd "$REPO_ROOT"
if [[ "$CLEAN" == "1" ]]; then
    echo "=== Cleaning build/, dist/ and AutoDJ.spec (--clean) ==="
    rm -rf build dist AutoDJ.spec
fi
if [[ -n "$VERSION" ]]; then
    echo "Requested version: $VERSION (the exe's real version comes from version_info.txt / pyproject.toml)"
fi
echo
echo "=== Generating AutoDJ.spec (shared PyInstaller flags) ==="
"$GEN_PYTHON" tools/generate_spec.py --name AutoDJ

echo
echo "=== Building AutoDJ.exe with PyInstaller (under Wine) ==="
"$WINE_BIN" "$WINE_PYTHON" -m PyInstaller --noconfirm AutoDJ.spec
if [[ ! -f dist/AutoDJ.exe ]]; then
    echo "ERROR: PyInstaller did not produce dist/AutoDJ.exe"
    exit 1
fi
echo "OK: dist/AutoDJ.exe built"

# --- 5. runtime + installer files next to the exe (mirrors build.ps1) ------------------
if [[ -f config.example.toml ]]; then
    cp config.example.toml dist/config.toml
    chmod u+w dist/config.toml 2>/dev/null || true
    echo "copied config.example.toml -> dist/config.toml"
fi
if [[ -d mpv ]]; then
    mkdir -p dist/mpv
    cp -a mpv/. dist/mpv/
    echo "copied mpv/ -> dist/mpv/"
else
    echo "WARNING: mpv/ not found -- dist/mpv/ will be missing"
    echo "(the installer's 'mpv + yt-dlp' component needs dist/mpv/*)."
fi
for f in app.ico config.example.toml README.md CHANGELOG.md LICENSE install.ps1 run_autodj.py; do
    if [[ -f "$f" ]]; then
        cp "$f" dist/
        echo "copied $f -> dist/$f"
    else
        echo "WARNING: Installer source file not found: $f"
    fi
done

echo
echo "NOTICE: dist/AutoDJ.exe is UNSIGNED (Authenticode signing requires Windows)."
echo "Do not distribute it as a release without signing on Windows"
echo "(make sign / build.ps1 / az signtool)."

# --- 6. smoke test ---------------------------------------------------------------------
if [[ "${AUTODJ_SKIP_SMOKE:-0}" == "1" ]]; then
    echo "Smoke test skipped (AUTODJ_SKIP_SMOKE=1)."
else
    echo
    echo "=== Smoke test: dist/AutoDJ.exe --version (under Wine) ==="
    "$WINE_BIN" dist/AutoDJ.exe --version
fi

echo
echo "=== AutoDJ.exe build complete ==="
