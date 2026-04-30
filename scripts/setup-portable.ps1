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

function Ensure-Dirs {
    $dirs = @($Shared, $Bin, $Models, $GGUF, $OllamaModels, $ModelFiles, $Data)
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
    if (Cmd-Exists curl) {
        Write-Host "Downloading $url -> $out (using curl)"
        & curl -L --retry 5 --retry-delay 3 -o "$out" "$url"
    } else {
        Write-Host "Downloading $url -> $out (using Invoke-WebRequest)"
        Invoke-WebRequest -Uri $url -OutFile $out -UseBasicParsing -TimeoutSec 300
    }
}

function Install-Embeddable-Python {
    param($arch = "amd64")
    $pyVersion = '3.11.4'
    if ($arch -eq 'amd64') {
        $zipName = "python-$pyVersion-embed-amd64.zip"
    } else {
        $zipName = "python-$pyVersion-embed-win32.zip"
    }

    $url = "https://www.python.org/ftp/python/$pyVersion/$zipName"
    $outZip = Join-Path $Bin $zipName
    if (-not (Test-Path $outZip)) {
        Download-File $url $outZip
    } else {
        Write-Host "Embeddable archive already present: $outZip"
    }

    $target = Join-Path $ROOT "python-portable"
    if (-not (Test-Path $target)) { New-Item -ItemType Directory -Path $target | Out-Null }

    Write-Host "Extracting to $target"
    Expand-Archive -Path $outZip -DestinationPath $target -Force

    $pyExe = Get-ChildItem -Path $target -Recurse -Filter python.exe -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $pyExe) { throw 'python.exe not found in extracted embeddable archive' }
    $pyPath = $pyExe.FullName

    $getpip = Join-Path $Bin 'get-pip.py'
    if (-not (Test-Path $getpip)) { Download-File 'https://bootstrap.pypa.io/get-pip.py' $getpip }

    Write-Host "Installing pip into portable python ($pyPath)"
    & "$pyPath" "$getpip"

    Write-Host "Installing recommended Python packages (requests)"
    try {
        & "$pyPath" -m pip install --no-warn-script-location requests
    } catch {
        Write-Host 'pip install failed or already present'
    }

    return $pyPath
}

function Ensure-Python {
    Write-Host "Checking for existing Python..."
    $py = Get-Command python -ErrorAction SilentlyContinue
    if ($py) {
        try {
            $ver = & python -c "import sys; print('.'.join(map(str, sys.version_info[:3])))" 2>&1
            Write-Host "Found system Python: $ver"
            return (Get-Command python).Source
        } catch {
            Write-Host "System python exists but failed to execute: $_"
        }
    }

    if ($NonInteractive) { $choice = 'Y' } else { $choice = Read-Host "No python found in PATH. Download embeddable Python and install (Y/n)?" }
    if ($choice -in @('Y', 'y', '', $null)) {
        return Install-Embeddable-Python -arch 'amd64'
    }
    throw 'Python not available'
}

function Maybe-Install-Ollama {
    $installer = Join-Path $ScriptRoot 'install-local-ollama.bat'
    if (Test-Path $installer) {
        if ($NonInteractive) { $run = 'Y' } else { $run = Read-Host "Found install-local-ollama.bat. Run it now to install Ollama (Y/n)?" }
        if ($run -in @('Y','y','','Yes')) {
            Write-Host "Running $installer"
            Start-Process -FilePath cmd -ArgumentList '/c', "$installer" -NoNewWindow -Wait
        }
    } else {
        Write-Host "No local Ollama installer found at $installer. You can place ollama binary at Shared/bin or run install-local-ollama.bat manually."
    }
}

try {
    Ensure-Dirs
    $pythonExe = Ensure-Python
    Maybe-Install-Ollama
    Write-Host "Setup complete."
    Write-Host "Run scripts\start-synthia.bat to launch the app."
    if ($pythonExe) {
        Write-Host "Portable/system Python ready: $pythonExe"
    }
} catch {
    Write-Error "Setup failed: $_"
    exit 1
}
