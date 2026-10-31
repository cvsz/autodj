@echo off
REM Camfrog AutoDJ - NSIS Installer Builder
REM Run this on Windows to build the NSIS installer

echo ==========================================
echo Camfrog AutoDJ - NSIS Installer Builder
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

REM Check for required files
echo Checking required files...
set REQUIRED=AutoDJ.exe app.ico config.example.toml README.md CHANGELOG.md LICENSE.md install.ps1 uninstall.ps1 run_autodj.py
for %%f in (%REQUIRED%) do (
    if not exist "%~dp0%%f" (
        echo WARNING: Missing required file: %%f
    ) else (
        echo   [OK] %%f
    )
)

REM Build installer
echo.
echo Building NSIS installer...
makensis installer.nsi
if errorlevel 1 (
    echo.
    echo ERROR: NSIS build failed!
    exit /b 1
)

echo.
echo ==========================================
echo Installer built successfully!
echo.
dir /b *.exe | findstr /i "setup"
echo ==========================================

echo.
echo Next steps:
echo   1. Test the installer on a clean VM
echo   2. Sign with: signtool sign /f cert.pfx /p password /t http://timestamp.digicert.com "Camfrog-AutoDJ-Setup-*.exe"
echo   3. Upload to GitHub Releases
echo.