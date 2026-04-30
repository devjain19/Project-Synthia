@echo off
setlocal
for %%I in ("%~dp0..") do set "ROOT=%%~fI"
if exist "%ROOT%\python-portable\python.exe" (
  "%ROOT%\python-portable\python.exe" "%ROOT%\scripts\synthia-terminal.py" %*
) else (
  python "%ROOT%\scripts\synthia-terminal.py" %*
)