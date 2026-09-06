@echo off
setlocal
cd /d "%~dp0"

set "PYEXE="
where py >nul 2>&1
if %errorlevel%==0 (
  set "PYEXE=py"
  set "PYARGS=-3"
)
if not defined PYEXE (
  where python >nul 2>&1
  if %errorlevel%==0 set "PYEXE=python"
)
if not defined PYEXE (
  where python3 >nul 2>&1
  if %errorlevel%==0 set "PYEXE=python3"
)
if not defined PYEXE (
  echo Python が見つかりません。Python 3 をインストールしてください。
  pause
  exit /b 1
)

if defined PYARGS (
  %PYEXE% %PYARGS% scripts\generator.py
) else (
  %PYEXE% scripts\generator.py
)
set ERR=%ERRORLEVEL%
if not %ERR%==0 echo 失敗しました。
pause
exit /b %ERR%
