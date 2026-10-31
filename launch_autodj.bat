@echo off
setlocal EnableDelayedEcho
rem Camfrog AutoDJ - Launcher for Windows
rem Double-click to open GUI, or run with arguments for other modes

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

echo [1] เปิดหน้าต่างเดสก์ท็อป GUI (ค่าเริ่มต้น)
echo [2] โหมดคอนโซล (พิมพ์คำสั่งผ่านแป้นพิมพ์)
echo [3] ตรวจสอบการตั้งค่า (--check)
echo [4] ค้นหาห้อง Camfrog อัตโนมัติ (--discover)
echo [5] ออกจากโปรแกรม
echo.
set /p choice="เลือกหมายเลข (1-5): "

if "%choice%"=="1" goto gui
if "%choice%"=="2" goto console
if "%choice%"=="3" goto check
if "%choice%"=="4" goto discover
if "%choice%"=="5" goto exit

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
