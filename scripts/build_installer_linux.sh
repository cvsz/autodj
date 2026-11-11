#!/bin/bash
# CamfrogAutoDJ - NSIS Installer Builder (Linux/WSL)
# Builds the NSIS installer. Detection order for makensis:
#   1. native `makensis` on PATH
#   2. $NSIS_PATH (Windows makensis.exe inside the Wine prefix)
#   3. Wine `makensis.exe` fallback search
# Wine is only required when a Windows makensis.exe is used.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
GEN_PYTHON="${PYTHON:-python3}"
WINEPREFIX="${WINEPREFIX:-$HOME/.wine}"

# Optional arguments:
#   build_installer_linux.sh [VERSION] [SRCDIR] [OUTDIR]
# VERSION defaults to pyproject.toml's project.version (never a hard-coded literal).
POSITIONAL=()
CLEAN=0
for arg in "$@"; do
    case "$arg" in
        --clean) CLEAN=1 ;;
        *) POSITIONAL+=("$arg") ;;
    esac
done
VERSION="${POSITIONAL[0]:-}"
SRCDIR="${POSITIONAL[1]:-dist}"
OUTDIR="${POSITIONAL[2]:-dist}"

if [[ -z "$VERSION" ]]; then
    VERSION="$("$GEN_PYTHON" -c "import tomllib; print(tomllib.load(open('$REPO_ROOT/pyproject.toml','rb'))['project']['version'])")"
fi

NSIS_PATH="${NSIS_PATH:-$HOME/.wine/drive_c/NSIS/makensis.exe}"
WINE_BIN="${WINE_BIN:-$(command -v wine || command -v wine64 || true)}"

echo "=========================================="
echo "CamfrogAutoDJ - NSIS Installer Builder (Linux/WSL)"
echo "=========================================="
echo "Version: $VERSION"
echo "Source:  $SRCDIR"
echo "Output:  $OUTDIR"
echo

# --- 1. makensis detection (native first, then Wine) -----------------------------
MAKENSIS=""
MAKENSIS_KIND=""
if command -v makensis >/dev/null 2>&1; then
    MAKENSIS="$(command -v makensis)"
    MAKENSIS_KIND="native"
    echo "Found native makensis: $MAKENSIS"
elif [[ -f "$NSIS_PATH" ]]; then
    MAKENSIS="$NSIS_PATH"
    MAKENSIS_KIND="wine"
    echo "Found NSIS (Wine): $MAKENSIS"
else
    # Fallback: search the Wine prefix for makensis.exe.
    if [[ -n "$WINE_BIN" ]]; then
        for candidate in \
            "$WINEPREFIX/drive_c/NSIS/makensis.exe" \
            "$WINEPREFIX/drive_c/Program Files/NSIS/makensis.exe" \
            "$WINEPREFIX/drive_c/Program Files (x86)/NSIS/makensis.exe"; do
            if [[ -f "$candidate" ]]; then
                MAKENSIS="$candidate"
                MAKENSIS_KIND="wine"
                echo "Found NSIS (Wine, fallback): $MAKENSIS"
                break
            fi
        done
    fi
fi

if [[ -z "$MAKENSIS" ]]; then
    echo "ERROR: makensis (NSIS) not found."
    echo "  Option 1: sudo apt install nsis   (native Linux makensis)"
    echo "  Option 2: set NSIS_PATH to a Windows makensis.exe in the Wine prefix"
    echo "  Option 3: install NSIS under Wine: https://nsis.sourceforge.io/"
    exit 1
fi

if [[ "$MAKENSIS_KIND" == "wine" ]]; then
    if [[ -z "$WINE_BIN" ]]; then
        echo "ERROR: wine not found, but a Windows makensis.exe was selected."
        echo "  Install Wine: sudo apt install wine   (or wine64)"
        exit 1
    fi
    echo "Using Wine: $("$WINE_BIN" --version 2>/dev/null | head -1)"
fi

# --- 2. verify source files -------------------------------------------------------
if [[ ! -d "$SRCDIR" ]]; then
    echo "ERROR: source dir not found: $SRCDIR"
    exit 1
fi

REQUIRED_FILES=(
    "AutoDJ.exe"
    "app.ico"
    "config.example.toml"
    "README.md"
    "CHANGELOG.md"
    "LICENSE"
    "install.ps1"
    "run_autodj.py"
)

echo "Checking required files..."
for f in "${REQUIRED_FILES[@]}"; do
    if [[ ! -f "$SRCDIR/$f" ]]; then
        echo "  WARNING: Missing $f"
    else
        echo "  [OK] $f"
    fi
done

# --- 3. render installer.nsi with the real version (shared renderer) --------------
RENDERED_NSI="$SRCDIR/installer.nsi"
echo "Generating installer.nsi with version $VERSION..."
"$GEN_PYTHON" "$REPO_ROOT/scripts/render_installer_nsi.py" \
    --version "$VERSION" \
    --input "$REPO_ROOT/installer.nsi" \
    --output "$RENDERED_NSI"
echo "Generated $RENDERED_NSI"

# --- 4. build installer from repo root (so dist\\ paths resolve) ------------------
INSTALLER_NAME="Camfrog-AutoDJ-Setup-${VERSION}.exe"
mkdir -p "$OUTDIR"
echo "Building installer: $INSTALLER_NAME..."

run_makensis() {
    if [[ "$MAKENSIS_KIND" == "native" ]]; then
        "$MAKENSIS" -NOCD /DAPP_VERSION="$VERSION" /DSRCDIR=. /DOUTDIR="$OUTDIR" "$RENDERED_NSI"
    else
        "$WINE_BIN" "$MAKENSIS" -NOCD /DAPP_VERSION="$VERSION" /DSRCDIR=. /DOUTDIR="$OUTDIR" "$RENDERED_NSI"
    fi
}

if ! ( cd "$REPO_ROOT" && run_makensis ); then
    echo "ERROR: NSIS build failed"
    exit 1
fi

# makensis writes next to the working dir (repo root) by default; mirror into
# OUTDIR when it is not already there so `make build-all` finds the artifact.
if [[ -f "$REPO_ROOT/$INSTALLER_NAME" && ! -f "$OUTDIR/$INSTALLER_NAME" ]]; then
    cp "$REPO_ROOT/$INSTALLER_NAME" "$OUTDIR/$INSTALLER_NAME"
fi

INSTALLER_PATH="$OUTDIR/$INSTALLER_NAME"
if [[ ! -f "$INSTALLER_PATH" && -f "$REPO_ROOT/$INSTALLER_NAME" ]]; then
    INSTALLER_PATH="$REPO_ROOT/$INSTALLER_NAME"
fi

if [[ -f "$INSTALLER_PATH" ]]; then
    SIZE_MB=$(du -m "$INSTALLER_PATH" | cut -f1)
    echo ""
    echo "=========================================="
    echo "Installer built successfully!"
    echo "=========================================="
    echo "File: $INSTALLER_PATH"
    echo "Size: ${SIZE_MB} MB"
    echo ""
    echo "NOTE: Linux/Wine artifact is UNSIGNED; sign on Windows for release."
else
    echo "ERROR: Installer not found at $INSTALLER_PATH"
    exit 1
fi
