@echo off
setlocal
title Install Local Ollama For Synthia

for %%I in ("%~dp0..") do set "ROOT=%%~fI"
set "SHARED=%ROOT%\Shared"
set "BIN_DIR=%SHARED%\bin"
set "MODELS_DIR=%SHARED%\models\ollama_data"
set "TMP_ZIP=%SHARED%\ollama-windows-amd64.zip"
set "TMP_EXTRACT=%SHARED%\_ollama_extract"

if not exist "%SHARED%" mkdir "%SHARED%"
if not exist "%BIN_DIR%" mkdir "%BIN_DIR%"
if not exist "%MODELS_DIR%" mkdir "%MODELS_DIR%"

echo Downloading Ollama for Windows...
set /a ATTEMPT=0
:download_retry
set /a ATTEMPT+=1
echo Attempt %ATTEMPT%/5
curl -L -C - --retry 5 --retry-delay 4 --retry-all-errors "https://github.com/ollama/ollama/releases/latest/download/ollama-windows-amd64.zip" -o "%TMP_ZIP%"
if errorlevel 1 (
  if %ATTEMPT% LSS 5 (
    echo Download interrupted. Retrying in 3 seconds...
    timeout /t 3 /nobreak >nul
    goto download_retry
  )
  echo Failed to download Ollama zip after multiple attempts.
  pause
  exit /b 1
)

if exist "%TMP_EXTRACT%" rmdir /s /q "%TMP_EXTRACT%"
mkdir "%TMP_EXTRACT%"

echo Extracting archive...
powershell -NoProfile -Command "Expand-Archive -Path '%TMP_ZIP%' -DestinationPath '%TMP_EXTRACT%' -Force"
if errorlevel 1 (
  echo Extraction failed.
  pause
  exit /b 1
)

set "FOUND_EXE="
for /r "%TMP_EXTRACT%" %%f in (ollama.exe) do (
  set "FOUND_EXE=%%f"
  goto :found
)

:found
if "%FOUND_EXE%"=="" (
  echo Could not find ollama.exe in extracted files.
  pause
  exit /b 1
)

copy /y "%FOUND_EXE%" "%BIN_DIR%\ollama-windows.exe" >nul
if errorlevel 1 (
  echo Could not copy ollama executable.
  pause
  exit /b 1
)

del /q "%TMP_ZIP%" >nul 2>&1
rmdir /s /q "%TMP_EXTRACT%" >nul 2>&1

echo.
echo Ollama installed at: %BIN_DIR%\ollama-windows.exe
echo Model cache directory: %MODELS_DIR%
echo.
echo Next step: Run scripts\start-synthia.bat
pause
