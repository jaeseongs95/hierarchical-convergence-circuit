@echo off
setlocal
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONDONTWRITEBYTECODE=1"
if defined HCC_PYTHON goto custom
py -3.12 -c "import sys; sys.exit(sys.version_info[0:2] not in [(3,n) for n in range(12,100)])" >nul 2>&1
if not errorlevel 1 goto py312
py -3 -c "import sys; sys.exit(sys.version_info[0:2] not in [(3,n) for n in range(12,100)])" >nul 2>&1
if not errorlevel 1 goto py3
python -c "import sys; sys.exit(sys.version_info[0:2] not in [(3,n) for n in range(12,100)])" >nul 2>&1
if not errorlevel 1 goto python
 echo Existing Python 3.12+ was not found. Nothing was installed.
set "RC=2"
goto finish
:custom
"%HCC_PYTHON%" -X utf8 -B "%~dp0Run-HCR-R073.py" %*
set "RC=%ERRORLEVEL%"
goto finish
:py312
py -3.12 -X utf8 -B "%~dp0Run-HCR-R073.py" %*
set "RC=%ERRORLEVEL%"
goto finish
:py3
py -3 -X utf8 -B "%~dp0Run-HCR-R073.py" %*
set "RC=%ERRORLEVEL%"
goto finish
:python
python -X utf8 -B "%~dp0Run-HCR-R073.py" %*
set "RC=%ERRORLEVEL%"
:finish
if not "%RC%"=="0" echo FAILED. No automatic retry was attempted. See the retained logs.
if not defined HCC_NO_PAUSE pause
exit /b %RC%
