param(
    [switch]$NonInteractive
)

Set-StrictMode -Version Latest
$ScriptRoot = $PSScriptRoot
$ROOT = (Resolve-Path (Join-Path $ScriptRoot "..")).Path
$Shared = Join-Path $ROOT "Shared"
$Bin = Join-Path $Shared "bin"
$Models = Join-Path $Shared "models"
$GGUF = Join-Path $Models "gguf"
$OllamaModels = Join-Path $Models "ollama_data"
$ModelFiles = Join-Path $Models "modelfiles"
$Data = Join-Path $ROOT "chat_data"
$PortablePythonRoot = Join-Path $ROOT "python-embed"
$PortablePythonZip = Join-Path $Bin "python-3.11.4-embed-amd64.zip"
$PortablePythonExe = Join-Path $PortablePythonRoot "python.exe"

function Ensure-Dirs {
    $dirs = @($Shared, $Bin, $Models, $GGUF, $OllamaModels, $ModelFiles, $Data, $PortablePythonRoot)
    foreach ($d in $dirs) {
        if (-not (Test-Path $d)) {
            Write-Host "Creating: $d"
            New-Item -ItemType Directory -Path $d | Out-Null
        }
    }
}

function Cmd-Exists($name) {
    return (Get-Command $name -ErrorAction SilentlyContinue) -ne $null
}

function Download-File($url, $out) {
    # Prefer an actual curl.exe if present (PowerShell 'curl' is often an alias to Invoke-WebRequest)
    $curlExe = Get-Command curl.exe -ErrorAction SilentlyContinue
    if ($curlExe -and $curlExe.CommandType -eq 'Application') {
        Write-Host "Downloading $url -> $out (using curl.exe)"
        & "$($curlExe.Source)" -L --retry 5 --retry-delay 3 -o "$out" "$url"
    } else {
        Write-Host "Downloading $url -> $out (using Invoke-WebRequest)"
        Invoke-WebRequest -Uri $url -OutFile $out -UseBasicParsing -TimeoutSec 300
    }
}

function Install-Embeddable-Python {
    param([string]$ZipPath, [string]$TargetPath)

    $pyVersion = '3.11.4'
    $zipName = Split-Path $ZipPath -Leaf
    $url = "https://www.python.org/ftp/python/$pyVersion/$zipName"

    if (-not (Test-Path $ZipPath)) {
        Download-File $url $ZipPath
    } else {
        Write-Host "Embeddable archive already present: $ZipPath"
    }

    if (-not (Test-Path $TargetPath)) { New-Item -ItemType Directory -Path $TargetPath | Out-Null }

    Write-Host "Extracting portable Python to $TargetPath"
    Expand-Archive -Path $ZipPath -DestinationPath $TargetPath -Force

    $pthFile = Get-ChildItem -Path $TargetPath -Filter '*._pth' -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($pthFile) {
        $pthContent = Get-Content -Path $pthFile.FullName
        if ($pthContent -notcontains 'import site') {
            Add-Content -Path $pthFile.FullName -Value 'import site'
        }
    }

    $pyExe = Get-ChildItem -Path $TargetPath -Recurse -Filter python.exe -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $pyExe) { throw 'python.exe not found in extracted embeddable archive' }

    $getpip = Join-Path $Bin 'get-pip.py'
    if (-not (Test-Path $getpip)) { Download-File 'https://bootstrap.pypa.io/get-pip.py' $getpip }

    Write-Host "Installing pip into portable python ($($pyExe.FullName))"
    & $pyExe.FullName $getpip

    Write-Host "Installing bundled Python dependencies"
    try {
        & $pyExe.FullName -m pip install --no-warn-script-location requests
    } catch {
        Write-Host 'pip install failed or was already satisfied'
    }

    return $pyExe.FullName
}

function Ensure-Python {
    Write-Host "Installing/refreshing portable Python in $PortablePythonRoot"
    return Install-Embeddable-Python -ZipPath $PortablePythonZip -TargetPath $PortablePythonRoot
}

function Maybe-Install-Ollama {
    $installer = Join-Path $ScriptRoot 'install-local-ollama.bat'
    if (Test-Path $installer) {
        Write-Host "Running $installer"
        Start-Process -FilePath cmd -ArgumentList @('/c', ('"{0}"' -f $installer)) -NoNewWindow -Wait
    } else {
        Write-Host "No local Ollama installer found at $installer. You can place ollama binary at Shared/bin or run install-local-ollama.bat manually."
    }
}

function Verify-Setup {
    $pyExe = $PortablePythonExe
    if (-not (Test-Path $pyExe)) { throw "Portable Python not found at $pyExe" }

    $ollamaExe = Join-Path $Bin 'ollama-windows.exe'
    if (-not (Test-Path $ollamaExe)) { throw "Ollama executable not found at $ollamaExe" }

    Write-Host "Verifying portable Python..."
    & $pyExe -c "import sys; print(sys.executable); print('.'.join(map(str, sys.version_info[:3])))"

    Write-Host "Verifying Ollama executable..."
    & $ollamaExe --version
}

try {
    Ensure-Dirs
    $pythonExe = Ensure-Python
    Maybe-Install-Ollama
    Verify-Setup
    Write-Host "Setup complete."
    Write-Host "Run scripts\run-portable.bat or scripts\launch-with-embedded-python.bat to launch the app."
    if ($pythonExe) {
        Write-Host "Portable/system Python ready: $pythonExe"
    }
} catch {
    Write-Error "Setup failed: $_"
    exit 1
}
