@echo off
setlocal
title Synthia Portable Backend

for %%I in ("%~dp0..") do set "ROOT=%%~fI"
set "PYTHON_CMD=python"
set "OLLAMA_EXE=%ROOT%\Shared\bin\ollama-windows.exe"
set "OLLAMA_HOST=http://127.0.0.1:11434"
set "OLLAMA_MODELS=%ROOT%\Shared\models\ollama_data"
set "OLLAMA_ORIGINS=*"

if exist "%ROOT%\python-portable\python.exe" (
    set "PYTHON_CMD=%ROOT%\python-portable\python.exe"
) else if exist "%ROOT%\Shared\python\python.exe" (
    set "PYTHON_CMD=%ROOT%\Shared\python\python.exe"
)

if exist "%OLLAMA_EXE%" (
    curl -s http://127.0.0.1:11434/api/tags >nul 2>&1
    if errorlevel 1 (
        start "" /b "%OLLAMA_EXE%" serve
        call :wait_for_ollama
    )
)

echo Starting Synthia backend...
%PYTHON_CMD% "%ROOT%\backend.py"

pause

exit /b

:wait_for_ollama
echo Waiting for Ollama to become ready...
:ollama_wait
curl -s http://127.0.0.1:11434/api/tags >nul 2>&1
if errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto ollama_wait
)
exit /b
