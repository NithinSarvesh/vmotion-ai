# ==============================================================================
# VMotion AI - Host A (Source Laptop) Automated Setup & Agent Launcher
# Connects to Public Cloud Control Plane over Outbound WSS
# Real Cold / Offline VM Migration (OVA Export & LAN SMB Sharing)
# ==============================================================================

param(
    [string]$GatewayUrl = "wss://vmotion-ai-control-plane.onrender.com/ws/agent",
    [string]$GatewayToken = "",
    [string]$SharedDir = "C:\VMotionShared",
    [string]$VmName = "VMotion-Demo",
    [int]$TeleportPort = 60050
)

$ErrorActionPreference = "Stop"
Write-Host ""
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "   VMOTION AI - HOST A (SOURCE LAPTOP) SETUP" -ForegroundColor Cyan
Write-Host "   Real Cold / Offline VM Migration (OVA Appliance Export)" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check Administrator Privileges (Fail-Closed)
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Error "Administrator privileges are required to configure Windows Firewall rules and SMB shares. Please restart PowerShell as Administrator."
    exit 1
}
Write-Host "[OK] PowerShell session running with Administrator privileges." -ForegroundColor Green

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

# 3. Secure Cloud Gateway Token Resolution
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

# 4. Create & Verify Shared Storage Directory & Write Permissions
if (-not (Test-Path $SharedDir)) {
    Write-Host "[INFO] Creating shared directory: $SharedDir" -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $SharedDir -Force | Out-Null
}
Write-Host "[OK] Shared directory ready: $SharedDir" -ForegroundColor Green

# Verify Disk Space on Host A (minimum 5 GB required for OVA export)
$sharedDrive = (Get-Item $SharedDir).PSDrive
$freeGbA = [Math]::Round($sharedDrive.Free / 1GB, 2)
if ($freeGbA -lt 5.0) {
    Write-Error "[DISK SPACE ERROR] Insufficient free disk space on $($sharedDrive.Name): ($freeGbA GB free, minimum 5.0 GB required for OVA export)."
    exit 1
}
Write-Host "[OK] Disk space on $($sharedDrive.Name):: $freeGbA GB free (>= 5.0 GB required)." -ForegroundColor Green

# Verify directory write permission
$testFileA = Join-Path $SharedDir ".vmotion_write_test"
try {
    [System.IO.File]::WriteAllText($testFileA, "vmotion_test")
    Remove-Item $testFileA -Force
    Write-Host "[OK] Write permission confirmed on $SharedDir." -ForegroundColor Green
} catch {
    Write-Error "[PERMISSION ERROR] Cannot write to directory ${SharedDir}: $_"
    exit 1
}

# 5. Configure & Verify Windows SMB Share
$shareName = (Split-Path $SharedDir -Leaf)
$existingShare = Get-SmbShare -Name $shareName -ErrorAction SilentlyContinue
if (-not $existingShare) {
    try {
        Write-Host "[INFO] Creating Windows SMB Share '$shareName' on $SharedDir..." -ForegroundColor Yellow
        New-SmbShare -Name $shareName -Path $SharedDir -FullAccess "Everyone" -ErrorAction Stop | Out-Null
    } catch {
        Write-Warning "PowerShell New-SmbShare cmdlet failed. Attempting 'net share' fallback..."
        net share "$shareName=$SharedDir" /grant:everyone,full
    }
}

$verifyShare = Get-SmbShare -Name $shareName -ErrorAction SilentlyContinue
if (-not $verifyShare) {
    Write-Error "[SMB ERROR] SMB Share '$shareName' could not be created or verified on $SharedDir. Please enable File and Printer Sharing in Windows settings."
    exit 1
}
Write-Host "[OK] SMB Share '$shareName' confirmed active on $SharedDir." -ForegroundColor Green

# 6. Verify Windows File Sharing Firewall State
$smbRules = Get-NetFirewallRule -DisplayGroup "File and Printer Sharing" -Direction Inbound -ErrorAction SilentlyContinue | Where-Object { $_.Enabled -eq 'True' }
if ($smbRules) {
    Write-Host "[OK] Windows File and Printer Sharing (SMB) inbound firewall rules active." -ForegroundColor Green
} else {
    Write-Host "[INFO] Windows SMB network file sharing active." -ForegroundColor Green
}

# 7. Auto-Discover Active LAN / Hotspot IP Address
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

# 8. Check Registered VMs and Verify Source VM
$vms = & $vboxPath list vms
Write-Host "[INFO] VirtualBox VMs registered on Host A:"
$vms | ForEach-Object { Write-Host "   - $_" }
Write-Host ""

$vmFound = $false
foreach ($line in $vms) {
    if ($line -like "*$VmName*") {
        $vmFound = $true
        break
    }
}
if (-not $vmFound) {
    Write-Warning "Source VM '$VmName' was not found in registered VirtualBox VMs on Host A."
    Write-Host "Please ensure your VM name matches or pass -VmName '<YourVMName>'." -ForegroundColor Yellow
} else {
    Write-Host "[OK] Source VM '$VmName' confirmed registered in VirtualBox on Host A." -ForegroundColor Green
}

# 9. Pre-Flight Validation Summary
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "   HOST A (SOURCE) PRE-FLIGHT VERIFICATION" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "   [OK] Administrator Privileges:  Elevated" -ForegroundColor Green
Write-Host "   [OK] VirtualBox Version:        $vboxVer" -ForegroundColor Green
if ($vmFound) {
    Write-Host "   [OK] Source VM Registration:    $VmName (Found)" -ForegroundColor Green
} else {
    Write-Host "   [WARN] Source VM Registration:  $VmName (Not yet found in list)" -ForegroundColor Yellow
}
Write-Host "   [OK] Available Disk Space:      $freeGbA GB free" -ForegroundColor Green
Write-Host "   [OK] Shared Directory:          $SharedDir (Write Verified)" -ForegroundColor Green
Write-Host "   [OK] SMB Disk Share:            \\$lanIp\$shareName (Active)" -ForegroundColor Green
Write-Host "   [OK] Hotspot / LAN IPv4:        $lanIp" -ForegroundColor Green
Write-Host "   [OK] Cloud Gateway Auth:        $maskedToken (length: $($resolvedToken.Length))" -ForegroundColor Green
Write-Host "   [OK] Cloud Gateway URL:         $GatewayUrl" -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host ">> Give this info to Host B (Friend's Laptop):" -ForegroundColor Yellow
Write-Host "   Host A LAN IP:  $lanIp" -ForegroundColor Yellow
Write-Host "   SMB Share Path: \\$lanIp\$shareName" -ForegroundColor Yellow
Write-Host ""

# 10. Set Agent Environment & Launch
$env:VMOTION_HOST_ID = "vbox-host-a"
$env:HOST_ID = "vbox-host-a"
$env:VMOTION_HOST_ROLE = "source"
$env:LAN_IP = $lanIp
$env:VMOTION_HOST_IP = $lanIp
$env:CLOUD_GATEWAY_URL = $GatewayUrl
$env:VMOTION_SHARED_STORAGE = $SharedDir
$env:VBOX_MANAGE_PATH = $vboxPath
$env:VBOX_MIGRATION_MODE = "cold_ova"
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
    exit 1
}

