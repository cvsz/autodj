@echo on
setlocal EnableDelayedExpansion
rem Camfrog AutoDJ - Windows 11 Automated Installer (Batch Wrapper)
rem This wrapper ensures PowerShell execution policy allows the script to run.

echo.
echo ============================================================================
echo  Camfrog AutoDJ - Windows 11 Automated Installer
echo  Version 0.2.4
echo ============================================================================
echo.

rem Check if running on Windows 11 (build 22000+)
for /f "tokens=4" %%a in ('ver') do set WINVER=%%a
for /f "tokens=3 delims=." %%b in ("%WINVER%") do set BUILD=%%b

rem Remove trailing bracket if present
set BUILD=%BUILD:]=%

rem Use PowerShell for reliable numeric comparison
powershell.exe -NoProfile -Command "if ('%BUILD%' -as [int] -ge 22000) { exit 0 } else { exit 1 }"
if !errorlevel! neq 0 (
    if "%BUILD%"=="" (
        echo WARNING: Could not determine Windows build number.
        echo Proceeding anyway...
    ) else (
        echo ERROR: Windows 11 (Build 22000+) is required.
        echo Current build: %WINVER%
        echo.
        pause
        exit /b 1
    )
)

echo DEBUG: Passed version check

rem Check for PowerShell
where powershell.exe >nul 2>&1
if !errorlevel! neq 0 (
    echo ERROR: PowerShell not found.
    pause
    exit /b 1
)

echo DEBUG: PowerShell found

rem Get script directory
set "SCRIPT_DIR=%~dp0"
set "INSTALL_PS1=%SCRIPT_DIR%install.ps1"
echo DEBUG: INSTALL_PS1=%INSTALL_PS1%

if not exist "%INSTALL_PS1%" (
    echo ERROR: install.ps1 not found at %INSTALL_PS1%
    pause
    exit /b 1
)

echo DEBUG: install.ps1 found

echo Starting installer...
echo.

rem Pass all arguments to the PowerShell script
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%INSTALL_PS1%" %*

set EXIT_CODE=!errorlevel!
echo.
if !EXIT_CODE! equ 0 (
    echo Installation completed successfully!
) else (
    echo Installation failed with exit code !EXIT_CODE!.
    echo Check the log file in %TEMP%\autodj-install-*.log
)
echo.
pause
exit /b !EXIT_CODE!