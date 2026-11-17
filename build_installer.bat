@echo off
REM CamfrogAutoDJ - NSIS Installer Builder
REM Run this on Windows to build the NSIS installer

echo ==========================================
echo CamfrogAutoDJ - NSIS Installer Builder
echo ==========================================
echo.

REM Check for NSIS
where makensis >nul 2>nul
if errorlevel 1 (
    echo ERROR: NSIS (makensis) not found in PATH
    echo Please install NSIS 3.08+ from https://nsis.sourceforge.io/
    echo After installation, restart this command prompt.
    exit /b 1
)

echo Found NSIS: %~$PATH:makensis
echo.

REM Check for required files (built artifacts are in dist/)
echo Checking required files...
REM installer.nsi packages everything from dist\ (build.ps1 stages it there), so check dist\.
set REQUIRED=dist\AutoDJ.exe dist\app.ico dist\config.toml dist\README.md dist\CHANGELOG.md dist\LICENSE dist\install.ps1 dist\run_autodj.py
for %%f in (%REQUIRED%) do (
    if not exist "%%f" (
        echo WARNING: Missing required file: %%f
    ) else (
        echo   [OK] %%f
    )
)

REM Build installer
echo.
REM Take the version from pyproject.toml; installer.nsi's built-in default can be stale.
set APP_VERSION=
for /f "usebackq delims=" %%v in (`python -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])"`) do set APP_VERSION=%%v
if "%APP_VERSION%"=="" (
    echo ERROR: could not read the version from pyproject.toml ^(is python on PATH?^)
    exit /b 1
)

echo.
echo Building NSIS installer %APP_VERSION%...
makensis /DAPP_VERSION=%APP_VERSION% /DOUTDIR=dist installer.nsi
if errorlevel 1 (
    echo.
    echo ERROR: NSIS build failed!
    exit /b 1
)

echo.
echo ==========================================
echo Installer built successfully!
echo.
dir /b dist\*Setup*.exe
echo ==========================================

echo.
echo Next steps:
echo   1. Test the installer on a clean VM
echo   2. Sign with: signtool sign /f cert.pfx /p password /t http://timestamp.digicert.com "Camfrog-AutoDJ-Setup-*.exe"
echo   3. Upload to GitHub Releases
echo.
