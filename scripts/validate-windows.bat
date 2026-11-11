@echo off
REM CamfrogAutoDJ - Windows Validation Evidence Collector (Batch Wrapper)
REM Calls scripts/validate-windows.ps1 with PowerShell
REM Usage: validate-windows.bat [VERSION] [SRCDIR] [OUTDIR] [-SkipBuild] [-SkipSign] [-SkipUiA] [-SkipTts] [-SkipE2e]

setlocal EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
set "PS1_SCRIPT=%SCRIPT_DIR%validate-windows.ps1"

if not exist "%PS1_SCRIPT%" (
    echo ERROR: %PS1_SCRIPT% not found
    exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%PS1_SCRIPT%" %*
exit /b %ERRORLEVEL%
