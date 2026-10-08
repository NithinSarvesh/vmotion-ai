# ==============================================================================
# VMotion AI - Host A (Source Laptop) Automated Setup & Agent Launcher
# Connects to Public Cloud Control Plane over Outbound WSS
# Streams Teleportation P2P over Phone Hotspot / LAN on TCP Port 60050
# ==============================================================================

param(
    [string]$GatewayUrl = "wss://vmotion-ai-control-plane.onrender.com/ws/agent",
    [string]$SharedDir = "C:\VMotionShared",
    [string]$VmName = "VMotion-Demo",
    [int]$TeleportPort = 60050
)

$ErrorActionPreference = "Stop"
Write-Host ""
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "   VMOTION AI - HOST A (SOURCE LAPTOP) SETUP" -ForegroundColor Cyan
Write-Host "   P2P Direct LAN Teleportation Data Plane" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check Administrator Privileges
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Warning "Please run PowerShell as Administrator to configure Firewall and SMB shares."
}

# 2. Check VirtualBox Installation
$vboxPaths = @(
    "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe",
    (Get-Command VBoxManage.exe -ErrorAction SilentlyContinue).Source
) | Where-Object { $_ -and (Test-Path $_) }

if ($vboxPaths.Count -eq 0) {
    Write-Error "VirtualBox (VBoxManage.exe) not found! Please install Oracle VirtualBox."
    exit 1
}
$vboxPath = $vboxPaths[0]
$vboxVer = & $vboxPath --version
Write-Host "[OK] VirtualBox detected: $vboxVer ($vboxPath)" -ForegroundColor Green

# 3. Create & Verify Shared Storage Directory
if (-not (Test-Path $SharedDir)) {
    Write-Host "[INFO] Creating shared directory: $SharedDir" -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $SharedDir -Force | Out-Null
}
Write-Host "[OK] Shared directory ready: $SharedDir" -ForegroundColor Green

# 4. Configure Windows SMB Share (for Target Laptop to access VDI)
$shareName = (Split-Path $SharedDir -Leaf)
$existingShare = Get-SmbShare -Name $shareName -ErrorAction SilentlyContinue
if (-not $existingShare) {
    try {
        Write-Host "[INFO] Creating Windows SMB Share '$shareName' on $SharedDir..." -ForegroundColor Yellow
        New-SmbShare -Name $shareName -Path $SharedDir -FullAccess "Everyone" -ErrorAction Stop | Out-Null
        Write-Host "[OK] SMB Share '$shareName' created successfully." -ForegroundColor Green
    } catch {
        Write-Warning "Could not create SMB share via PowerShell. Attempting 'net share' fallback..."
        net share "$shareName=$SharedDir" /grant:everyone,full
    }
} else {
    Write-Host "[OK] SMB Share '$shareName' already active." -ForegroundColor Green
}

# 5. Open Windows Firewall Port 60050 for Direct LAN Teleportation
$ruleName = "VMotion AI Teleportation Stream (Port $TeleportPort)"
$existingRule = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
if (-not $existingRule) {
    try {
        Write-Host "[INFO] Adding Inbound Firewall rule for TCP port $TeleportPort..." -ForegroundColor Yellow
        New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -LocalPort $TeleportPort -Protocol TCP -Action Allow | Out-Null
        Write-Host "[OK] Firewall port $TeleportPort opened for P2P live migration." -ForegroundColor Green
    } catch {
        Write-Warning "Could not add firewall rule automatically. Run: netsh advfirewall firewall add rule name=`"$ruleName`" dir=in action=allow protocol=TCP localport=$TeleportPort"
    }
} else {
    Write-Host "[OK] Firewall rule '$ruleName' is already enabled." -ForegroundColor Green
}

# 6. Auto-Discover Active LAN / Hotspot IP Address
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
Write-Host "-----------------------------------------------------------------" -ForegroundColor Cyan
Write-Host "   HOST A (SOURCE) NETWORK CONFIGURATION" -ForegroundColor Cyan
Write-Host "   Active LAN / Hotspot IPv4:  $lanIp" -ForegroundColor Green
Write-Host "   Shared Storage UNC Path:    \\$lanIp\$shareName" -ForegroundColor Green
Write-Host "   Teleport Listener Port:     $TeleportPort (TCP)" -ForegroundColor Green
Write-Host "-----------------------------------------------------------------" -ForegroundColor Cyan
Write-Host ""
Write-Host ">> Give this info to Host B (Friend's Laptop):" -ForegroundColor Yellow
Write-Host "   Host A LAN IP:  $lanIp" -ForegroundColor Yellow
Write-Host "   SMB Disk Share: \\$lanIp\$shareName\VMotion-Demo.vdi" -ForegroundColor Yellow
Write-Host ""

# 7. Check Registered VMs
$vms = & $vboxPath list vms
Write-Host "[INFO] VirtualBox VMs registered on Host A:"
$vms | ForEach-Object { Write-Host "   - $_" }
Write-Host ""

# 8. Set Agent Environment & Launch
$env:VMOTION_HOST_ID = "vbox-host-a"
$env:HOST_ID = "vbox-host-a"
$env:VMOTION_HOST_ROLE = "source"
$env:LAN_IP = $lanIp
$env:VMOTION_HOST_IP = $lanIp
$env:CLOUD_GATEWAY_URL = $GatewayUrl
$env:VMOTION_SHARED_STORAGE = $SharedDir
$env:VBOX_MANAGE_PATH = $vboxPath
$env:VMOTION_TELEPORT_PORT = [string]$TeleportPort

Write-Host "Starting VMotion Agent for Host A..." -ForegroundColor Cyan
Write-Host "Connecting outbound to Cloud Gateway: $GatewayUrl" -ForegroundColor Cyan
Write-Host ""

if (Test-Path ".venv\Scripts\python.exe") {
    & ".venv\Scripts\python.exe" "vmotion-agent\agent.py"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    python "vmotion-agent\agent.py"
} else {
    Write-Error "Python executable not found! Please run agent.py with Python 3.10+."
}
