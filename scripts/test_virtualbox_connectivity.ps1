<#
.SYNOPSIS
    VMotion AI - Pre-Flight Network Connectivity and Teleport Port Verification.
.DESCRIPTION
    Tests network latency, ICMP reachability, and TCP port connectivity (default: 60050)
    between Source Host A and Target Host B over the local area network.
.PARAMETER TargetIP
    The IPv4 address or hostname of the target VirtualBox computer (Host B).
.PARAMETER TeleportPort
    The TCP port to verify for teleportation streaming (default: 60050).
.PARAMETER AgentPort
    The TCP port for the vmotion-agent HTTP service (default: 8001).
#>
param(
    [Parameter(Mandatory=$false)]
    [string]$TargetIP = "127.0.0.1",
    [int]$TeleportPort = 60050,
    [int]$AgentPort = 8001
)

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " VMotion AI: Dual-Host Network Connectivity Test" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Target Host : $TargetIP" -ForegroundColor Yellow

# 1. ICMP Ping Test
Write-Host "`n[1/3] Testing ICMP Ping Reachability..." -ForegroundColor Yellow
$ping = Test-Connection -ComputerName $TargetIP -Count 2 -Quiet -ErrorAction SilentlyContinue
if ($ping) {
    Write-Host "[OK] Target host '$TargetIP' responded to ICMP echo." -ForegroundColor Green
} else {
    Write-Host "[WARNING] Target host did not respond to ICMP (Firewall may block ping; continuing TCP probes)." -ForegroundColor Yellow
}

# 2. Teleporter Port Test (TCP 60050)
Write-Host "`n[2/3] Probing VirtualBox Teleport Port (TCP $TeleportPort)..." -ForegroundColor Yellow
$teleportSocket = Test-NetConnection -ComputerName $TargetIP -Port $TeleportPort -WarningAction SilentlyContinue
if ($teleportSocket.TcpTestSucceeded) {
    Write-Host "[OK] TCP Port $TeleportPort is OPEN and accepting connections!" -ForegroundColor Green
} else {
    Write-Host "[NOTICE] TCP Port $TeleportPort is currently closed." -ForegroundColor DarkGray
    Write-Host "         Run 'scripts\prepare_teleport_target.ps1' on Host B to arm the listener." -ForegroundColor DarkGray
}

# 3. Host Agent Port Test (TCP 8001)
Write-Host "`n[3/3] Probing VMotion Agent Port (TCP $AgentPort)..." -ForegroundColor Yellow
$agentSocket = Test-NetConnection -ComputerName $TargetIP -Port $AgentPort -WarningAction SilentlyContinue
if ($agentSocket.TcpTestSucceeded) {
    Write-Host "[OK] VMotion Host Agent is active on port $AgentPort." -ForegroundColor Green
} else {
    Write-Host "[NOTICE] VMotion Host Agent not detected on port $AgentPort." -ForegroundColor DarkGray
    Write-Host "         Start agent on Host B: python vmotion-agent\agent.py" -ForegroundColor DarkGray
}

Write-Host "`nConnectivity test complete." -ForegroundColor Cyan
