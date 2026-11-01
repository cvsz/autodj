#!/bin/bash
# Camfrog AutoDJ - NSIS Installer Builder (Linux/WSL via Wine)
# Builds the NSIS installer using Wine + NSIS on Linux/WSL
#
# Prerequisites:
#   sudo apt update && sudo apt install wine64 nsis
#   OR: download NSIS portable and extract to ~/.wine/drive_c/NSIS

set -euo pipefail

VERSION="${1:-0.2.5}"
SRCDIR="${2:-dist}"
OUTDIR="${3:-dist}"
NSIS_PATH="${NSIS_PATH:-$HOME/.wine/drive_c/NSIS/makensis.exe}"

echo "=========================================="
echo "Camfrog AutoDJ - NSIS Installer Builder (Linux/Wine)"
echo "=========================================="
echo "Version: $VERSION"
echo "Source:  $SRCDIR"
echo "Output:  $OUTDIR"
echo

# Check for Wine
if ! command -v wine64 >/dev/null 2>&1; then
    echo "ERROR: wine64 not found. Install with: sudo apt install wine64"
    exit 1
fi
echo "Found Wine: $(wine64 --version)"

# Check for NSIS
if [[ ! -f "$NSIS_PATH" ]]; then
    echo "NSIS not found at $NSIS_PATH"
    echo "Install NSIS:"
    echo "  Option 1: sudo apt install nsis  (may be older version)"
    echo "  Option 2: Download NSIS 3.08+ portable from https://nsis.sourceforge.io/"
    echo "            Extract to ~/.wine/drive_c/NSIS/"
    exit 1
fi
echo "Found NSIS: $NSIS_PATH"

# Verify source files
cd "$SRCDIR" || { echo "Source dir not found: $SRCDIR"; exit 1; }

REQUIRED_FILES=(
    "AutoDJ.exe"
    "app.ico"
    "config.example.toml"
    "README.md"
    "CHANGELOG.md"
    "LICENSE.md"
    "install.ps1"
    "uninstall.ps1"
    "run_autodj.py"
)

echo "Checking required files..."
for f in "${REQUIRED_FILES[@]}"; do
    if [[ ! -f "$f" ]]; then
        echo "  WARNING: Missing $f"
    else
        echo "  [OK] $f"
    fi
done

# Create installer.nsi with version substitution
echo "Generating installer.nsi with version $VERSION..."
sed "s/!define APP_VERSION \"0\.2\.3\"/!define APP_VERSION \"$VERSION\"/" ../installer.nsi > installer.nsi
echo "Generated installer.nsi"

# Build installer
INSTALLER_NAME="Camfrog-AutoDJ-Setup-${VERSION}.exe"
echo "Building installer: $INSTALLER_NAME..."

wine64 "$NSIS_PATH" /DVERSION="$VERSION" /DSRCDIR=. /DOUTDIR=. installer.nsi

if [[ $? -ne 0 ]]; then
    echo "ERROR: NSIS build failed"
    exit 1
fi

INSTALLER_PATH="$OUTDIR/$INSTALLER_NAME"
if [[ -f "$INSTALLER_PATH" ]]; then
    SIZE_MB=$(du -m "$INSTALLER_PATH" | cut -f1)
    echo ""
    echo "=========================================="
    echo "Installer built successfully!"
    echo "=========================================="
    echo "File: $INSTALLER_PATH"
    echo "Size: ${SIZE_MB} MB"
    echo ""
    echo "Next steps:"
    echo "  1. Test on clean Windows VM"
    echo "  2. Sign with signtool (on Windows):"
    echo "     signtool sign /f cert.pfx /p password /t http://timestamp.digicert.com \"$INSTALLER_NAME\""
    echo "  3. Upload to GitHub Releases"
else
    echo "ERROR: Installer not found at $INSTALLER_PATH"
    exit 1
fi