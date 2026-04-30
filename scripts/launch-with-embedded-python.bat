@echo off
REM Launcher to run backend using an included/embedded Python on a USB drive.
REM Place this file in the `scripts` folder. It will look for python.exe in common locations
REM relative to the repository root (one level up from this script).

setlocal enabledelayedexpansion
set SCRIPT_DIR=%~dp0
set REPO_ROOT=%SCRIPT_DIR%..\

REM candidate locations (relative to repo root)
set CANDIDATE=%REPO_ROOT%python-embed\python.exe
if exist "%CANDIDATE%" set PYEXE=%CANDIDATE%

if not defined PYEXE (
  set CANDIDATE=%REPO_ROOT%python\python.exe
  if exist "%CANDIDATE%" set PYEXE=%CANDIDATE%
)

if not defined PYEXE (
  set CANDIDATE=%REPO_ROOT%venv\Scripts\python.exe
  if exist "%CANDIDATE%" set PYEXE=%CANDIDATE%
)

if not defined PYEXE (
  set CANDIDATE=%REPO_ROOT%python.exe
  if exist "%CANDIDATE%" set PYEXE=%CANDIDATE%
)

if not defined PYEXE (
  echo No bundled Python found. Put the Windows embeddable distribution into "%REPO_ROOT%python-embed\" or create a venv at "%REPO_ROOT%venv\" and place this launcher back on the USB.
  echo Alternatively install Python on the target machine.
  pause
  exit /b 1
)

pushd %REPO_ROOT%
echo Using Python: %PYEXE%
REM Ensure backend.py is present
if not exist backend.py (
  echo backend.py not found in %REPO_ROOT%
  popd
  exit /b 1
)

REM Start the backend in a new window so user can see logs (adjust args if needed)
start "Synthia Backend" "%PYEXE%" backend.py
popd

echo Backend started (if no errors). Open synthia.html in your browser and point to http://127.0.0.1:3333
exit /b 0
