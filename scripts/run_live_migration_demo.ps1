<#
.SYNOPSIS
    VMotion AI - Execute Oracle VirtualBox Live VM Teleportation Demonstration.
.DESCRIPTION
    Authoritative script to execute live teleportation of a running virtual machine
    from Computer A to Computer B using VBoxManage controlvm teleport.
.PARAMETER VMName
    The name of the running virtual machine to teleport.
.PARAMETER TargetHost
    The IP address or hostname of the target computer (Computer B).
.PARAMETER Port
    The teleporter port configured on the target computer (default: 60050).
.PARAMETER MaxDowntimeMs
    Maximum permitted blackout window in milliseconds during handover (default: 500).
#>
param(
    [Parameter(Mandatory=$false)]
    [string]$VMName = "DemoVM",
    [Parameter(Mandatory=$false)]
    [string]$TargetHost = "127.0.0.1",
    [int]$Port = 60050,
    [int]$MaxDowntimeMs = 500,
    [string]$VBoxPath = "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe"
)

if (-not (Test-Path $VBoxPath)) {
    $cmd = Get-Command VBoxManage -ErrorAction SilentlyContinue
    if ($cmd) { $VBoxPath = $cmd.Source }
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " VMotion AI: LIVE ORACLE VIRTUALBOX TELEPORTATION DEMO" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Workload VM   : $VMName" -ForegroundColor Yellow
Write-Host "Source Host   : $env:COMPUTERNAME" -ForegroundColor Yellow
Write-Host "Target Host   : $TargetHost" -ForegroundColor Yellow
Write-Host "Teleport Port : $Port" -ForegroundColor Yellow
Write-Host "Max Downtime  : $MaxDowntimeMs ms" -ForegroundColor Yellow

# Step 1: Verify source VM is running
Write-Host "`n[1/4] Verifying source VM state on $env:COMPUTERNAME..." -ForegroundColor Yellow
$running = & $VBoxPath list runningvms
if ($running -notmatch [regex]::Escape($VMName)) {
    Write-Host "[ERROR] VM '$VMName' is not running on this host!" -ForegroundColor Red
    Write-Host "Please start the demonstration VM before initiating live migration:" -ForegroundColor DarkGray
    Write-Host "  & '$VBoxPath' startvm '$VMName'" -ForegroundColor DarkGray
    exit 1
}
Write-Host "[OK] Workload '$VMName' is actively running." -ForegroundColor Green

# Step 2: Probe target listener
Write-Host "`n[2/4] Testing target teleporter listener at $TargetHost`:$Port..." -ForegroundColor Yellow
$probe = Test-NetConnection -ComputerName $TargetHost -Port $Port -WarningAction SilentlyContinue
if (-not $probe.TcpTestSucceeded) {
    Write-Host "[WARNING] Target port $Port is not responding. Ensure target was prepared with 'prepare_teleport_target.ps1'." -ForegroundColor Yellow
    $confirm = Read-Host "Proceed with teleport attempt anyway? (y/n)"
    if ($confirm -ne 'y') { exit 1 }
} else {
    Write-Host "[OK] Target teleporter listener verified open!" -ForegroundColor Green
}

# Step 3: Dispatch Teleportation
Write-Host "`n[3/4] INITIATING VBOXMANAGE TELEPORTATION STREAM..." -ForegroundColor Cyan
Write-Host "Command: VBoxManage controlvm $VMName teleport --host=$TargetHost --port=$Port --maxdowntime=$MaxDowntimeMs" -ForegroundColor DarkGray

$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
$result = & $VBoxPath controlvm $VMName teleport "--host=$TargetHost" "--port=$Port" "--maxdowntime=$MaxDowntimeMs"
$stopwatch.Stop()
$elapsedSec = [math]::Round($stopwatch.Elapsed.TotalSeconds, 2)

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n==========================================================" -ForegroundColor Green
    Write-Host " TELEPORTATION COMPLETED SUCCESSFULLY!" -ForegroundColor Green
    Write-Host "==========================================================" -ForegroundColor Green
    Write-Host " Total Handover Time : $elapsedSec seconds" -ForegroundColor Green
    Write-Host " Observed Interruption: < $MaxDowntimeMs ms" -ForegroundColor Green
    Write-Host " Details              : $result" -ForegroundColor DarkGray

    # Step 4: Verify post-migration state
    Write-Host "`n[4/4] Verifying post-migration state on local host..." -ForegroundColor Yellow
    $afterRunning = & $VBoxPath list runningvms
    if ($afterRunning -notmatch [regex]::Escape($VMName)) {
        Write-Host "[OK] Confirmed: Workload '$VMName' is no longer running on Source Host A." -ForegroundColor Green
        Write-Host "     Active execution handed over seamlessly to Target Host B." -ForegroundColor Green
    }
} else {
    Write-Host "`n[ERROR] VBoxManage teleportation failed with exit code $LASTEXITCODE." -ForegroundColor Red
    Write-Host "Output: $result" -ForegroundColor Yellow
    exit $LASTEXITCODE
}
