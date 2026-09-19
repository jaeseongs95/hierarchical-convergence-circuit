@echo off
setlocal
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PYTHONDONTWRITEBYTECODE=1"
set "HCR_PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if exist "%HCR_PY%" goto run
set "HCR_PY=python"
python -c "import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)" >nul 2>nul
if errorlevel 1 goto missing
:run
"%HCR_PY%" -X utf8 -B "%~dp0Run-HCR-R042.py" %*
set "HCR_EXIT=%ERRORLEVEL%"
if not "%HCR_EXIT%"=="0" echo ERROR: Stopped at the first failure. Existing evidence was retained.
if not defined HCR_NO_PAUSE pause
exit /b %HCR_EXIT%
:missing
echo Python 3.12 or later is required. No software was installed or downloaded.
if not defined HCR_NO_PAUSE pause
exit /b 1
