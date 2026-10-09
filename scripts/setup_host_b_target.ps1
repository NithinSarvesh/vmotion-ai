# ==============================================================================
# VMotion AI - Host B (Target Laptop / Friend's Laptop) Setup & Agent Launcher
# Connects to Public Cloud Control Plane over Outbound WSS
# Real Cold / Offline VM Migration (Direct LAN SMB Copy & OVA Import)
# ==============================================================================

param(
    [string]$HostAIp = "",
    [string]$GatewayUrl = "wss://vmotion-ai-control-plane.onrender.com/ws/agent",
    [string]$GatewayToken = "",
    [string]$StagingDir = "C:\VMotionStaging",
    [int]$TeleportPort = 60050
)

$ErrorActionPreference = "Stop"
Write-Host ""
Write-Host "=================================================================" -ForegroundColor Magenta
Write-Host "   VMOTION AI - HOST B (TARGET LAPTOP) SETUP" -ForegroundColor Magenta
Write-Host "   Real Cold / Offline VM Migration (OVA Appliance Import)" -ForegroundColor Magenta
Write-Host "=================================================================" -ForegroundColor Magenta
Write-Host ""

# 1. Check Administrator Privileges (Fail-Closed)
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Error "Administrator privileges are required to configure Windows Firewall rules and networking on Host B. Please restart PowerShell as Administrator."
    exit 1
}
Write-Host "[OK] PowerShell session running with Administrator privileges." -ForegroundColor Green

# 2. Prompt for Host A LAN IP if not provided as argument
if (-not $HostAIp) {
    Write-Host "Please enter the LAN IP address of Host A (shown on Host A's screen):" -ForegroundColor Yellow
    $HostAIp = Read-Host "Host A LAN IP (e.g., 172.16.0.2 or 192.168.43.15)"
}

if (-not $HostAIp) {
    Write-Error "Host A IP is required to connect to the shared virtual disk."
    exit 1
}

# 3. Check VirtualBox Installation
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

# 4. Secure Cloud Gateway Token Resolution
$resolvedToken = ""
if ($GatewayToken -and $GatewayToken.Trim() -ne "") {
    $resolvedToken = $GatewayToken.Trim()
} elseif ($env:VMOTION_AGENT_SECRET -and $env:VMOTION_AGENT_SECRET.Trim() -ne "") {
    $resolvedToken = $env:VMOTION_AGENT_SECRET.Trim()
} elseif ($env:GATEWAY_AGENT_TOKEN -and $env:GATEWAY_AGENT_TOKEN.Trim() -ne "") {
    $resolvedToken = $env:GATEWAY_AGENT_TOKEN.Trim()
} else {
    try {
        Write-Host ""
        Write-Host "[AUTH] Cloud Gateway Token is required for Render authentication." -ForegroundColor Yellow
        $secPrompt = Read-Host -Prompt "Please enter GATEWAY_AGENT_TOKEN from Render Dashboard" -AsSecureString
        if ($secPrompt) {
            $bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secPrompt)
            $resolvedToken = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr).Trim()
            [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
        }
    } catch {
        $resolvedToken = ""
    }
}

if (-not $resolvedToken) {
    Write-Error "[AUTH ERROR] Missing Cloud Gateway Token! Please supply -GatewayToken <token> or set `$env:GATEWAY_AGENT_TOKEN / `$env:VMOTION_AGENT_SECRET."
    exit 1
}

# If targeting remote Render and token is the default dev secret, block with clear instruction
if ($GatewayUrl -like "*onrender.com*" -and $resolvedToken -eq "vmotion-vbox-secret") {
    Write-Error "[AUTH ERROR] Render generated a dynamic GATEWAY_AGENT_TOKEN for your deployment. The local default 'vmotion-vbox-secret' will be rejected with HTTP 403. Please copy the actual value from Render Dashboard -> Environment tab."
    exit 1
}

# Export environment variables for the agent process (do NOT print or persist the token)
$env:VMOTION_AGENT_SECRET = $resolvedToken
$env:GATEWAY_AGENT_TOKEN = $resolvedToken
$maskedToken = "*" * [Math]::Min(12, $resolvedToken.Length)
Write-Host "[OK] Cloud Gateway authentication token configured ($maskedToken, length: $($resolvedToken.Length))." -ForegroundColor Green

# 5. Test Network Reachability to Host A
Write-Host "[INFO] Testing connectivity to Host A at $HostAIp..." -ForegroundColor Yellow
$pingOk = Test-Connection -ComputerName $HostAIp -Count 2 -Quiet -ErrorAction SilentlyContinue
if ($pingOk) {
    Write-Host "[OK] Host A is reachable over LAN / phone hotspot." -ForegroundColor Green
} else {
    Write-Warning "ICMP ping to $HostAIp did not reply, but SMB/TCP may still be open."
}

# 6. Verify Staging Directory, Disk Space & Write Permissions
if (-not (Test-Path $StagingDir)) {
    Write-Host "[INFO] Creating target staging directory: $StagingDir" -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $StagingDir -Force | Out-Null
}
Write-Host "[OK] Target staging directory ready: $StagingDir" -ForegroundColor Green

# Verify Disk Space on Host B (minimum 5 GB required for OVA import)
$stagingDrive = (Get-Item $StagingDir).PSDrive
$freeGbB = [Math]::Round($stagingDrive.Free / 1GB, 2)
if ($freeGbB -lt 5.0) {
    Write-Error "[DISK SPACE ERROR] Insufficient free disk space on $($stagingDrive.Name): ($freeGbB GB free, minimum 5.0 GB required for staging and OVA import)."
    exit 1
}
Write-Host "[OK] Disk space on $($stagingDrive.Name):: $freeGbB GB free (>= 5.0 GB required)." -ForegroundColor Green

# Verify directory write permission
$testFileB = Join-Path $StagingDir ".vmotion_write_test"
try {
    [System.IO.File]::WriteAllText($testFileB, "vmotion_test")
    Remove-Item $testFileB -Force
    Write-Host "[OK] Write permission confirmed on $StagingDir." -ForegroundColor Green
} catch {
    Write-Error "[PERMISSION ERROR] Cannot write to directory $StagingDir: $_"
    exit 1
}

# 7. Verify Shared Storage Access (UNC SMB Path - Fail Closed)
$sharedPath = "\\$HostAIp\VMotionShared"
Write-Host "[INFO] Checking access to Host A shared directory at $sharedPath..." -ForegroundColor Yellow
if (Test-Path $sharedPath) {
    Write-Host "[OK] Source shared directory is accessible over LAN: $sharedPath" -ForegroundColor Green
} else {
    Write-Error "[SMB ACCESS ERROR] Could not access shared path $sharedPath! Ensure Host A is on the same network, File Sharing is enabled, and 'VMotionShared' share is active. Failing closed."
    exit 1
}

# 8. Firewall Configuration (Cold OVA Mode uses standard Windows SMB)
Write-Host "[OK] Cold OVA migration uses direct SMB transfer. Port 60050 receiver not required." -ForegroundColor Green

# 9. Auto-Discover Host B's LAN IP
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

# 10. Dynamic Appliance Import Notice
Write-Host "[INFO] Oracle VirtualBox on Host B is ready for automated OVA appliance import." -ForegroundColor Green
Write-Host "   Note: You do NOT need to manually pre-create the VM on Host B." -ForegroundColor Green
Write-Host "   The VMotion Agent will automatically import the OVA as 'VMotion-Migrated-<job-id>'." -ForegroundColor Green

# 11. Pre-Flight Validation Summary
Write-Host ""
Write-Host "=================================================================" -ForegroundColor Magenta
Write-Host "   HOST B (TARGET) PRE-FLIGHT VERIFICATION" -ForegroundColor Magenta
Write-Host "=================================================================" -ForegroundColor Magenta
Write-Host "   [OK] Administrator Privileges:  Elevated" -ForegroundColor Green
Write-Host "   [OK] VirtualBox Version:        $vboxVer" -ForegroundColor Green
Write-Host "   [OK] Target Staging Directory:  $StagingDir" -ForegroundColor Green
Write-Host "   [OK] Staging Disk Space:        $freeGbB GB (>= 5.0 GB required)" -ForegroundColor Green
Write-Host "   [OK] Write Permissions:         Confirmed" -ForegroundColor Green
Write-Host "   [OK] Source Host A Reachability: $HostAIp" -ForegroundColor Green
Write-Host "   [OK] Shared Storage SMB Path:   $sharedPath" -ForegroundColor Green
Write-Host "   [OK] Host B LAN / Hotspot IP:   $lanIp" -ForegroundColor Green
Write-Host "   [OK] Cloud Gateway Auth:        $maskedToken (length: $($resolvedToken.Length))" -ForegroundColor Green
Write-Host "   [OK] Cloud Gateway URL:         $GatewayUrl" -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Magenta
Write-Host ""

# 12. Set Agent Environment & Launch
$env:VMOTION_HOST_ID = "vbox-host-b"
$env:HOST_ID = "vbox-host-b"
$env:VMOTION_HOST_ROLE = "target"
$env:LAN_IP = $lanIp
$env:VMOTION_HOST_IP = $lanIp
$env:CLOUD_GATEWAY_URL = $GatewayUrl
$env:VMOTION_SHARED_STORAGE = $sharedPath
$env:VBOX_STAGING_PATH = $StagingDir
$env:VBOX_MANAGE_PATH = $vboxPath
$env:VBOX_MIGRATION_MODE = "cold_ova"
$env:VMOTION_TELEPORT_PORT = [string]$TeleportPort

Write-Host "Starting VMotion Agent for Host B..." -ForegroundColor Magenta
Write-Host "Connecting outbound to Cloud Gateway: $GatewayUrl" -ForegroundColor Magenta
Write-Host "Target agent is standing by to receive and import OVA appliance." -ForegroundColor Green
Write-Host ""

if (Test-Path ".venv\Scripts\python.exe") {
    & ".venv\Scripts\python.exe" "vmotion-agent\agent.py"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    python "vmotion-agent\agent.py"
} else {
    Write-Error "Python executable not found! Please run agent.py with Python 3.10+."
    exit 1
}
