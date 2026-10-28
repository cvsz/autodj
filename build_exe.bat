@echo off
rem Thin wrapper: everything lives in build.ps1 (build + sign). Extra args are passed on, e.g. build_exe.bat -Clean
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build.ps1" %*
