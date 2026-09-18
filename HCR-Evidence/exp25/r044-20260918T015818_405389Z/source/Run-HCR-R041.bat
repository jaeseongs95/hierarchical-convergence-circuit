@echo off
chcp 65001 >nul
setlocal DisableDelayedExpansion
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\bootstrap_r041.ps1" -Repo "%~dp0."
set "RC=%ERRORLEVEL%"
echo.
echo Exit code: %RC%
pause
exit /b %RC%
