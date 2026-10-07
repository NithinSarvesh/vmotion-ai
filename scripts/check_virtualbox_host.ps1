<#
.SYNOPSIS
    VMotion AI - Inspect Oracle VirtualBox Host Health and Inventory.
.DESCRIPTION
    Queries host hardware metrics, VirtualBox version, registered virtual machines,
    and running virtual machines using VBoxManage.
#>
param(
    [string]$VBoxPath = "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe"
)

if (-not (Test-Path $VBoxPath)) {
    $cmd = Get-Command VBoxManage -ErrorAction SilentlyContinue
    if ($cmd) { $VBoxPath = $cmd.Source }
}

if (-not (Test-Path $VBoxPath)) {
    Write-Host "[ERROR] VBoxManage not found at '$VBoxPath'." -ForegroundColor Red
    exit 1
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Oracle VirtualBox Host Status Diagnostic" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$ver = & $VBoxPath --version
Write-Host "VirtualBox Version : $ver" -ForegroundColor Green
Write-Host "Host Computer Name : $env:COMPUTERNAME" -ForegroundColor DarkGray
Write-Host "Operating System   : $((Get-CimInstance Win32_OperatingSystem).Caption)" -ForegroundColor DarkGray

# Host info from VBoxManage
Write-Host "`n[+] VirtualBox Host Information:" -ForegroundColor Yellow
$hostInfo = & $VBoxPath list hostinfo
$hostInfo | Select-Object -First 12 | ForEach-Object { Write-Host "    $_" -ForegroundColor DarkGray }

# Registered VMs
Write-Host "`n[+] Registered Virtual Machines:" -ForegroundColor Yellow
$allVMs = & $VBoxPath list vms
if ($allVMs) {
    $allVMs | ForEach-Object { Write-Host "    $($_)" -ForegroundColor White }
} else {
    Write-Host "    (No VMs currently registered on this host)" -ForegroundColor DarkGray
}

# Running VMs
Write-Host "`n[+] Running Virtual Machines (Active Teleport Candidates):" -ForegroundColor Yellow
$runningVMs = & $VBoxPath list runningvms
if ($runningVMs) {
    $runningVMs | ForEach-Object { Write-Host "    $($_)" -ForegroundColor Green }
} else {
    Write-Host "    (No VMs are currently in 'running' state)" -ForegroundColor DarkGray
}

Write-Host "`nHost diagnostic check complete." -ForegroundColor Cyan
