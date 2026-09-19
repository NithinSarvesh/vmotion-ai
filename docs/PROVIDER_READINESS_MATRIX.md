# VMotion AI — Virtualization Provider Readiness Audit & Matrix

This document provides a factual, line-by-line capability audit of the virtualization provider implementations in VMotion AI as of Phase 9.

---

## 1. Provider Capability Classification Schema

Every hypervisor provider capability is classified strictly according to the following evaluation labels:
- **IMPLEMENTED**: Complete, executable source code written in `backend/app/providers/`.
- **UNIT TESTED**: Verified by automated test suites in `backend/tests/test_provider_contracts.py`.
- **MOCK TESTED**: Verified against simulated or recorded HTTP REST / RPC payloads.
- **SIMULATION TESTED**: Verified in end-to-end multi-node simulation lifecycle runs.
- **REAL INFRASTRUCTURE TESTED**: Verified against genuine physical or cloud-hosted hypervisors.
- **NOT VERIFIED**: Code exists and passes unit/mock tests, but has not yet been executed on physical hypervisors.
- **STUBBED**: Method signature exists on the interface but returns placeholder empty values, raises `NotImplementedError`, or fails due to missing OS dependencies.

*Note: In accordance with technical accuracy guidelines, the term "production-ready" is strictly prohibited.*

---

## 2. Comparative Readiness Matrix

| Capability | Simulation (`SimulationProvider`) | Proxmox VE (`ProxmoxVEProvider`) | Linux KVM / Libvirt (`LibvirtKVMProvider`) |
| :--- | :--- | :--- | :--- |
| **1. Connection Diagnostic (`test_connection`)** | `IMPLEMENTED`<br>`UNIT TESTED`<br>`SIMULATION TESTED` | `IMPLEMENTED`<br>`UNIT TESTED`<br>`MOCK TESTED`<br>`NOT VERIFIED` | `IMPLEMENTED`<br>`UNIT TESTED`<br>`NOT VERIFIED` (Missing C library) |
| **2. Session Connect (`connect`)** | `IMPLEMENTED`<br>`UNIT TESTED`<br>`SIMULATION TESTED` | `IMPLEMENTED`<br>`UNIT TESTED`<br>`MOCK TESTED`<br>`NOT VERIFIED` | `IMPLEMENTED`<br>`UNIT TESTED`<br>`NOT VERIFIED` |
| **3. Disconnect (`disconnect`)** | `IMPLEMENTED`<br>`UNIT TESTED`<br>`SIMULATION TESTED` | `IMPLEMENTED`<br>`UNIT TESTED`<br>`NOT VERIFIED` | `IMPLEMENTED`<br>`UNIT TESTED`<br>`NOT VERIFIED` |
| **4. Connection State (`is_connected`)** | `IMPLEMENTED`<br>`UNIT TESTED`<br>`SIMULATION TESTED` | `IMPLEMENTED`<br>`UNIT TESTED`<br>`NOT VERIFIED` | `IMPLEMENTED`<br>`UNIT TESTED`<br>`NOT VERIFIED` |
| **5. Compute Node Discovery (`discover_nodes`)** | `IMPLEMENTED`<br>`UNIT TESTED`<br>`SIMULATION TESTED` | `IMPLEMENTED`<br>`UNIT TESTED`<br>`MOCK TESTED`<br>`NOT VERIFIED` | `STUBBED`<br>(returns empty list `[]`) |
| **6. Workload Discovery (`discover_vms`)** | `IMPLEMENTED`<br>`UNIT TESTED`<br>`SIMULATION TESTED` | `IMPLEMENTED`<br>`UNIT TESTED`<br>`MOCK TESTED`<br>`NOT VERIFIED` | `STUBBED`<br>(returns empty list `[]`) |
| **7. Telemetry Aggregation (`collect_telemetry`)** | `IMPLEMENTED`<br>`UNIT TESTED`<br>`SIMULATION TESTED` | `IMPLEMENTED`<br>`UNIT TESTED`<br>`MOCK TESTED`<br>`NOT VERIFIED` | `STUBBED`<br>(returns empty cluster dictionaries) |
| **8. Workload State Inspection (`inspect_vm_state`)** | `IMPLEMENTED`<br>`UNIT TESTED`<br>`SIMULATION TESTED` | `IMPLEMENTED`<br>`UNIT TESTED`<br>`MOCK TESTED`<br>`NOT VERIFIED` | `STUBBED`<br>(returns `None`) |
| **9. Migration Validation (`validate_migration`)** | `IMPLEMENTED`<br>`UNIT TESTED`<br>`SIMULATION TESTED` | `IMPLEMENTED`<br>`UNIT TESTED`<br>`MOCK TESTED`<br>`NOT VERIFIED` | `STUBBED`<br>(returns `False, "Libvirt cluster validation not active."`) |
| **10. Migration Planning (`plan_migration`)** | `IMPLEMENTED`<br>`UNIT TESTED`<br>`SIMULATION TESTED` | `IMPLEMENTED`<br>`UNIT TESTED`<br>`MOCK TESTED`<br>`NOT VERIFIED` | `IMPLEMENTED`<br>(generates generic `MigrationPlan`) |
| **11. Migration Dispatch (`execute_migration`)** | `IMPLEMENTED`<br>`UNIT TESTED`<br>`SIMULATION TESTED` | `IMPLEMENTED`<br>`UNIT TESTED`<br>`MOCK TESTED`<br>`NOT VERIFIED` | `STUBBED`<br>(raises `NotImplementedError`) |
| **12. Task Progress Monitoring (`monitor_migration_task`)** | `IMPLEMENTED`<br>`UNIT TESTED`<br>`SIMULATION TESTED` | `IMPLEMENTED`<br>`UNIT TESTED`<br>`MOCK TESTED`<br>`NOT VERIFIED` | `STUBBED`<br>(raises `NotImplementedError`) |
| **13. Placement Verification (`verify_placement`)** | `IMPLEMENTED`<br>`UNIT TESTED`<br>`SIMULATION TESTED` | `IMPLEMENTED`<br>`UNIT TESTED`<br>`MOCK TESTED`<br>`NOT VERIFIED` | `STUBBED`<br>(returns `False`) |
| **14. Workload Health Verification (`verify_vm_health`)** | `IMPLEMENTED`<br>`UNIT TESTED`<br>`SIMULATION TESTED` | `IMPLEMENTED`<br>`UNIT TESTED`<br>`MOCK TESTED`<br>`NOT VERIFIED` | `STUBBED`<br>(returns `False`) |
| **15. Disconnected Truthfulness Reporting** | `IMPLEMENTED`<br>`UNIT TESTED`<br>`SIMULATION TESTED` | `IMPLEMENTED`<br>`UNIT TESTED`<br>`MOCK TESTED`<br>`NOT VERIFIED` | `IMPLEMENTED`<br>`UNIT TESTED`<br>`NOT VERIFIED` |

---

## 3. Deep Dive: `ProxmoxVEProvider` Readiness Status

The Proxmox VE provider (`backend/app/providers/proxmox.py`) is the primary live-provider integration path. Its capabilities are audited in detail below:

1. **Target Hypervisor Version**:
   - Proxmox VE 9.x/current supported release (currently 9.2), x86_64, with hardware virtualization enabled.
   - Code adheres to Proxmox VE REST API v2 specification and does not hard-code older releases.
2. **Authentication & Protocol**:
   - `IMPLEMENTED` & `UNIT TESTED`: Token-based authentication using `PVEAPIToken={user}!{token_id}={token_secret}` headers (`_get_headers()`, line 61).
   - Operates entirely over standard HTTPS via `httpx.AsyncClient`.
3. **Privilege Set Derivation (PVE 9.x)**:
   - Evaluated directly against the implemented API calls:
     - `Sys.Audit`: For `GET /api2/json/nodes` and checking UPID task status (`GET /nodes/{node}/tasks/{upid}/status`).
     - `VM.Audit`: For `GET /api2/json/cluster/resources?type=vm` and `GET /nodes/{node}/qemu/{vmid}/status/current`.
     - `VM.Migrate`: For `POST /nodes/{node}/qemu/{vmid}/migrate`.
     - `VM.Allocate`: For registering VM state on the target node during relocation.
     - `Datastore.Audit`: For verifying storage status.
     - `Datastore.AllocateSpace`: For allocating disk blocks when migrating with local disks (`--with-local-disks 1`).
     - `VM.GuestAgent.Audit`: For guest-agent responsiveness checks (`GET .../qemu/{vmid}/agent/ping`).
   - *Removal of Invalid Privileges*: `VM.Monitor` has been excised from documentation as it is not a valid PVE 9 privilege.
4. **Two-Node Cluster Quorum & Resilience**:
   - A 2-node cluster functions normally when both nodes are online, but loses quorum if one node fails or disconnects (requires $\ge 2$ votes).
   - An external **QDevice** (`corosync-qnetd`) can be deployed to provide a 3rd vote for single-node failure resilience in a 2-node lab.
   - A 2-node cluster without a QDevice is strictly an experimental lab topology and must not be described as equivalent to a production 3+ node fault-tolerant HA architecture.
5. **Storage Flexibility**:
   - Both Shared Storage (NFS/Ceph) and Local Storage with Live Block Mirroring (`--with-local-disks 1`) are supported. Neither is an absolute architectural requirement.
6. **Real Infrastructure Verification Status**:
   - **`NOT VERIFIED`**: All 6 real-world operational aspects remain strictly unverified on physical hardware:
     - Real Proxmox hardware connectivity: **UNVERIFIED**
     - Real telemetry stream: **UNVERIFIED**
     - Real VM migration: **UNVERIFIED**
     - Real UPID execution: **UNVERIFIED**
     - Real placement verification: **UNVERIFIED**
     - Real guest-agent verification: **UNVERIFIED**

---

## 4. Deep Dive: `LibvirtKVMProvider` Readiness Status

The Libvirt provider (`backend/app/providers/libvirt.py`) is preserved as a future provider path:

1. **Native Dependency Friction**:
   - Requires native C libraries (`libvirt.so.0` on Linux, `libvirt.dll` on Windows).
   - On the Windows development machine, importing `libvirt` fails because Windows wheels are not available on PyPI without building from source against MinGW.
2. **Stubbed Live Operations**:
   - 8 out of 14 operational methods return empty lists, `None`, `False`, or raise `NotImplementedError`.
3. **Future Architectural Path**:
   - Instead of compiling libvirt on Windows, future Libvirt support should deploy a lightweight HTTP REST daemon (`vmotion-kvm-agent`) on the Linux hypervisors to expose an API identical to Proxmox.
