# VMotion AI — Intelligent Infrastructure Control Plane

VMotion AI is an AI-powered virtual machine migration control plane capable of orchestrating live VM migrations across real and simulated virtualization infrastructure.

---

## 1. Architectural Principles

```
REAL INFRASTRUCTURE / HIGH-FIDELITY SIMULATION
                         ↓
                  REAL TELEMETRY
                         ↓
                VMOTION AI BACKEND
                         ↓
           OBSERVATION / FEATURE ADAPTER (103 Feat)
                         ↓
               PPO / RL DECISION ENGINE
                         ↓
          DETERMINISTIC SAFETY GATE (8 Mandatory Rules)
                         ↓
              MIGRATION PLANNER
                         ↓
              HUMAN APPROVAL GATE
                         ↓
           VIRTUALIZATION PLATFORM API
                         ↓
                 REAL VM MIGRATION
                         ↓
                  TASK MONITORING
                         ↓
             POST-MIGRATION VERIFICATION
                         ↓
               PREMIUM CONTROL-PLANE UI
```

1. **The AI Recommends. The Safety Gate Validates. The Human Approves. The Backend Executes.**
   - The frontend never touches the hypervisor directly.
   - The AI model cannot override safety checks or execute without human operator sign-off (`ENABLE_HUMAN_APPROVAL = true` by default).
2. **Deterministic Safety Architecture (8 Mandatory Checks)**:
   - `VM_RUNNING_STATE`: VM must be active and operational.
   - `DISTINCT_TARGET`: `source_node != destination_node`.
   - `SOURCE_NODE_HEALTH`: Source hypervisor is online with zero critical alarms.
   - `DEST_NODE_HEALTH`: Destination hypervisor is reachable and healthy.
   - `DEST_RAM_HEADROOM`: Target unallocated RAM exceeds VM footprint + safety buffer.
   - `DEST_CPU_CAPACITY`: Projected target CPU load $\le 85.0\%$.
   - `STORAGE_AND_QUORUM`: Shared storage datastore and cluster quorum confirmed.
   - `COOLDOWN_PERIOD`: Minimum 60-second cooldown elapsed since last migration.
3. **Strict Migration Lifecycle & Verification**:
   - Never marked completed upon dispatch.
   - States: `PREPARING` → `VALIDATING` → `MIGRATING` → `MONITORING` → `VERIFYING` → `VERIFIED`.
   - Final verification actively queries destination placement and workload health.
4. **Separation of Modes**:
   - **Simulation Mode**: 3 compute nodes, 6 workloads, dynamic CPU drift,dirty memory transfer emulation.
   - **Live Mode (Proxmox VE / Libvirt KVM)**: Interfaces directly with hypervisor REST/libvirt APIs. If unreachable, displays `LIVE CLUSTER DISCONNECTED` without silent fallbacks.

---

## 2. Quickstart Guide

### Prerequisites
- **Python**: Python 3.11 (`py -3.11`)
- **Node.js**: v20+ / npm v10+

### Step 1: Start Backend
In a terminal at the project root:
```powershell
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH="backend"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Backend endpoints:
- API Root: `http://127.0.0.1:8000`
- Interactive API Docs (Swagger): `http://127.0.0.1:8000/docs`
- Telemetry WebSocket: `ws://127.0.0.1:8000/ws/telemetry`

### Step 2: Start Frontend
In a second terminal:
```powershell
cd frontend
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## 3. Automated Verification & Testing

To run the automated backend test suite:
```powershell
$env:PYTHONPATH="backend"
.\.venv\Scripts\pytest.exe -v backend/tests
```

All 8 tests verify:
- Placement & health verification lifecycle
- 103-dimension observation adapter mathematical bounds
- 8 deterministic safety gate failure modes and nominal passes
