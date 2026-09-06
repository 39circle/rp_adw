@echo off
setlocal
cd /d "%~dp0"

set /p TARGET_NS=namespace を入力してください: 
if "%TARGET_NS%"=="" (
  echo namespace が空です。
  pause
  exit /b 1
)

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
  %PYEXE% %PYARGS% scripts\build_user_template.py "%TARGET_NS%"
) else (
  %PYEXE% scripts\build_user_template.py "%TARGET_NS%"
)
set ERR=%ERRORLEVEL%
if not %ERR%==0 echo 失敗しました。
pause
exit /b %ERR%
