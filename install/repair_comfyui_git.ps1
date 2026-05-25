# Re-clone broken custom_nodes (e.g. ComfyUI-Manager: unable to read tree)
param(
    [string]$ComfyRoot = "",
    [string[]]$Nodes = @("ComfyUI-Manager")
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")

if (-not $ComfyRoot) {
    $cfg = Join-Path $RepoRoot "jinframe_install_paths.json"
    if (Test-Path $cfg) {
        $ComfyRoot = (Get-Content $cfg -Raw | ConvertFrom-Json).comfyui_root
    }
}
if (-not $ComfyRoot) { $ComfyRoot = $env:COMFYUI_ROOT }
if (-not $ComfyRoot) { throw "Specify -ComfyRoot" }

$ComfyRoot = [System.IO.Path]::GetFullPath($ComfyRoot)
$CustomNodes = Join-Path $ComfyRoot "custom_nodes"

foreach ($name in $Nodes) {
    $dest = Join-Path $CustomNodes $name
    if (Test-Path $dest) {
        Write-Host "Removing $dest ..." -ForegroundColor Yellow
        Remove-Item $dest -Recurse -Force
    }
}

& (Join-Path $PSScriptRoot "setup_comfyui.ps1") -ComfyRoot $ComfyRoot -Force
Write-Host "Git repair done." -ForegroundColor Green
