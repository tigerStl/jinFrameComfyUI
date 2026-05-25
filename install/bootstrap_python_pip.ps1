# Install pip into Python (full install or embeddable). Idempotent.
# Usage: .\install\bootstrap_python_pip.ps1 -PythonExe "K:\tools\Python312\python.exe"

param(
    [Parameter(Mandatory = $true)]
    [string]$PythonExe
)

$ErrorActionPreference = "Stop"
$PythonExe = [System.IO.Path]::GetFullPath($PythonExe)
if (-not (Test-Path $PythonExe)) {
    throw "Python not found: $PythonExe"
}

function Test-PipOk {
    & $PythonExe -m pip --version 2>$null | Out-Null
    return $LASTEXITCODE -eq 0
}

if (Test-PipOk) {
    Write-Host "[pip] already installed" -ForegroundColor Green
    & $PythonExe -m pip --version
    exit 0
}

Write-Host "[pip] bootstrapping for $PythonExe" -ForegroundColor Yellow

# Enable site for embeddable
$pyDir = Split-Path $PythonExe -Parent
$pth = Get-ChildItem -Path $pyDir -Filter "python*._pth" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($pth) {
    $text = Get-Content $pth.FullName -Raw
    if ($text -match '#import site') {
        Set-Content -Path $pth.FullName -Value ($text.Replace('#import site', 'import site')) -NoNewline
        Write-Host "[pip] enabled import site in $($pth.Name)" -ForegroundColor DarkGray
    }
}

$prevEap = $ErrorActionPreference
$ErrorActionPreference = 'Continue'

& $PythonExe -m ensurepip --upgrade 2>&1 | ForEach-Object { Write-Host "    $_" }
if (Test-PipOk) {
    Write-Host "[pip] ready (ensurepip)" -ForegroundColor Green
    exit 0
}

$getPip = Join-Path $env:TEMP "jinframe_get-pip.py"
Write-Host "[pip] downloading get-pip.py ..." -ForegroundColor Yellow
Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile $getPip -UseBasicParsing

& $PythonExe $getPip --no-warn-script-location 2>&1 | ForEach-Object { Write-Host "    $_" }
$ErrorActionPreference = $prevEap

if (-not (Test-PipOk)) {
    throw "pip bootstrap failed for $PythonExe"
}

Write-Host "[pip] ready (get-pip)" -ForegroundColor Green
& $PythonExe -m pip --version
