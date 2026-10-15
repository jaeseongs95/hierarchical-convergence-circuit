@echo off
setlocal
set "R11_PY=C:\Users\Lenovo\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if not exist "%R11_PY%" exit /b 2
if "%~1"=="" (
  "%R11_PY%" -B -X utf8 "%~dp0tools\analysis\termination_certificate_cost.py" --self-test
) else (
  "%R11_PY%" -B -X utf8 "%~dp0tools\analysis\termination_certificate_cost.py" %*
)
exit /b %errorlevel%
