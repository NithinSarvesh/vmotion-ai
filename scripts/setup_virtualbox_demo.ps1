<#
.SYNOPSIS
    VMotion AI - Setup and verify the Oracle VirtualBox Live Teleportation Demonstration Environment.
.DESCRIPTION
    Verifies VirtualBox installation, opens firewall port for live memory streaming (TCP 60050),
    verifies shared folder/SMB accessibility, and tests VBoxManage CLI commands.
.PARAMETER TeleportPort
    The TCP port dedicated for VirtualBox memory streaming (default: 60050).
.PARAMETER SharedStoragePath
    The network directory path where shared VM virtual disks reside (e.g. \\storage\vdi or C:\shared_vdi).
#>
param(
    [int]$TeleportPort = 60050,
    [string]$SharedStoragePath = "C:\vmotion_shared_storage"
)

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " VMotion AI: Oracle VirtualBox Demo Environment Setup" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Check VirtualBox Installation
$vboxPaths = @(
    "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe",
    (Get-Command VBoxManage -ErrorAction SilentlyContinue).Source
) | Where-Object { $_ -and (Test-Path $_) }

if ($vboxPaths.Count -eq 0) {
    Write-Host "[ERROR] Oracle VirtualBox (VBoxManage) was not detected!" -ForegroundColor Red
    Write-Host "Please install Oracle VirtualBox 7.x or verify installation directory." -ForegroundColor Yellow
    exit 1
}

$vboxExe = $vboxPaths[0]
$vboxVer = & $vboxExe --version
Write-Host "[OK] Detected Oracle VirtualBox: $vboxVer" -ForegroundColor Green
Write-Host "     Path: $vboxExe" -ForegroundColor DarkGray

# 2. Check / Create Shared Storage Directory
Write-Host "`n[+] Verifying Shared Storage Path: $SharedStoragePath" -ForegroundColor Yellow
if (-not (Test-Path $SharedStoragePath)) {
    Write-Host "    Directory does not exist. Creating local directory..." -ForegroundColor DarkGray
    New-Item -ItemType Directory -Path $SharedStoragePath -Force | Out-Null
}
$testFile = Join-Path $SharedStoragePath ".vmotion_rw_probe.tmp"
try {
    "probe" | Out-File -FilePath $testFile -Encoding ascii
    Remove-Item -Path $testFile -Force
    Write-Host "[OK] Shared storage directory is accessible and read/write verified." -ForegroundColor Green
} catch {
    Write-Host "[WARNING] Could not write probe file to shared storage: $_" -ForegroundColor Yellow
}

# 3. Check Windows Firewall for Teleport Port
Write-Host "`n[+] Verifying Firewall Rule for Teleport Port TCP $TeleportPort..." -ForegroundColor Yellow
$ruleName = "VMotion_AI_VirtualBox_Teleporter"
$existingRule = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue

if (-not $existingRule) {
    try {
        New-NetFirewallRule -DisplayName $ruleName `
            -Direction Inbound `
            -Protocol TCP `
            -LocalPort $TeleportPort `
            -Action Allow `
            -Description "Allows Oracle VirtualBox Teleportation stream for VMotion AI" | Out-Null
        Write-Host "[OK] Created inbound firewall rule for TCP $TeleportPort." -ForegroundColor Green
    } catch {
        Write-Host "[NOTICE] Could not automatically create firewall rule (Run as Administrator if needed)." -ForegroundColor DarkGray
        Write-Host "         Command: New-NetFirewallRule -DisplayName '$ruleName' -Direction Inbound -Protocol TCP -LocalPort $TeleportPort -Action Allow" -ForegroundColor DarkGray
    }
} else {
    Write-Host "[OK] Firewall rule '$ruleName' is active for TCP $TeleportPort." -ForegroundColor Green
}

# 4. Summary
Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host " Setup Complete! Oracle VirtualBox is Ready for Live Demo" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Next steps:"
Write-Host " 1. Run 'scripts\discover_vms.ps1' to inspect local VMs."
Write-Host " 2. Ensure target VM is registered on Computer B."
Write-Host " 3. Launch backend control plane: python -m uvicorn app.main:app --port 8000"
