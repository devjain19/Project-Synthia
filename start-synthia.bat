@echo off
setlocal
title Synthia Portable Backend

set "ROOT=%~dp0"
set "OLLAMA_EXE=%ROOT%Shared\bin\ollama-windows.exe"
set "OLLAMA_HOST=http://127.0.0.1:11434"
set "OLLAMA_MODELS=%ROOT%Shared\models\ollama_data"
set "OLLAMA_ORIGINS=*"
set "RUN_PORTABLE=%ROOT%scripts\run-portable.bat"

if exist "%OLLAMA_EXE%" (
    curl -s http://127.0.0.1:11434/api/tags >nul 2>&1
    if errorlevel 1 (
        start "" /b "%OLLAMA_EXE%" serve
        call :wait_for_ollama
    )
)

echo Starting Synthia backend...
if exist "%RUN_PORTABLE%" (
    call "%RUN_PORTABLE%" "%ROOT%backend.py"
) else (
    echo run-portable.bat not found at %RUN_PORTABLE%
    exit /b 1
)

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