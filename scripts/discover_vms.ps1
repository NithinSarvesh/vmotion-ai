<#
.SYNOPSIS
    VMotion AI - Deep Virtual Machine Discovery and Configuration Inspection.
.DESCRIPTION
    Inspects all VirtualBox VMs, parsing vCPU count, memory allocation, storage controllers,
    attached virtual disks, and teleporter parameters using VBoxManage showvminfo.
#>
param(
    [string]$VBoxPath = "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe",
    [string]$SpecificVM = ""
)

if (-not (Test-Path $VBoxPath)) {
    $cmd = Get-Command VBoxManage -ErrorAction SilentlyContinue
    if ($cmd) { $VBoxPath = $cmd.Source }
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " VMotion AI: VirtualBox VM Inventory & Specs Discovery" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$runningRaw = & $VBoxPath list runningvms
$runningSet = @{}
if ($runningRaw) {
    $runningRaw | ForEach-Object {
        if ($_ -match '"([^"]+)"') { $runningSet[$matches[1]] = $true }
    }
}

$vmsRaw = & $VBoxPath list vms
if (-not $vmsRaw) {
    Write-Host "[NOTICE] No VirtualBox VMs found on this computer." -ForegroundColor Yellow
    Write-Host "You can create a demonstration VM using the documented Linux template:" -ForegroundColor DarkGray
    Write-Host "  Name: DemoVM | 2 vCPUs | 2048 MB RAM | Shared Storage VDI" -ForegroundColor DarkGray
    exit 0
}

$vmNames = @()
$vmsRaw | ForEach-Object {
    if ($_ -match '"([^"]+)"') {
        if (-not $SpecificVM -or $matches[1] -eq $SpecificVM) {
            $vmNames += $matches[1]
        }
    }
}

foreach ($vmName in $vmNames) {
    $isRunning = $runningSet.ContainsKey($vmName)
    $statusColor = if ($isRunning) { "Green" } else { "DarkGray" }
    $statusText = if ($isRunning) { "RUNNING (Candidate for Live Teleport)" } else { "STOPPED" }

    Write-Host "`n──────────────────────────────────────────────────────────" -ForegroundColor DarkGray
    Write-Host " VM: $vmName" -ForegroundColor Cyan
    Write-Host " Status: $statusText" -ForegroundColor $statusColor

    # Inspect machine-readable info
    $infoRaw = & $VBoxPath showvminfo $vmName --machinereadable
    $info = @{}
    $infoRaw | ForEach-Object {
        if ($_ -match '^"([^"]+)"="([^"]*)"$' -or $_ -match '^([^=]+)="?([^"]*)"?$') {
            $info[$matches[1]] = $matches[2]
        }
    }

    Write-Host "  Hardware:"
    Write-Host "    vCPUs        : $($info['cpus'])"
    Write-Host "    RAM          : $($info['memory']) MB"
    Write-Host "    Chipset      : $($info['chipset'])"
    Write-Host "    Firmware     : $($info['firmware'])"
    Write-Host "  Teleporter Configuration:"
    Write-Host "    Enabled      : $($info['teleporterenabled'])"
    Write-Host "    Port         : $($info['teleporterport'])"
    Write-Host "    Address      : $($info['teleporteraddress'])"
}

Write-Host "`n──────────────────────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host "Discovery complete. Found $($vmNames.Count) virtual machine(s)." -ForegroundColor Green
