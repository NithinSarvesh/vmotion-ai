<#
.SYNOPSIS
    VMotion AI - Arm Target VirtualBox Host for Incoming Teleportation.
.DESCRIPTION
    Configures the target virtual machine on Computer B to listen for the incoming
    teleportation memory stream, then boots the VM in headless mode into the
    teleport-waiting state.
.PARAMETER VMName
    The target virtual machine name (must match source VM hardware specs).
.PARAMETER Port
    The dedicated TCP port for teleporter listening (default: 60050).
#>
param(
    [Parameter(Mandatory=$false)]
    [string]$VMName = "DemoVM",
    [int]$Port = 60050,
    [string]$VBoxPath = "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe"
)

if (-not (Test-Path $VBoxPath)) {
    $cmd = Get-Command VBoxManage -ErrorAction SilentlyContinue
    if ($cmd) { $VBoxPath = $cmd.Source }
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " VMotion AI: Prepare Target VirtualBox Teleporter" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Target VM : $VMName" -ForegroundColor Yellow
Write-Host "TCP Port  : $Port" -ForegroundColor Yellow

# Step 1: Configure teleporter listener
Write-Host "`n[1/2] Configuring teleporter service on '$VMName'..." -ForegroundColor Yellow
& $VBoxPath modifyvm $VMName --teleporter on --teleporter-port $Port --teleporter-address "0.0.0.0"

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to configure teleporter on target VM '$VMName'." -ForegroundColor Red
    exit $LASTEXITCODE
}
Write-Host "[OK] Teleporter enabled on port $Port." -ForegroundColor Green

# Step 2: Start VM in headless mode (Enters teleport-waiting state)
Write-Host "`n[2/2] Launching target VM into headless teleport-waiting state..." -ForegroundColor Yellow
& $VBoxPath startvm $VMName --type headless

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Target VM '$VMName' is armed and listening on port $Port!" -ForegroundColor Green
    Write-Host "     The VM is paused and ready to receive the live memory stream from Host A." -ForegroundColor Cyan
} else {
    # Check if VM is already in waiting state
    $info = & $VBoxPath showvminfo $VMName --machinereadable
    if ($info -match 'VMState="teleporting"' -or $info -match 'VMState="paused"') {
        Write-Host "[OK] Target VM is already in teleport-waiting state." -ForegroundColor Green
    } else {
        Write-Host "[WARNING] Target startvm reported exit code $LASTEXITCODE. Verify VM state." -ForegroundColor Yellow
    }
}

Write-Host "`nReady for teleportation dispatch from source computer." -ForegroundColor Cyan
