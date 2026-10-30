@echo on
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
echo DEBUG: WINVER=%WINVER%
for /f "tokens=3 delims=." %%b in ("%WINVER%") do set BUILD=%%b
echo DEBUG: BUILD before=%BUILD%

rem Remove trailing bracket if present
set BUILD=%BUILD:]=%
echo DEBUG: BUILD after=%BUILD%

if "%BUILD%"=="" (
    echo WARNING: Could not determine Windows build number.
    echo Proceeding anyway...
) else if %BUILD% LSS 22000 (
    echo ERROR: Windows 11 (Build 22000+) is required.
    echo Current build: %WINVER%
    echo.
    pause
    exit /b 1
)

echo DEBUG: Passed version check