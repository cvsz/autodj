#!/bin/bash
# AutoDJ - NSIS Installer Builder (Linux/WSL)
# Builds the NSIS installer. Detection order for makensis:
#   1. native `makensis` on PATH
#   2. $NSIS_PATH (Windows makensis.exe inside the Wine prefix)
#   3. Wine `makensis.exe` fallback search
# Wine is only required when a Windows makensis.exe is used.

set -euo pipefail

VERSION="${1:-$(python3 -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")}"
SRCDIR="${2:-dist}"
OUTDIR="${3:-dist}"
NSIS_PATH="${NSIS_PATH:-$HOME/.wine/drive_c/NSIS/makensis.exe}"
WINE_BIN="${WINE_BIN:-$(command -v wine || command -v wine64 || true)}"

echo "=========================================="
echo "AutoDJ - NSIS Installer Builder (Linux/WSL)"
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
    "zAutoDJ.exe"
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
# makensis would fail later with a far less obvious message; stop here for the exe itself.
if [[ ! -f "$SRCDIR/zAutoDJ.exe" ]]; then
    echo "ERROR: $SRCDIR/zAutoDJ.exe is missing -- run the exe build first (make build)."
    exit 1
fi

# --- 3. render installer.nsi with the real version (shared renderer) --------------
RENDERED_NSI="$SRCDIR/installer.nsi"
echo "Generating installer.nsi with version $VERSION..."
"$GEN_PYTHON" "$REPO_ROOT/scripts/render_installer_nsi.py" \
    --version "$VERSION" \
    --input "$REPO_ROOT/installer.nsi" \
    --output "$RENDERED_NSI"
echo "Generated $RENDERED_NSI"

# --- 4. build installer from repo root (so dist\\ paths resolve) ------------------
INSTALLER_NAME="zAutoDJ-Setup-${VERSION}.exe"
mkdir -p "$OUTDIR"
echo "Building installer: $INSTALLER_NAME..."

# Full installer (same rule as scripts/build_installer.ps1): mirror the whole mpv/
# folder into $SRCDIR/mpv and pass /DBUNDLE_MPV when it holds mpv.exe and yt-dlp.exe.
if [[ -f "$REPO_ROOT/mpv/mpv.exe" ]]; then
    mkdir -p "$SRCDIR/mpv"
    if command -v rsync >/dev/null 2>&1; then
        # --checksum: compare content, not just size + mtime (a same-size update with a
        # preserved timestamp would otherwise be skipped and the stale copy packaged).
        rsync -a --delete --checksum "$REPO_ROOT/mpv/" "$SRCDIR/mpv/"
    else
        rm -rf "${SRCDIR:?}/mpv" && cp -a "$REPO_ROOT/mpv" "$SRCDIR/mpv"
    fi
fi
BUNDLE_MPV_DEFINE="/DBUNDLE_MPV_OFF"
if [[ -f "$SRCDIR/mpv/mpv.exe" && -f "$SRCDIR/mpv/yt-dlp.exe" ]]; then
    BUNDLE_MPV_DEFINE="/DBUNDLE_MPV"
    echo "Installer type: full (mpv bundle installed by default)"
else
    echo "Installer type: without mpv bundle"
fi

run_makensis() {
    if [[ "$MAKENSIS_KIND" == "native" ]]; then
        "$MAKENSIS" -NOCD /DAPP_VERSION="$VERSION" /DSRCDIR=. /DOUTDIR="$OUTDIR" "$BUNDLE_MPV_DEFINE" "$RENDERED_NSI"
    else
        "$WINE_BIN" "$MAKENSIS" -NOCD /DAPP_VERSION="$VERSION" /DSRCDIR=. /DOUTDIR="$OUTDIR" "$BUNDLE_MPV_DEFINE" "$RENDERED_NSI"
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
