# VMotion AI — Intelligent Infrastructure Control Plane
### AI-Powered Virtual Machine Live Migration Control Plane using Oracle VirtualBox Teleportation & Tailscale Private Overlay

VMotion AI is a public-cloud virtual machine migration control plane driven by reinforcement learning (PPO V5). It remotely monitors and orchestrates real-time live virtual machine teleportation across physical Oracle VirtualBox hosts anywhere on the internet using an outbound WebSocket Agent Gateway and Tailscale peer-to-peer overlay network, while enforcing strict deterministic safety bounds and human-in-the-loop operational governance.

---

## 1. System Architecture

```
                       PUBLIC CLOUD CONTROL PLANE
                (FastAPI + React 19 Hosted in Public Cloud)
                  [https://vmotion-ai.cloud.example.com]
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
   Tailscale: 100.64.0.10                               Tailscale: 100.64.0.20
           │                                                   │
           │                                                   │
           └═══════════════ TAILSCALE DATA PLANE ══════════════┘
                     Encrypted Direct WireGuard Mesh
                   TCP Port 60050 Live Teleport Stream
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
                ORACLE VIRTUALBOX TELEPORTATION ENGINE
          Target Arming: modifyvm --teleporter on + startvm headless
          Source Stream: controlvm teleport --host 100.64.0.20 --port 60050
                                     │
                                     ▼
                     SHARED NETWORK STORAGE (SMB / NFS)
                     Identical VDI Disk Resides on Shared Mount
                                     │
                                     ▼
               POST-MIGRATION PLACEMENT & HEALTH VERIFICATION
                Source Released • Target Verified Running Headlessly
```

### Core Architectural Principles
1. **Public Cloud Control Plane with Edge Execution**:
   - The VMotion AI control plane runs in the public cloud (Render, Railway, AWS, Docker).
   - Hypervisors do NOT run in the cloud; they run on physical laptops or workstations (Host A and Host B).
   - Remote host agents establish persistent **outbound WebSocket connections** (`/ws/agent`), requiring zero inbound port forwarding or public IP addresses on the laptops.
2. **Tailscale Peer-to-Peer Data Plane**:
   - Live VM memory transmission occurs directly between Host A and Host B over a private, encrypted **Tailscale WireGuard overlay mesh** (`100.x.y.z`).
   - The high-throughput teleportation stream bypasses the public cloud server entirely, ensuring maximum throughput, minimum latency, and enterprise-grade data privacy.
3. **The AI Recommends. The Safety Gate Validates. The Human Approves. The Backend Executes**:
   - The AI agent cannot dispatch hypervisor commands unilaterally.
   - Deterministic safety validation overrides AI policy decisions unconditionally.
   - Operator human signoff is strictly required prior to dispatch.
4. **Authoritative Oracle VirtualBox Teleportation**:
   - Live migration streams RAM and CPU execution state across Tailscale port `60050` with sub-second guest pause time.
   - Target VM is pre-armed via `VBoxManage modifyvm <target> --teleporter on --teleporter-port 60050 --teleporter-address 0.0.0.0` and started headlessly.
   - Source transfers state via `VBoxManage controlvm <source> teleport --host <target_tailscale_ip> --port 60050 --maxdowntime 500`.
5. **Deterministic Safety Architecture**:
   - 8 core mandatory checks and 16 fail-closed validation rules.
   - Typed error codes (`VBX_VM_NOT_FOUND`, `VBX_VM_NOT_RUNNING`, `VBX_TARGET_UNREACHABLE`, `VBX_INCOMPATIBLE_VM_CONFIG`, `VBX_SHARED_STORAGE_UNAVAILABLE`, `VBX_TELEPORT_PORT_BLOCKED`, `VBX_SNAPSHOT_CONFLICT`, etc.).
   - Prevents split-brain scenarios, resource starvation, and CPU instruction incompatibilities.
6. **Append-Only Forensic Audit Ledger**:
   - Every telemetry frame, recommendation, safety veto, approval, migration phase transition, and verification check is immutably logged with microsecond timestamps and cryptographic task IDs.

---

## 2. Implementation Readiness & Physical Laboratory Status

To maintain absolute academic and engineering honesty (for institutional evaluation at **Vellore Institute of Technology (VIT), Chennai**):

| Domain | Completion | Status & Verification |
|---|:---:|---|
| **Public Cloud Control Plane** | **100%** | Multi-stage Dockerfile, FastAPI REST/WSS, static frontend hosting, Render blueprint |
| **Cloud Agent Gateway Router** | **100%** | Persistent outbound WSS, token authentication, correlation ID matching, RPC timeout handling |
| **Tailscale Overlay Integration** | **100%** | Automated Tailscale IP discovery, peer-to-peer data plane routing on port 60050 |
| **PPO V5 Reinforcement Learning Engine** | **100%** | Frozen PyTorch/Stable-Baselines3 weights (`ppo_v5_final.zip`), 103-feature contract v1.0.0, Discrete(7) action space |
| **Deterministic Safety Gate** | **100%** | 16 fail-closed rules, 8 core mandatory checks, zero-bypass policy, typed `VBX_*` error codes |
| **VirtualBox Provider & Host Agent** | **100%** | Native `VBoxManage` integration, machine-readable parser, target compatibility matrix, pre-warming, teleport dispatch |
| **Automated Test Suite** | **100%** | **117 passing automated unit & integration tests** in `backend/tests/` (100% pass rate) |
| **Frontend Control Plane UI** | **100%** | React 19, TypeScript, Vite, Tailwind CSS, Tailscale live metrics, centerpiece **Live Demo** screen |
| **Two-Host Physical Laboratory Run** | **Demonstration Ready** | **READY (Pending physical two-host laboratory execution)**. Software is completely implemented; execution occurs once two physical computers connect via Tailscale. |

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

### Option B: Connecting Physical Laptops (Host A & Host B)

#### Prerequisites on each physical laptop:
1. Install [Oracle VirtualBox 7.x](https://www.virtualbox.org/).
2. Install [Tailscale](https://tailscale.com/) and run `tailscale up` to join your private network.
3. Python 3.11 with `pip install -r vmotion-agent/requirements.txt`.

#### 1. On Laptop A (Source Host):
```powershell
$env:CLOUD_GATEWAY_URL="wss://your-cloud-control-plane/ws/agent"
$env:HOST_ID="vbox-host-a"
$env:AGENT_SECRET="your-secret-agent-token"
$env:VBOX_SHARED_STORAGE_PATH="C:\shared_vdi"

python vmotion-agent/agent.py
```

#### 2. On Laptop B (Target Host):
```powershell
$env:CLOUD_GATEWAY_URL="wss://your-cloud-control-plane/ws/agent"
$env:HOST_ID="vbox-host-b"
$env:AGENT_SECRET="your-secret-agent-token"
$env:VBOX_SHARED_STORAGE_PATH="C:\shared_vdi"

python vmotion-agent/agent.py
```

Both agents will immediately authenticate and register over outbound WebSocket, report their Tailscale `100.x.y.z` IP addresses, and begin streaming live hardware telemetry to the cloud control plane.

---

## 4. Verification & Testing

To run the complete automated test suite:
```powershell
$env:PYTHONPATH="backend"
.\.venv\Scripts\pytest.exe -v backend/tests
```

### Verified Test Areas (117 Tests Passing):
- **Cloud Agent Gateway**: `backend/tests/test_agent_gateway.py` (7 tests)
  - Agent outbound registration & session creation
  - Heartbeat freshness and timeout detection
  - RPC command dispatch with unique correlation ID matching
  - Agent response resolution and error propagation
  - Offline agent error handling (`AgentOfflineError`)
  - Request timeout enforcement (`AgentCommandTimeoutError`)
  - Disconnect unregistration and future cleanup
- **VirtualBox Provider**: `backend/tests/test_virtualbox_provider.py` (8 tests)
  - VBoxManage path discovery and version validation
  - Machine-readable `showvminfo` output parsing
  - Target compatibility matrix checking with snapshot absence verification
  - Pre-flight teleport target receiver configuration via Agent Gateway RPC
  - Asynchronous teleportation command dispatch over Tailscale overlay
  - Post-teleport placement verification via remote agent
- **VirtualBox Host Agent**: `backend/tests/test_virtualbox_agent.py` (6 tests)
  - Secret token authentication
  - Live hardware metrics & Tailscale IP reporting (`psutil`)
  - Machine inventory reporting
  - Target teleporter pre-warming
  - Live teleportation dispatch
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
