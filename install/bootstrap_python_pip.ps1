# Install pip into Python (full install or embeddable). Idempotent.
# Usage: .\install\bootstrap_python_pip.ps1 -PythonExe "K:\tools\Python312\python.exe"
# (Run in PowerShell, or let 一键安装.bat invoke it automatically.)

param(
    [Parameter(Mandatory = $true)]
    [string]$PythonExe
)

$PythonExe = [System.IO.Path]::GetFullPath($PythonExe)
if (-not (Test-Path $PythonExe)) {
    Write-Error "Python not found: $PythonExe"
    exit 1
}

function Invoke-PythonCli {
    param([string[]]$PythonArgs)
    if (-not $PythonArgs -or $PythonArgs.Count -eq 0) {
        throw "Invoke-PythonCli: empty argument list"
    }
    $p = Start-Process -FilePath $PythonExe -ArgumentList $PythonArgs -Wait -PassThru -NoNewWindow
    return $p.ExitCode
}

function Test-PipOk {
    return (Invoke-PythonCli -PythonArgs @("-m", "pip", "--version")) -eq 0
}

# Enable site-packages for Windows embeddable (must run before pip bootstrap)
$pyDir = Split-Path $PythonExe -Parent
$pth = Get-ChildItem -Path $pyDir -Filter "python*._pth" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($pth) {
    $text = Get-Content $pth.FullName -Raw
    if ($text -match '#import site') {
        Set-Content -Path $pth.FullName -Value ($text.Replace('#import site', 'import site')) -NoNewline
        Write-Host "[pip] enabled import site in $($pth.Name)" -ForegroundColor DarkGray
    }
}

if (Test-PipOk) {
    Write-Host "[pip] already installed" -ForegroundColor Green
    & $PythonExe -m pip --version
    exit 0
}

Write-Host "[pip] bootstrapping for $PythonExe" -ForegroundColor Yellow

$code = Invoke-PythonCli -PythonArgs @("-m", "ensurepip", "--upgrade")
if ($code -ne 0) {
    Write-Host "[pip] ensurepip not available (exit $code), trying get-pip.py ..." -ForegroundColor DarkYellow
}

if (Test-PipOk) {
    Write-Host "[pip] ready (ensurepip)" -ForegroundColor Green
    & $PythonExe -m pip --version
    exit 0
}

$getPip = Join-Path $env:TEMP "jinframe_get-pip.py"
Write-Host "[pip] downloading get-pip.py ..." -ForegroundColor Yellow
try {
    Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile $getPip -UseBasicParsing
} catch {
    Write-Error "Failed to download get-pip.py: $_"
    exit 1
}

if (-not (Test-Path $getPip)) {
    Write-Error "get-pip.py not found after download: $getPip"
    exit 1
}

$code = Invoke-PythonCli -PythonArgs @($getPip, "--no-warn-script-location")
if ($code -ne 0) {
    Write-Error "get-pip.py failed with exit code $code"
    exit 1
}

if (-not (Test-PipOk)) {
    Write-Error "pip bootstrap failed for $PythonExe"
    exit 1
}

Write-Host "[pip] ready (get-pip)" -ForegroundColor Green
& $PythonExe -m pip --version
exit 0
