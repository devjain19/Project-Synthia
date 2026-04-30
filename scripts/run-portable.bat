@echo off
setlocal enabledelayedexpansion
for %%I in ("%~dp0..") do set "ROOT=%%~fI"

REM Prefer bundled/embedded Python on the USB even if system Python exists.
REM Check multiple candidate locations and use the first python.exe found.
set "PYEXE="
if exist "%ROOT%\python-embed\python.exe" set "PYEXE=%ROOT%\python-embed\python.exe"
if not defined PYEXE if exist "%ROOT%\python-portable\python.exe" set "PYEXE=%ROOT%\python-portable\python.exe"
if not defined PYEXE if exist "%ROOT%\python\python.exe" set "PYEXE=%ROOT%\python\python.exe"
if not defined PYEXE if exist "%ROOT%\venv\Scripts\python.exe" set "PYEXE=%ROOT%\venv\Scripts\python.exe"
if not defined PYEXE if exist "%ROOT%\python.exe" set "PYEXE=%ROOT%\python.exe"

if defined PYEXE (
  echo Using bundled Python: %PYEXE%
  "%PYEXE%" %*
) else (
  REM No bundled Python found; fall back to system python (may fail if not installed)
  echo No bundled Python found; falling back to system Python.
  python %*
)
