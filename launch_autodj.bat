@echo off
chcp 65001 >nul 2>&1

rem Self-relaunch hidden via PowerShell so the CMD window does not show.
rem First run: no marker -> relaunch hidden, then exit.
rem Second run: marker set -> proceed normally with hidden window.
if "%AUTODJ_HIDDEN%" neq "1" (
    rem First run: relaunch hidden via PowerShell; if PowerShell is unavailable,
    rem fall through and run with a visible CMD window instead of exiting.
    powershell -NoProfile -WindowStyle Hidden -Command "Start-Process -FilePath '%~f0' -ArgumentList '' -WindowStyle Hidden" 2>nul
    if not errorlevel 1 exit /b
)
set AUTODJ_HIDDEN=1
setlocal EnableDelayedExpansion
rem Camfrog AutoDJ - Launcher for Windows
rem Double-click to open GUI (CMD window hidden)

echo ============================================
echo   Camfrog AutoDJ - Launcher
echo ============================================
echo.

rem Check if Python is available
where python >nul 2>&1
if errorlevel 1 (
    echo [!] ไม่พบ Python กรุณาติดตั้ง Python 3.11+ ก่อน
    echo.
    pause
    exit /b 1
)

rem Check if config.toml exists
if not exist config.toml (
    echo [!] ไม่พบไฟล์ config.toml
    echo    กรุณาคัดลอก config.example.toml มาเป็น config.toml แก้ไขให้ถูกต้อง
    echo.
    pause
    exit /b 1
)

rem Go straight to GUI (menu is hidden when CMD window is hidden)
goto gui

:gui
echo.
echo [AutoDJ] กำลังเปิด GUI...
python -m camfrog_autodj -c config.toml --lang th --gui
goto end

:console
echo.
echo [AutoDJ] โหมดคอนโซล (พิมพ์ !ช่วยเหลือ เพื่อดูคำสั่ง)
python -m camfrog_autodj -c config.toml --lang th --console
goto end

:check
echo.
echo [AutoDJ] ตรวจสอบการตั้งค่า...
python -m camfrog_autodj -c config.toml --check
goto end

:discover
echo.
echo [AutoDJ] ค้นหาห้อง Camfrog...
python -m camfrog_autodj -c config.toml --discover
goto end

:exit
echo.
echo [AutoDJ] ลาก่อน
goto end

:end
echo.
pause
