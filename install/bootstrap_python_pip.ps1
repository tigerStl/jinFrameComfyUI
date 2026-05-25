# Install pip into Python (full install or embeddable). Idempotent.
# Usage: .\install\bootstrap_python_pip.ps1 -PythonExe "K:\tools\Python312\python.exe"

param(
    [Parameter(Mandatory = $true)]
    [string]$PythonExe
)

$PythonExe = [System.IO.Path]::GetFullPath($PythonExe)
if (-not (Test-Path $PythonExe)) {
    Write-Error "Python not found: $PythonExe"
    exit 1
}

function Invoke-Python {
    param([string[]]$Args)
    $p = Start-Process -FilePath $PythonExe -ArgumentList $Args -Wait -PassThru -NoNewWindow
    return $p.ExitCode
}

function Test-PipOk {
    $code = Invoke-Python -Args @("-m", "pip", "--version")
    return $code -eq 0
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
    Invoke-Python -Args @("-m", "pip", "--version") | Out-Null
    & $PythonExe -m pip --version
    exit 0
}

Write-Host "[pip] bootstrapping for $PythonExe" -ForegroundColor Yellow

# ensurepip (may be missing on embeddable — non-fatal)
$code = Invoke-Python -Args @("-m", "ensurepip", "--upgrade")
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

$code = Invoke-Python -Args @($getPip, "--no-warn-script-location")
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
