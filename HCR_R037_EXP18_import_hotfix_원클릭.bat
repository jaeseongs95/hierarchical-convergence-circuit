@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"
title HCR R037 EXP-18 Import Hotfix + Rerun

echo.
echo ============================================================
echo HCR R0.3.7 / EXP-18 import hotfix + 재실행
echo ============================================================
echo.

set "HOTFIX=HCR_R037_EXP18_import_hotfix.zip"

if not exist "src\hcr" (
  echo [오류] 현재 폴더가 프로젝트 루트가 아닙니다.
  goto :fail
)
if not exist "Run-HCR-R037.py" (
  echo [오류] R037 소스가 아직 프로젝트 루트에 설치되지 않았습니다.
  goto :fail
)
if not exist "%HOTFIX%" (
  echo [오류] %HOTFIX% 를 찾지 못했습니다.
  goto :fail
)

echo [1/3] import hotfix 적용 중...
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Stop'; Expand-Archive -LiteralPath '%HOTFIX%' -DestinationPath '%CD%' -Force"
if errorlevel 1 goto :fail
echo       완료

set "PY_EXE=%LocalAppData%\Programs\Python\Python312\python.exe"
set "PY_MODE="
if exist "%PY_EXE%" (
  "%PY_EXE%" -c "import sys; raise SystemExit(0 if sys.version_info >= (3,12) else 1)" >nul 2>&1
  if not errorlevel 1 set "PY_MODE=ABS"
)
if not defined PY_MODE (
  where py >nul 2>&1
  if not errorlevel 1 (
    py -3.12 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,12) else 1)" >nul 2>&1
    if not errorlevel 1 set "PY_MODE=PY"
  )
)
if not defined PY_MODE (
  where python >nul 2>&1
  if not errorlevel 1 (
    python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,12) else 1)" >nul 2>&1
    if not errorlevel 1 set "PY_MODE=PATH"
  )
)
if not defined PY_MODE (
  echo [오류] Python 3.12 이상을 찾지 못했습니다.
  goto :fail
)

echo.
echo [2/3] hotfix 후 R037 배포 해시 사전검사...
if "%PY_MODE%"=="ABS" (
  "%PY_EXE%" -X utf8 -B scripts\verify_r037.py
) else if "%PY_MODE%"=="PY" (
  py -3.12 -X utf8 -B scripts\verify_r037.py
) else (
  python -X utf8 -B scripts\verify_r037.py
)
if errorlevel 1 (
  echo [오류] hotfix 적용 후 R037 배포 검증에 실패했습니다.
  goto :fail
)
echo       완료

echo.
echo [3/3] EXP-18 전체 재실행...
set "OUT=HCR-Evidence\exp18\r037-first"
if exist "!OUT!" (
  for /f %%I in ('powershell.exe -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "STAMP=%%I"
  set "OUT=HCR-Evidence\exp18\r037-!STAMP!"
)
echo       결과 폴더: !OUT!
echo.

if "%PY_MODE%"=="ABS" (
  "%PY_EXE%" -X utf8 -B Run-HCR-R037.py --out "!OUT!"
  set "RC=!ERRORLEVEL!"
) else if "%PY_MODE%"=="PY" (
  py -3.12 -X utf8 -B Run-HCR-R037.py --out "!OUT!"
  set "RC=!ERRORLEVEL!"
) else (
  python -X utf8 -B Run-HCR-R037.py --out "!OUT!"
  set "RC=!ERRORLEVEL!"
)

if not "!RC!"=="0" (
  echo.
  echo [실패] 재실행이 중단되었습니다. 종료 코드: !RC!
  goto :fail
)

echo.
echo [성공] EXP-18 실행 및 검증 완료
echo 결과: !OUT!
echo 핵심 보고서: !OUT!\analysis\summary.ko.md
echo.
pause
exit /b 0

:fail
echo.
echo 작업이 완료되지 않았습니다. 위 오류를 확인하세요.
pause
exit /b 1
