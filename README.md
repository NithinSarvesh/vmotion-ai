# VMotion AI — Intelligent Infrastructure Control Plane
### AI-Powered Virtual Machine Cold Migration Control Plane using Oracle VirtualBox OVA Export/Import & Direct LAN SMB Transfer

VMotion AI is a public-cloud virtual machine migration control plane driven by reinforcement learning (PPO V5). It remotely monitors physical Oracle VirtualBox hosts over outbound WebSocket Agent connections and orchestrates deterministic, offline (cold) VM migration across physical hosts over local SMB file sharing. The VM undergoes graceful ACPI shutdown (incurring planned downtime during transfer), appliance export (OVA), direct LAN SMB package copy, cryptographic SHA-256 integrity verification, target hypervisor import, and automated headless boot—all governed by deterministic safety gates and human-in-the-loop operational approvals.

---

## 1. System Architecture

```
                       PUBLIC CLOUD CONTROL PLANE
                (FastAPI + React 19 Hosted in Public Cloud / Render)
                  [https://vmotion-ai-control-plane.onrender.com]
                                     ▲
                                     │  Outbound Persistent WSS
                                     │  (/ws/agent - Auth Token)
                                     ▼
                      CLOUD AGENT GATEWAY ROUTER
                                     │
           ┌─────────────────────────┴─────────────────────────┐
           │                                                   │
    Outbound WSS                                        Outbound WSS
    (No Port Forwarding)                                (No Port Forwarding)
           │                                                   │
           ▼                                                   ▼
PHYSICAL VIRTUALBOX HOST A                           PHYSICAL VIRTUALBOX HOST B
(Source Laptop / Physical PC)                        (Target Laptop / Physical PC)
   [vmotion-agent v2.0]                                 [vmotion-agent v2.0]
   LAN / Hotspot: 172.16.0.2                            LAN / Hotspot: 172.16.0.55
   Shared Dir: C:\VMotionShared                         Staging Dir: C:\VMotionStaging
           │                                                   ▲
           │                                                   │
           └═══════════════ DIRECT LAN SMB DATA PLANE ═════════┘
                     Direct Windows SMB Copy (Bypasses Cloud)
                     Package: C:\VMotionShared\*.ova
                                     │
                                     ▼
                   OBSERVATION ADAPTER (v1.0.0 Contract)
                     103 Continuous Features in [-1, 1]
                                     │
                                     ▼
                    AI DECISION ENGINE (PPO V5 FROZEN)
                    Discrete(7) Action Space with Masks
                                     │
                                     ▼
                DETERMINISTIC SAFETY GATE (16 Strict Checks)
                   Fail-Closed: VBX_* Typed Error Codes
                                     │
                                     ▼
                   HUMAN-IN-THE-LOOP APPROVAL GATE
                Operator Cryptographic / Manual Signoff
                                     │
                                     ▼
                ORACLE VIRTUALBOX COLD MIGRATION ENGINE
          9-Stage Deterministic Pipeline (Fail-Closed Execution):
          1. PREFLIGHT      → Quotas, exact VM & agent liveness verified
          2. SOURCE SHUTDOWN→ ACPI shutdown (planned downtime)
          3. EXPORT         → VBoxManage export + SHA-256 calculation
          4. TRANSFER       → Direct SMB copy into target staging
          5. CHECKSUM VERIFY→ SHA-256 cryptographic match check
          6. IMPORT         → VBoxManage import dynamic appliance
          7. DESTINATION ON → Headless VM start on target host
          8. VERIFY         → Hypervisor health & state verification
          9. SUCCESS        → Verified status & forensic audit ledger
```

### Core Architectural Principles
1. **Public Cloud Control Plane with Edge Execution**:
   - The VMotion AI control plane runs in the public cloud (Render, Railway, Docker).
   - Hypervisors do NOT run in the cloud; they run on physical laptops or workstations (Host A and Host B).
   - Remote host agents establish persistent **outbound WebSocket connections** (`/ws/agent`), requiring zero inbound port forwarding or public IP addresses on the laptops.
2. **Real Cold / Offline VM Migration with Planned Downtime**:
   - VMotion AI performs genuine, physical cold VM migration using Oracle VirtualBox OVA appliance export and import.
   - The guest operating system is gracefully powered off via ACPI before export, ensuring zero filesystem corruption or split-brain memory divergence. Planned downtime occurs during export and network transfer.
3. **Direct LAN / Hotspot SMB Data Plane**:
   - VM disk and state are packaged into an OVA appliance file and transferred directly between Host A and Host B across the local Wi-Fi / hotspot network via Windows SMB (`\\HostA\VMotionShared`).
   - The high-volume disk transfer completely bypasses the public cloud server, eliminating bandwidth bottlenecks and safeguarding data privacy.
4. **Cryptographic Integrity & Quarantine**:
   - Host A calculates a 256-bit SHA-256 checksum during export.
   - Host B independently recalculates the SHA-256 digest upon transfer completion before touching the hypervisor. If a checksum mismatch occurs, the file is immediately quarantined (`.corrupt`) and the task fails closed.
5. **The AI Recommends. The Safety Gate Validates. The Human Approves. The Backend Executes**:
   - The AI agent cannot dispatch hypervisor commands unilaterally.
   - Deterministic safety validation overrides AI policy decisions unconditionally.
   - Operator human signoff is strictly required prior to dispatch.
6. **Strict Fail-Closed Real Execution (No Synthetic Data)**:
   - Both physical agents must be online before migration starts. If either agent is offline, migration aborts at PREFLIGHT.
   - Synthetic metrics, fake durations, and mock checksums are strictly rejected. The destination VM must be confirmed in `running` state by the target hypervisor before `SUCCESS` is recorded.
7. **Append-Only Forensic Audit Ledger**:
   - Every telemetry frame, recommendation, safety veto, approval, migration phase transition, and verification check is immutably logged with microsecond timestamps and cryptographic task IDs.

---

## 2. Implementation Readiness & Physical Laboratory Status

To maintain absolute academic and engineering honesty (for institutional evaluation at **Vellore Institute of Technology (VIT), Chennai**):

| Domain | Completion | Status & Verification |
|---|:---:|---|
| **Public Cloud Control Plane** | **100%** | Multi-stage Dockerfile, FastAPI REST/WSS, static frontend hosting, Render blueprint |
| **Cloud Agent Gateway Router** | **100%** | Persistent outbound WSS, token authentication, correlation ID matching, RPC timeout handling |
| **Direct SMB Data Plane** | **100%** | Windows SMB share configuration, UNC path discovery, direct LAN copy, disk quota validation |
| **PPO V5 Reinforcement Learning Engine** | **100%** | Frozen PyTorch/Stable-Baselines3 weights (`ppo_v5_final.zip`), 103-feature contract v1.0.0, Discrete(7) action space |
| **Deterministic Safety Gate** | **100%** | 16 fail-closed rules, 8 core mandatory checks, zero-bypass policy, typed `VBX_*` error codes |
| **VirtualBox Provider & Cold OVA Engine** | **100%** | 9-stage deterministic pipeline, ACPI graceful shutdown, OVA export/import, SHA-256 integrity verification |
| **Automated Test Suite** | **100%** | **158 passing automated unit & integration tests** in `backend/tests/` (100% pass rate) |
| **Frontend Control Plane UI** | **100%** | React 19, TypeScript, Vite, Tailwind CSS, live agent telemetry, centerpiece **Live Demo** screen |
| **Two-Host Physical Laboratory Run** | **Demonstration Ready** | **READY (Pending physical two-host laboratory execution)**. Software is completely implemented; execution occurs when Host A and Host B run their setup scripts on the same phone hotspot / LAN. |

> [!NOTE]
> **Automated Mock Tests vs. Physical Host Runs**:
> The 158 automated pytest tests validate all software contracts, gateway authentication, observation normalization, PPO inference, safety gate edge cases, and 9-stage cold migration orchestration by mocking hypervisor and agent boundaries. Physical two-host execution validates actual Windows SMB transfer speed, real VBoxManage export/import durations, and physical hardware behavior when running `scripts/setup_host_a_source.ps1` and `scripts/setup_host_b_target.ps1`.

---

## 3. Quickstart & Deployment

### Option A: Deploying the Cloud Control Plane (Docker / Cloud Host)

```bash
# Build and run the public cloud control plane container
docker build -t vmotion-ai .
docker run -p 8000:8000 \
  -e MODE=virtualbox \
  -e SERVE_FRONTEND=true \
  -e GATEWAY_AGENT_TOKEN="your-secret-agent-token" \
  vmotion-ai
```

The cloud control plane will be available at:
- Control Plane Web UI: `http://localhost:8000`
- API Swagger Docs: `http://localhost:8000/docs`
- Agent Gateway Endpoint: `ws://localhost:8000/ws/agent`
- Real-Time Telemetry Stream: `ws://localhost:8000/ws/telemetry`

---

### Option B: Connecting Two Physical Windows Laptops (Real Cold OVA Migration)

VMotion AI executes **Real Cold / Offline VM Migration** across two physical Windows laptops connected over a mobile phone hotspot or local LAN. The VM is powered off gracefully on Host A, exported as an Open Virtualization Appliance (OVA), transferred directly over a Windows SMB share with SHA-256 integrity verification, imported into Oracle VirtualBox on Host B, and booted headlessly. Zero cloud data relay occurs.

#### Prerequisites on each physical laptop:
1. Connect both laptops to the **SAME mobile phone hotspot** or local Wi-Fi.
2. Install [Oracle VirtualBox 7.x](https://www.virtualbox.org/).
3. Python 3.10+ installed (`pip install -r vmotion-agent/requirements.txt`).
4. On Host A: have your real VM (e.g. `VMotion-Demo` or Ubuntu guest) registered in VirtualBox.
5. On Host B: **no VM pre-creation is needed**. The agent dynamically imports the appliance as `VMotion-Migrated-<job-id>`.

---

#### Step 1: Launch Host A (Source Laptop)
Open PowerShell as **Administrator** and run:
```powershell
.\scripts\setup_host_a_source.ps1
```
The script will:
- Verify Administrator elevation and VirtualBox installation.
- Securely prompt for the Render `GATEWAY_AGENT_TOKEN` (never logged or printed).
- Create and share `C:\VMotionShared` via Windows SMB so Host B can read it directly.
- Auto-discover your hotspot/LAN IP address.
- Launch the VMotion Agent connecting outbound to the Render control plane.

Take note of the Host A LAN IP shown on the screen (e.g., `172.16.0.2` or `192.168.43.15`).

---

#### Step 2: Launch Host B (Target Laptop / Friend's Laptop)
Open PowerShell as **Administrator** and run:
```powershell
.\scripts\setup_host_b_target.ps1 -HostAIp "<Host A LAN IP>"
```
The script will:
- Verify Administrator elevation and VirtualBox installation.
- Securely prompt for the Render `GATEWAY_AGENT_TOKEN`.
- Initialize local staging directory `C:\VMotionStaging`.
- Verify network reachability and access to Host A's SMB share (`\\<HostA-LAN>\VMotionShared`).
- Launch the VMotion Agent connecting outbound to the Render control plane.

---

#### Step 3: Trigger Migration from the Cloud Web Dashboard
1. Open your public Render control plane URL (or `http://localhost:8000`).
2. Navigate to the **Live Demo** section. Both physical laptops will show as **ONLINE** with real-time LAN IP addresses and hardware metrics.
3. The PPO V5 decision engine will evaluate 103 telemetry dimensions and recommend migrating the VM to Host B.
4. The Deterministic Safety Gate will validate all 16 fail-closed safety checks.
5. Click **`[MIGRATE VM]`**.
6. Watch the real-time progression across all 9 stages:
   1. **`PREFLIGHT`**: Storage quotas and hypervisor readiness checks.
   2. **`SOURCE SHUTDOWN`**: Graceful guest ACPI shutdown (fail-closed on timeout).
   3. **`EXPORT`**: `VBoxManage export` packages VM into `C:\VMotionShared\*.ova` and calculates SHA-256 digest.
   4. **`TRANSFER`**: Host B copies package across LAN SMB into `C:\VMotionStaging`.
   5. **`CHECKSUM VERIFIED`**: SHA-256 verified on destination; corrupted files are quarantined immediately.
   6. **`IMPORT`**: `VBoxManage import` registers appliance as `VMotion-Migrated-<job-id>` (idempotent).
   7. **`DESTINATION STARTED`**: Host B powers on imported VM headlessly.
   8. **`VERIFY`**: Hypervisor confirms VM is running with intact guest health.
   9. **`SUCCESS`**: Total migration metrics recorded in append-only forensic audit log.

---

## 4. Verification & Testing

To run the complete automated test suite:
```powershell
.\.venv\Scripts\pytest.exe -v backend/tests
```

### Verified Test Areas (158 Tests Passing, 100% Pass Rate):
- **VirtualBox Cold OVA Migration**: `backend/tests/test_virtualbox_cold_migration.py` (23 tests)
  - Preflight disk space quota failure and validation
  - Preflight failure when source or target agent is offline (fail-closed)
  - Preflight failure when requested VM is not registered on Host A
  - Graceful ACPI guest shutdown timeout and success
  - Appliance export failure and SHA-256 cryptographic calculation
  - Direct LAN SMB transfer failure and local staging copy
  - Checksum mismatch detection and corrupted file quarantine (`.corrupt`)
  - Duplicate job request rejection (idempotency protection)
  - Appliance import failure and dynamic registration
  - Headless VM start failure handling
  - Destination running health verification
  - Destination failure when VM not running fails closed at VERIFY
  - Authoritative `VBOX_MIGRATION_MODE=cold_ova` routing
  - Explicit legacy `teleport` mode routing
  - Full end-to-end 9-stage orchestration in `VirtualBoxProvider` with verified live metrics
- **Cloud Agent Gateway**: `backend/tests/test_agent_gateway.py` (7 tests)
  - Agent outbound registration & session creation
  - Heartbeat freshness and timeout detection
  - RPC command dispatch with unique correlation ID matching
  - Agent response resolution and error propagation
  - Offline agent error handling (`AgentOfflineError`)
  - Request timeout enforcement (`AgentCommandTimeoutError`)
  - Disconnect unregistration and future cleanup
- **VirtualBox Provider & Parser**: `backend/tests/test_virtualbox_provider.py` (8 tests)
  - VBoxManage path discovery and version validation
  - Machine-readable `showvminfo` output parsing
  - Target compatibility matrix checking with snapshot absence verification
  - Pre-flight teleport target receiver configuration via Agent Gateway RPC
  - Asynchronous command dispatch over Agent Gateway
  - Post-migration placement verification via remote agent
- **VirtualBox Host Agent**: `backend/tests/test_virtualbox_agent.py` (6 tests)
  - Secret token authentication
  - Live hardware metrics & LAN IP reporting (`psutil`)
  - Machine inventory reporting
  - Target teleporter pre-warming
- **VirtualBox Live Demo & LAN**: `backend/tests/test_virtualbox_live_demo.py` (8 tests)
  - LAN IP discovery and gateway reporting
  - Direct P2P routing
  - Locked VM recovery
- **Observation Contract & PPO Model**: `backend/tests/test_observation_adapter.py`, `backend/tests/test_observation_spec.py`
  - 103-feature normalization strict adherence in $[-1, 1]$
  - Model forward pass output distribution
  - Action masking and invalid transition prevention
- **Deterministic Safety Gate**: `backend/tests/test_safety_gate.py`
  - 8 core safety rules and 16 fail-closed edge cases
  - Source/target load thresholds, RAM buffers, and cooldown intervals
- **API & Lifecycle Integration**: `backend/tests/test_api_behavior.py`, `backend/tests/test_provider_contracts.py`
  - Provider runtime switching without restart
  - Human approval workflow and forensic audit trails

---

## 5. Academic Affiliation

- **Project**: VMotion AI — Reinforcement-Learning-Driven Virtual Machine Migration Control Plane
- **Evaluation**: DA1 Evaluation / Capstone Project
- **Institution**: **Vellore Institute of Technology (VIT), Chennai, Tamil Nadu, India**

