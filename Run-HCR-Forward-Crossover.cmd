@echo off
setlocal
set "PYTHON=C:\Users\Lenovo\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if not exist "%PYTHON%" exit /b 2
pushd "%~dp0"
"%PYTHON%" -B -X utf8 tools\analysis\termination_forward_crossover.py %*
set "RESULT=%ERRORLEVEL%"
popd
exit /b %RESULT%
