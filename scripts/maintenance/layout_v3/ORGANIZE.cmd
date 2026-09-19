@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONDONTWRITEBYTECODE=1"
set "HCC_PY="
if not defined HCR_PYTHON goto SELECT_PY
"%HCR_PYTHON%" -c "import sys;sys.exit(0 if sys.version_info >= (3,12) else 2)" >nul 2>&1
if errorlevel 1 goto NO_PY
set "HCC_PY=custom"
goto CUSTOM
:SELECT_PY
py -3.12 -c "import sys;sys.exit(0 if sys.version_info >= (3,12) else 2)" >nul 2>&1
if not errorlevel 1 set "HCC_PY=py -3.12"
if defined HCC_PY goto RUN
py -3 -c "import sys;sys.exit(0 if sys.version_info >= (3,12) else 2)" >nul 2>&1
if not errorlevel 1 set "HCC_PY=py -3"
if defined HCC_PY goto RUN
python -c "import sys;sys.exit(0 if sys.version_info >= (3,12) else 2)" >nul 2>&1
if not errorlevel 1 set "HCC_PY=python"
if not defined HCC_PY goto NO_PY
:RUN
%HCC_PY% -X utf8 -B "%~dp0verify_package.py"
if errorlevel 1 goto FAILED
%HCC_PY% -X utf8 -B "%~dp0main.py" apply
set "RC=%ERRORLEVEL%"
goto END
:CUSTOM
"%HCR_PYTHON%" -X utf8 -B "%~dp0verify_package.py"
if errorlevel 1 goto FAILED
"%HCR_PYTHON%" -X utf8 -B "%~dp0main.py" apply
set "RC=%ERRORLEVEL%"
goto END
:NO_PY
echo Existing Python 3.12+ not found. No software was installed.
:FAILED
set "RC=2"
:END
echo.
if not "%RC%"=="0" echo STOPPED - see the evidence path and error above.
if not defined HCC_NO_PAUSE pause
exit /b %RC%
