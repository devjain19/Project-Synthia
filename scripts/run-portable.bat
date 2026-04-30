@echo off
setlocal
for %%I in ("%~dp0..") do set "ROOT=%%~fI"
if exist "%ROOT%\python-portable\python.exe" (
  "%ROOT%\python-portable\python.exe" %*
) else (
  python %*
)
