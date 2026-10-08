# ==============================================================================
# VMotion AI - Host B (Target Laptop / Friend's Laptop) Setup & Agent Launcher
# Connects to Public Cloud Control Plane over Outbound WSS
# Listens for Teleportation P2P over Phone Hotspot / LAN on TCP Port 60050
# ==============================================================================

param(
    [string]$HostAIp = "",
    [string]$GatewayUrl = "wss://vmotion-ai-control-plane.onrender.com/ws/agent",
    [string]$TargetVmName = "VMotion - demo target",
    [int]$TeleportPort = 60050
)

$ErrorActionPreference = "Stop"
Write-Host ""
Write-Host "=================================================================" -ForegroundColor Magenta
Write-Host "   VMOTION AI - HOST B (TARGET LAPTOP) SETUP" -ForegroundColor Magenta
Write-Host "   P2P Direct LAN Teleportation Receiver Node" -ForegroundColor Magenta
Write-Host "=================================================================" -ForegroundColor Magenta
Write-Host ""

# 1. Prompt for Host A LAN IP if not provided as argument
if (-not $HostAIp) {
    Write-Host "Please enter the LAN IP address of Host A (shown on Host A's screen):" -ForegroundColor Yellow
    $HostAIp = Read-Host "Host A LAN IP (e.g., 172.16.0.2 or 192.168.43.15)"
}

if (-not $HostAIp) {
    Write-Error "Host A IP is required to connect to the shared virtual disk."
    exit 1
}

# 2. Check VirtualBox Installation
$vboxPaths = @(
    "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe",
    (Get-Command VBoxManage.exe -ErrorAction SilentlyContinue).Source
) | Where-Object { $_ -and (Test-Path $_) }

if ($vboxPaths.Count -eq 0) {
    Write-Error "VirtualBox (VBoxManage.exe) not found! Please install Oracle VirtualBox on Host B."
    exit 1
}
$vboxPath = $vboxPaths[0]
$vboxVer = & $vboxPath --version
Write-Host "[OK] VirtualBox detected: $vboxVer ($vboxPath)" -ForegroundColor Green

# 3. Test Network Reachability to Host A
Write-Host "[INFO] Testing connectivity to Host A at $HostAIp..." -ForegroundColor Yellow
$pingOk = Test-Connection -ComputerName $HostAIp -Count 2 -Quiet -ErrorAction SilentlyContinue
if ($pingOk) {
    Write-Host "[OK] Host A is reachable over LAN / phone hotspot." -ForegroundColor Green
} else {
    Write-Warning "ICMP ping to $HostAIp did not reply, but SMB/TCP may still be open."
}

# 4. Verify Shared Storage Access (UNC SMB Path)
$sharedPath = "\\$HostAIp\VMotionShared"
Write-Host "[INFO] Checking access to shared disk at $sharedPath..." -ForegroundColor Yellow
if (Test-Path $sharedPath) {
    Write-Host "[OK] Shared disk directory is accessible: $sharedPath" -ForegroundColor Green
    $vdiFiles = Get-ChildItem -Path $sharedPath -Filter "*.vdi" -ErrorAction SilentlyContinue
    if ($vdiFiles.Count -gt 0) {
        Write-Host "[OK] Found shared virtual disk: $($vdiFiles[0].Name)" -ForegroundColor Green
    }
} else {
    Write-Warning "Could not access $sharedPath directly. Make sure both laptops are connected to the SAME phone hotspot and network discovery / file sharing is enabled."
}

# 5. Open Windows Firewall Port 60050 for Receiving Teleportation Stream
$ruleName = "VMotion AI Teleportation Receiver (Port $TeleportPort)"
$existingRule = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
if (-not $existingRule) {
    try {
        Write-Host "[INFO] Adding Inbound Firewall rule for TCP port $TeleportPort..." -ForegroundColor Yellow
        New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -LocalPort $TeleportPort -Protocol TCP -Action Allow | Out-Null
        Write-Host "[OK] Firewall port $TeleportPort opened for receiving teleportation stream." -ForegroundColor Green
    } catch {
        Write-Warning "Could not add firewall rule automatically. Run PowerShell as Administrator."
    }
} else {
    Write-Host "[OK] Firewall rule '$ruleName' is already enabled." -ForegroundColor Green
}

# 6. Auto-Discover Host B's LAN IP
$lanIp = $null
try {
    $udpSock = New-Object System.Net.Sockets.UdpClient
    $udpSock.Connect("8.8.8.8", 80)
    $lanIp = $udpSock.Client.LocalEndPoint.Address.ToString()
    $udpSock.Close()
} catch {
    $lanIp = (Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias "*Wi-Fi*", "*Ethernet*" | Where-Object { $_.IPAddress -notlike "169.254*" -and $_.IPAddress -notlike "127*" } | Select-Object -First 1).IPAddress
}

if (-not $lanIp) {
    $lanIp = "127.0.0.1"
}

Write-Host ""
Write-Host "-----------------------------------------------------------------" -ForegroundColor Magenta
Write-Host "   HOST B (TARGET) NETWORK CONFIGURATION" -ForegroundColor Magenta
Write-Host "   Host B LAN / Hotspot IPv4:  $lanIp" -ForegroundColor Green
Write-Host "   Host A Source IP:           $HostAIp" -ForegroundColor Green
Write-Host "   Teleport Listener Port:     $TeleportPort (TCP)" -ForegroundColor Green
Write-Host "   Target VM Name:             $TargetVmName" -ForegroundColor Green
Write-Host "-----------------------------------------------------------------" -ForegroundColor Magenta
Write-Host ""

# 7. Check Registered VMs on Host B
$vms = & $vboxPath list vms
$vmFound = $false
foreach ($line in $vms) {
    if ($line -like "*$TargetVmName*" -or $line -like "*VMotion*") {
        $vmFound = $true
        Write-Host "[OK] Target VM found: $line" -ForegroundColor Green
    }
}

if (-not $vmFound) {
    Write-Host "[NOTICE] Target VM '$TargetVmName' not yet in list." -ForegroundColor Yellow
    Write-Host "   If you need to create it, ensure its CPU (2), RAM (4096MB), Chipset (PIIX3), and BIOS match Host A,"
    Write-Host "   and its SATA controller attaches to: \\$HostAIp\VMotionShared\VMotion-Demo.vdi"
}

# 8. Set Agent Environment & Launch
$env:VMOTION_HOST_ID = "vbox-host-b"
$env:HOST_ID = "vbox-host-b"
$env:VMOTION_HOST_ROLE = "target"
$env:LAN_IP = $lanIp
$env:VMOTION_HOST_IP = $lanIp
$env:CLOUD_GATEWAY_URL = $GatewayUrl
$env:VMOTION_SHARED_STORAGE = $sharedPath
$env:VBOX_MANAGE_PATH = $vboxPath
$env:VMOTION_TELEPORT_PORT = [string]$TeleportPort

Write-Host ""
Write-Host "Starting VMotion Agent for Host B..." -ForegroundColor Magenta
Write-Host "Connecting outbound to Cloud Gateway: $GatewayUrl" -ForegroundColor Magenta
Write-Host "Target agent will stand by in headless listener mode automatically." -ForegroundColor Green
Write-Host ""

if (Test-Path ".venv\Scripts\python.exe") {
    & ".venv\Scripts\python.exe" "vmotion-agent\agent.py"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    python "vmotion-agent\agent.py"
} else {
    Write-Error "Python executable not found! Please run agent.py with Python 3.10+."
}
