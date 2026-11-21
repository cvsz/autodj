@echo off
REM AutoDJ - Portable build
REM Builds the portable AutoDJ.exe distribution (dist/AutoDJ.exe + dist/mpv/ + dist/config.toml)
REM No NSIS installer, no Git Bash required. Runs on Windows cmd / PowerShell.

echo ==========================================
echo AutoDJ - Portable Build
echo ==========================================
echo.

REM Check for python
where python >nul 2>nul
if errorlevel 1 (
    echo ERROR: python not found in PATH
    exit /b 1
)
echo Found python

REM Check for PyInstaller
python -c "import PyInstaller" >nul 2>nul
if errorlevel 1 (
    echo ERROR: PyInstaller not installed. Run: pip install pyinstaller
    exit /b 1
)
echo Found PyInstaller

REM Build the portable exe (unsigned)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File build.ps1 -NoSign
if errorlevel 1 (
    echo.
    echo ERROR: Portable build failed. See output above.
    exit /b 1
)

REM Verify the artifact
if not exist dist\AutoDJ.exe (
    echo ERROR: dist\AutoDJ.exe not found after build.
    exit /b 1
)

REM Create shortcuts in dist\
echo.
echo Creating shortcuts...
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$s=New-Object -ComObject WScript.Shell; $e=(Resolve-Path 'dist\AutoDJ.exe').Path; $d=(Resolve-Path 'dist').Path; $c=$s.CreateShortcut($d+'\AutoDJ-Check.lnk'); $c.TargetPath=$e; $c.Arguments='--check'; $c.WorkingDirectory=$d; $c.Save(); $c=$s.CreateShortcut($d+'\Start-AutoDJ.lnk'); $c.TargetPath=$e; $c.Arguments='--gui'; $c.WorkingDirectory=$d; $c.Save()" 2>nul
if errorlevel 1 (
    echo WARNING: Could not create shortcuts. You can still run:
    echo   dist\AutoDJ.exe --check
    echo   dist\AutoDJ.exe --gui
    goto done
)
echo   dist\AutoDJ-Check.lnk   (runs --check)
echo   dist\Start-AutoDJ.lnk   (runs --gui)

REM Register mpv/yt-dlp paths (silent)
echo.
echo Registering mpv/yt-dlp...
call mpv\mpv-register.bat /S
if errorlevel 1 (
    echo WARNING: mpv registration failed. You can still run AutoDJ, but YouTube links may not work.
) else (
    echo   mpv/yt-dlp registered
)

REM Create client-friendly batch launchers (relative paths - work from any folder)
echo.
echo Creating client launchers...
python tools\make_client_shortcuts.py
if errorlevel 1 (
    echo WARNING: Could not create client launchers.
    goto done
)

REM Copy client readme
if exist dist-readme.txt copy dist-readme.txt dist\readme.txt >nul

:done
echo.
echo ==========================================
echo Portable build complete!
echo ==========================================
echo   dist\AutoDJ.exe
echo   dist\mpv\
echo   dist\config.toml
echo   dist\AutoDJ-Check.lnk
echo   dist\Start-AutoDJ.lnk
echo.
echo Run:   dist\AutoDJ.exe --gui   (or double-click Start-AutoDJ.lnk)
echo Check: dist\AutoDJ.exe --check (or double-click AutoDJ-Check.lnk)

