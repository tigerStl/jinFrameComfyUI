# Shared GPU detection helpers (dot-source from other install scripts).

function Get-SmiGpuInfo {
    $out = @{ ok = $false; name = ""; driver = ""; lost = $false; raw = "" }
    if (-not (Get-Command nvidia-smi -ErrorAction SilentlyContinue)) {
        return $out
    }
    $raw = (& nvidia-smi 2>&1 | Out-String)
    $out.raw = $raw
    if ($raw -match "GPU is lost|Unable to determine the device handle") {
        $out.lost = $true
        return $out
    }
    try {
        $out.name = (& nvidia-smi --query-gpu=name --format=csv,noheader 2>$null | Select-Object -First 1).Trim()
        $out.driver = (& nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>$null | Select-Object -First 1).Trim()
        if ($out.name) { $out.ok = $true }
    } catch { }
    return $out
}

function Test-Rtx50GpuName {
    param([string]$Name)
    if (-not $Name) { return $false }
    $u = $Name.ToUpperInvariant()
    if ($u -match '\bRTX\s*30[0-9]{2}\b') { return $false }
    if ($u -match '\bRTX\s*40[0-9]{2}\b') { return $false }
    if ($u -match '\bRTX\s*50[0-9]{2}\b') { return $true }
    if ($u -match '\b(5050|5060|5070|5080|5090)\b') { return $true }
    return $false
}

function New-GpuProfileObject {
    param(
        [string]$GpuName,
        [string]$Driver = ""
    )
    $launch = "--lowvram --disable-cuda-malloc"
    if (Test-Rtx50GpuName $GpuName) {
        return [PSCustomObject]@{
            has_nvidia         = $true
            gpu_name           = $GpuName
            driver_version     = $Driver
            torch_profile      = "cu128_nightly"
            torch_index_url    = "https://download.pytorch.org/whl/nightly/cu128"
            torch_nightly      = $true
            comfy_launch_extra = $launch
            min_cuda_major     = 12
            reason             = "RTX 50 series: PyTorch cu128 nightly (sm_120)."
            detected_at        = (Get-Date).ToString("o")
        }
    }
    return [PSCustomObject]@{
        has_nvidia         = $true
        gpu_name           = $GpuName
        driver_version     = $Driver
        torch_profile      = "cu130"
        torch_index_url    = "https://download.pytorch.org/whl/cu130"
        torch_nightly      = $false
        comfy_launch_extra = $launch
        min_cuda_major     = 13
        reason             = "RTX 30/40 series: PyTorch cu130 for ComfyUI 0.21+."
        detected_at        = (Get-Date).ToString("o")
    }
}

function Test-ProfileMatchesGpu {
    param($Profile, [string]$GpuName)
    if (-not $Profile -or -not $GpuName) { return $false }
    $is50 = Test-Rtx50GpuName $GpuName
    if ($is50 -and $Profile.torch_profile -eq "cu128_nightly") { return $true }
    if (-not $is50 -and $Profile.torch_profile -eq "cu130") { return $true }
    return $false
}

function Test-TorchTagMatchesProfile {
    param([string]$TorchVersion, [string]$ProfileName)
    if ($ProfileName -eq "cu130") { return $TorchVersion -match "\+cu130" }
    if ($ProfileName -eq "cu128_nightly") { return $TorchVersion -match "\+cu128" }
    return $true
}

# PyTorch cu130 (CUDA 13) needs Windows driver 580+; cu128 nightly needs ~570+
function Test-NvidiaDriverVersion {
    param(
        [string]$DriverVersion,
        [string]$MinVersion
    )
    if ([string]::IsNullOrWhiteSpace($DriverVersion)) { return $false }
    try {
        return ([version]$DriverVersion -ge [version]$MinVersion)
    } catch {
        return $false
    }
}

function Test-DriverForTorchProfile {
    param(
        [string]$DriverVersion,
        [string]$TorchProfile
    )
    switch ($TorchProfile) {
        "cu130" { return (Test-NvidiaDriverVersion $DriverVersion "580.0") }
        "cu128_nightly" { return (Test-NvidiaDriverVersion $DriverVersion "570.0") }
        default { return $true }
    }
}

function Get-DriverHintForProfile {
    param([string]$TorchProfile)
    if ($TorchProfile -eq "cu130") {
        return "NVIDIA driver 580.0+ required for PyTorch cu130 / CUDA 13 (ComfyUI 0.21+)."
    }
    if ($TorchProfile -eq "cu128_nightly") {
        return "NVIDIA driver 570.0+ recommended for PyTorch cu128 nightly."
    }
    return ""
}

function Get-WindowsNvidiaOsId {
    if ([System.Environment]::OSVersion.Version.Build -ge 22000) { return 135 }
    return 57
}

function Get-LatestGeForceGameReadyDriver {
  <# Query NVIDIA for latest WHQL Game Ready driver (all GeForce, Win10/11 64 DCH). #>
    param([int]$OsId = 0)
    if ($OsId -eq 0) { $OsId = Get-WindowsNvidiaOsId }
    $uri = "https://www.nvidia.com/Download/processFind.aspx?psid=107&pfid=879&osid=$OsId&lid=1&whql=1&lang=en-us&ctk=0&dtcid=1"
    $r = Invoke-WebRequest -Uri $uri -UseBasicParsing -Headers @{ "User-Agent" = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" }
    $vers = [regex]::Matches($r.Content, 'class="gridItem">([0-9]+\.[0-9]+)</td>')
    if ($vers.Count -eq 0) { return $null }
    $best = $null
    foreach ($m in $vers) {
        $v = $m.Groups[1].Value
        try {
            $ver = [version]$v
            if (-not $best -or $ver -gt $best.Version) {
                $best = [PSCustomObject]@{
                    Version     = $v
                    DownloadUrl = "https://us.download.nvidia.com/Windows/$v/$v-desktop-win10-win11-64bit-international-dch-whql.exe"
                    OsId        = $OsId
                }
            }
        } catch { }
    }
    return $best
}

function Get-RebootPendingFile {
    param([string]$RepoRoot)
    return (Join-Path $RepoRoot "jinframe_reboot_pending.json")
}

function Set-RebootPending {
    param(
        [string]$RepoRoot,
        [string]$Reason,
        [string]$Detail = ""
    )
    $path = Get-RebootPendingFile $RepoRoot
    @{
        reason     = $Reason
        detail     = $Detail
        created_at = (Get-Date).ToString("o")
    } | ConvertTo-Json -Depth 3 | Set-Content -Path $path -Encoding UTF8
    return $path
}

function Test-RebootPending {
    param([string]$RepoRoot)
    $path = Get-RebootPendingFile $RepoRoot
    return (Test-Path $path)
}

function Clear-RebootPending {
    param([string]$RepoRoot)
    $path = Get-RebootPendingFile $RepoRoot
    if (Test-Path $path) { Remove-Item $path -Force }
}

function Test-IsAdmin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $p = New-Object Security.Principal.WindowsPrincipal $id
    return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}
