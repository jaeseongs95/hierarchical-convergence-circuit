@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if exist "%PY%" goto runlocal
where python >nul 2>nul
if errorlevel 1 (
  echo Python 3.12+ was not found. Run Run-HCR-R038.py with your Python executable.
  pause
  exit /b 1
)
python -X utf8 -B "%~dp0Run-HCR-R038.py" %*
goto done
:runlocal
"%PY%" -X utf8 -B "%~dp0Run-HCR-R038.py" %*
:done
set "RESULT=%ERRORLEVEL%"
echo Exit code: %RESULT%
pause
exit /b %RESULT%
