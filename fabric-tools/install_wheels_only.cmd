@echo off
rem Installs project requirements using wheels only.
rem Usage: install_wheels_only.cmd [requirements-file]
rem If no requirements-file is provided it defaults to requirements.txt in the current directory.

setlocal enabledelayedexpansion

if "%~1"=="" (
  set REQ=requirements.txt
) else (
  set REQ=%~1
)

echo Installing using wheel-only policy from %REQ%
echo Upgrading pip first...
"%~dp0\..\.\venv\Scripts\python.exe" -m pip --version >nul 2>&1 || (
  rem fallback to system python
  python -m pip install --upgrade pip
  python -m pip install --only-binary=:all: -r "%REQ%"
  exit /b %ERRORLEVEL%
)

rem If a project venv exists under .venv or .fabric-env-1.3, users can activate it and re-run this script.
python -m pip install --upgrade pip
python -m pip install --only-binary=:all: -r "%REQ%"

if %ERRORLEVEL% EQU 0 (
  echo \nWheel-only install completed successfully.
) else (
  echo \nWheel-only install failed. pip reported an error. If pip attempted to build a source distribution, it will fail under the --only-binary flag.
  exit /b %ERRORLEVEL%
)

endlocal
