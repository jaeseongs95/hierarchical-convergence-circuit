@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0"
set "HCC_PY="
py -3.12 -c "import sys;raise SystemExit(sys.version_info[:2] < (3,12))" >nul 2>nul
if not errorlevel 1 set "HCC_PY=py -3.12"
if defined HCC_PY goto RUN
py -3 -c "import sys;raise SystemExit(sys.version_info[:2] < (3,12))" >nul 2>nul
if not errorlevel 1 set "HCC_PY=py -3"
if defined HCC_PY goto RUN
python -c "import sys;raise SystemExit(sys.version_info[:2] < (3,12))" >nul 2>nul
if not errorlevel 1 set "HCC_PY=python"
if defined HCC_PY goto RUN
echo Python 3.12+ was not found. Nothing was installed.
pause
exit /b 2
:RUN
%HCC_PY% -X utf8 -B "%~dp0scripts\run_indexed_experiment.py" %*
set "HCC_EXIT=%ERRORLEVEL%"
echo.
if not "%HCC_EXIT%"=="0" echo FAILED - original error and available evidence were preserved.
if not defined HCC_NO_PAUSE pause
exit /b %HCC_EXIT%
