# VMotion AI — Real Infrastructure Test Plan & Integration Contract

This document specifies the exact environment requirements, security architecture, data contract, success criteria, and progressive 15-stage test plan for connecting VMotion AI to genuine virtualization infrastructure.

---

## 1. Minimum Real Infrastructure Requirements

To validate VMotion AI on real hardware or cloud-nested hypervisors, the physical or nested environment must satisfy the following minimum baseline. *SimulationProvider cannot satisfy these requirements.*

```
+-------------------------------------------------------------------------------+
|                       MINIMUM REAL TEST TOPOLOGY                              |
|                                                                               |
|   +--------------------------+               +--------------------------+     |
|   |       REAL NODE A        |               |       REAL NODE B        |     |
|   |  (Hypervisor Host 1)     |               |  (Hypervisor Host 2)     |     |
|   |  - Static IP (e.g. .10)  |               |  - Static IP (e.g. .11)  |     |
|   |  - Hypervisor Daemon     |<=============>|  - Hypervisor Daemon     |     |
|   |  - Bridged Network       |  Migration    |  - Bridged Network       |     |
|   |                          |  Network      |                          |     |
|   |   +------------------+   |  (QEMU NBD    |   +------------------+   |     |
|   |   |     REAL VM      |   |   / TCP)      |   |  (Target Buffer) |   |     |
|   |   |  - Guest OS      |---+-------------->|   |  - Idle Headroom |   |     |
|   |   |  - QEMU Agent    |   |               |   |  - Reserved RAM  |   |     |
|   |   +------------------+   |               |   +------------------+   |     |
|   +--------------------------+               +--------------------------+     |
+-------------------------------------------------------------------------------+
                                      ^
                                      | HTTPS REST API (Port 8006)
                                      | Scoped API Token Auth
                                      v
                        +---------------------------+
                        |    WINDOWS WORKSTATION    |
                        |   VMotion AI Controller   |
                        +---------------------------+
```

### Hardware & Virtualization Requirements
1. **Real Node A (Source Hypervisor)**:
   - Minimum 4 physical/virtual CPU cores, 8 GB RAM, 50 GB storage.
   - Running Proxmox VE 9.x/current supported release (currently 9.2), x86_64, with hardware virtualization enabled.
   - Network connectivity to Node B and the Windows control machine.
2. **Real Node B (Target Hypervisor)**:
   - Minimum 4 physical/virtual CPU cores, 8 GB RAM, 50 GB storage.
   - Symmetrical hypervisor configuration in cluster with Node A.
   - Unallocated memory headroom of at least VM RAM footprint $+ 20\%$.
   - **Cluster Quorum & Resilience**: A 2-node cluster operates with both nodes online but loses majority quorum ($1/2 = 50\%$) if one node fails or disconnects. For single-node failure resilience in a 2-node test lab, an external QDevice (`corosync-qnetd`) can be configured to provide a tie-breaker 3rd vote. A 2-node cluster without a QDevice is strictly for testing and must not be described as equivalent to a production 3+ node fault-tolerant HA architecture.
3. **Real Workload (Test VM)**:
   - Running lightweight Linux distribution (Alpine Linux or Debian 12 Minimal).
   - 1–2 vCPUs, 1024–2048 MB RAM, 10 GB disk.
   - `qemu-guest-agent` installed and active (`systemctl enable --now qemu-guest-agent`).
4. **Network Connectivity**:
   - Node-to-node latency $< 5\text{ ms}$, MTU 1500 (or 9000 jumbo frames if supported).
   - Unfiltered TCP traffic between nodes on migration stream ports (TCP 60000–60050 for Proxmox; TCP 49152–49215 for Libvirt).
5. **Storage Mechanism**:
   - Supported: Either shared datastore (NFSv4 / Ceph mount on both nodes at identical paths) OR online local disk migration (`with-local-disks=1` via QEMU NBD mirroring). Neither is an absolute architectural requirement.

---

## 2. Control Machine Architecture

The control architecture strictly preserves the existing separation of concerns:

$$\text{Windows Workstation} \xrightarrow{\text{HTTPS REST (Port 8006)}} \text{Hypervisor API} \xrightarrow{\text{Cluster Interconnect}} \text{Physical Hosts}$$

- **No Hypervisor on Windows**: The Windows development machine runs VMotion AI (FastAPI backend + React frontend). It does NOT run local VMs or require firmware virtualization.
- **Pure Client Protocol**: All control-plane interactions operate via standard HTTP/JSON requests using Python `httpx`, eliminating local hypervisor C-library bindings on Windows.

---

## 3. Security Specification

1. **Credential Handling**:
   - Authenticates via scoped API tokens (e.g., `PVEAPIToken=vmotion-api@pve!automation=secret`).
   - Tokens require only the verified privileges derived from implemented API calls: `VM.Migrate`, `VM.Audit`, `VM.GuestAgent.Audit`, `Datastore.Audit`, `Datastore.AllocateSpace`, `Sys.Audit`. (`VM.Allocate` is excluded from the baseline set as the implemented migration endpoint does not call a VM allocation API; verify with `pveum user token permissions` whether Proxmox internally requires it.) (Note: `VM.Monitor` is not a valid PVE 9 privilege and has been removed.)
   - No root password or SSH private keys stored or transmitted by VMotion AI.
2. **Secret Masking & Frontend Decoupling**:
   - Hypervisor credentials and API token secrets are stored securely on the backend (`.env` or encrypted settings store).
   - When the frontend queries cluster configuration via `GET /api/cluster/config`, the backend strictly masks secrets (`••••••••`).
   - The browser client NEVER receives plaintext hypervisor API keys.
3. **Network Boundary & Port Matrix**:
   - Control Plane to Hypervisor: TCP 8006 (HTTPS REST API).
   - Node A to Node B: TCP 60000–60050 (QEMU live migration data stream; encryption subject to cluster configuration).
   - Cluster Quorum / Corosync: UDP 5405–5412.

---

## 4. Real Data Contract

To guarantee seamless transition from simulation to real infrastructure, the backend data models are identical across all provider implementations. The frontend requires **zero architectural modifications**:

| Domain Object | Schema Definition | Simulation Provider Output | Real Proxmox Provider Output |
| :--- | :--- | :--- | :--- |
| **ClusterState** | `app.providers.base.ClusterState` | `is_live: false`, simulated node maps | `is_live: true`, real node maps |
| **NodeTelemetry**| `app.providers.base.NodeTelemetry`| Simulated CPU/RAM drift | Real RRD / `/nodes` statistics |
| **VMTelemetry** | `app.providers.base.VMTelemetry` | Simulated load profiles | Real `/cluster/resources` data |
| **MigrationPlan**| `app.providers.base.MigrationPlan`| `plan-sim-{uuid}` | `plan-pve-{timestamp}` |
| **MigrationTask**| `app.providers.base.MigrationTaskStatus`| Synthetic progress 0% $\to$ 100% | Real UPID progress and log status |
| **AuditEvent** | `app.audit.ledger.AuditEntry` | Logged to append-only ledger | Logged to append-only ledger |

---

## 5. Real Migration Success Contract & Project Truthfulness

> [!IMPORTANT]
> **Empirical Verification Status**:
> All live hypervisor capabilities remain strictly **UNVERIFIED on real hardware**:
> - Real Proxmox hardware connectivity: **UNVERIFIED**
> - Real telemetry stream: **UNVERIFIED**
> - Real VM migration: **UNVERIFIED**
> - Real UPID execution: **UNVERIFIED**
> - Real placement verification: **UNVERIFIED**
> - Real guest-agent verification: **UNVERIFIED**
> The system does not claim "production-grade", "guaranteed", "zero-downtime", or "optimal" performance.

Before VMotion AI can transition any real migration proposal to `VERIFIED`, all three of the following independent assertions must be satisfied:

$$\text{MIGRATION VERIFIED} \iff (\text{Task Completed}) \land (\text{Placement Confirmed}) \land (\text{Guest Health Confirmed})$$

1. **Hypervisor Task Success**:
   - The hypervisor task tracker must report exit status `OK` (or return code 0).
   - Migration task state transitions to `VERIFYING`.
2. **Physical Placement Assertion**:
   - The control plane re-queries the independent cluster inventory endpoint (`GET /cluster/resources?type=vm`).
   - Asserts: `vm.node_id == expected_destination_node`.
   - Asserts: `vm.node_id != source_node`.
3. **Guest Workload Health Verification**:
   - The control plane issues a guest agent responsiveness query (`qemu-guest-agent ping` or status check).
   - Asserts: Guest kernel responds and reports status `running`.
   - Asserts: Workload IP address remains responsive on the virtual network.

If any check fails, the task transitions to `FAILED` and raises an alert in the audit ledger.

---

## 6. Progressive 15-Stage Real Connection Test Plan

All tests must be executed in strict sequence. **Test 07 (Manual Migration Outside VMotion AI) must succeed before VMotion AI is ever permitted to dispatch a live migration.**

```
Phase A: Read-Only Discovery & Telemetry (Tests 01 - 05)
   ↓
Phase B: Precondition Validation & Manual Baseline (Tests 06 - 07)
   ↓ [GATE: Manual live migration MUST succeed first]
Phase C: Governed Migration Lifecycle (Tests 08 - 11)
   ↓
Phase D: Verification & Audit Assertions (Tests 12 - 15)
```

### Stage A: Discovery & Read-Only Telemetry
- **TEST 01: Connection & Authentication**:
  - *Action*: Call `test_connection()` from VMotion AI against the real hypervisor endpoint.
  - *Pass Criteria*: Returns HTTP 200, status `CONNECTED`, latency $< 100\text{ ms}$, hypervisor version parsed.
- **TEST 02: Compute Node Discovery**:
  - *Action*: Call `discover_nodes()`.
  - *Pass Criteria*: Discovers exactly Node A and Node B with valid CPU cores, total RAM, and `status: "online"`.
- **TEST 03: Workload Discovery**:
  - *Action*: Call `discover_vms()`.
  - *Pass Criteria*: Discovers the test VM with correct VMID, assigned node (`node-01`), allocated RAM, and `status: "running"`.
- **TEST 04: Real Telemetry Ingest**:
  - *Action*: Ingest real cluster telemetry over 30 continuous seconds.
  - *Pass Criteria*: Live CPU % and RAM % reflect real workload activity without NaN values or schema violations.
- **TEST 05: VM State Inspection**:
  - *Action*: Call `inspect_vm_state(vmid)`.
  - *Pass Criteria*: Accurately reflects guest uptime, running state, and memory reservation.

### Stage B: Precondition Validation & Manual Baseline
- **TEST 06: Migration Precondition Validation**:
  - *Action*: Call `validate_migration(vmid, target_node="node-02")`.
  - *Pass Criteria*: Asserts source and target nodes exist, cluster quorum is intact, and storage is accessible.
- **TEST 07: Manual Migration Outside VMotion AI (MANDATORY)**:
  - *Action*: Execute a manual live migration using the Proxmox Web GUI or CLI:
    ```bash
    qm migrate <vmid> node-02 --online 1 --with-local-disks 1
    ```
  - *Pass Criteria*: Migration succeeds without dropped network packets, VM switches over to Node B, guest OS continues running.
  - *Rule*: **If Test 07 fails, do not proceed. Debug infrastructure networking/storage first.**

### Stage C: Governed Migration Lifecycle
- **TEST 08: VMotion AI Migration Proposal**:
  - *Action*: Induce CPU hotspot on Node A or trigger manual rebalance proposal in VMotion AI.
  - *Pass Criteria*: System generates candidate proposal to migrate test VM from Node A to Node B.
- **TEST 09: Deterministic Safety Gate Evaluation**:
  - *Action*: Evaluate all 8 hard safety rules against the real cluster state.
  - *Pass Criteria*: 8/8 checks pass with `passed: true`. Status advances to `PENDING_APPROVAL`.
- **TEST 10: Human Operator Gate**:
  - *Action*: Operator clicks "APPROVE MIGRATION" in the VMotion AI frontend.
  - *Pass Criteria*: Proposal status transitions `PENDING_APPROVAL` $\to$ `APPROVED` $\to$ `DISPATCHED`.
- **TEST 11: Hypervisor Migration Dispatch**:
  - *Action*: VMotion AI dispatches `execute_migration()`.
  - *Pass Criteria*: Proxmox accepts the API call and returns an opaque UPID string. Task state becomes `TASK_RUNNING`.

### Stage D: Verification & Audit Assertions
- **TEST 12: Real Task Monitoring**:
  - *Action*: VMotion AI polls `monitor_migration_task(upid)` every 1.0 second.
  - *Pass Criteria*: Progress updates from 0% $\to$ 100%; detects `status: "stopped"` and `exitstatus: "OK"`.
- **TEST 13: Destination Placement Verification**:
  - *Action*: VMotion AI executes `verify_placement(vmid, "node-02")`.
  - *Pass Criteria*: Confirms test VM is now registered on Node B.
- **TEST 14: Guest Workload Health Verification**:
  - *Action*: VMotion AI executes `verify_vm_health(vmid)`.
  - *Pass Criteria*: Confirms QEMU guest agent responds and guest OS is running.
- **TEST 15: Append-Only Audit Ledger Verification**:
  - *Action*: Query `GET /api/audit/logs`.
  - *Pass Criteria*: All 6 lifecycle events are committed to the ledger with valid timestamps and details:
    1. `AI_RECOMMENDATION_GENERATED`
    2. `SAFETY_CHECKS_EVALUATED`
    3. `HUMAN_APPROVAL_GRANTED`
    4. `MIGRATION_TASK_STARTED`
    5. `DESTINATION_PLACEMENT_VERIFIED`
    6. `MIGRATION_VERIFIED`
