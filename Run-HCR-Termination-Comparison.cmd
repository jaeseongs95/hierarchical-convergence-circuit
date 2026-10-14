@echo off
setlocal
cd /d "%~dp0"
set "HCR_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if not exist "%HCR_PYTHON%" exit /b 2
if "%~1"=="" (
  "%HCR_PYTHON%" -B -X utf8 tools\analysis\termination_compare_runner.py --self-test
) else (
  "%HCR_PYTHON%" -B -X utf8 tools\analysis\termination_compare_runner.py %*
)
exit /b %errorlevel%
