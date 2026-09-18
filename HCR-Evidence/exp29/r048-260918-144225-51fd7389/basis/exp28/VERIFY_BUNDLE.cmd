@echo off
setlocal DisableDelayedExpansion
chcp 65001 >nul
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0source\scripts\launch_r047.ps1" -Repo "%~dp0source" -VerifyRun "%~dp0."
set "RC=%ERRORLEVEL%"
echo.
echo Verify exit code: %RC%
pause
exit /b %RC%
