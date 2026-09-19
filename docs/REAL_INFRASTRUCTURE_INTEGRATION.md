# VMotion AI — Real Infrastructure Integration Specification & Live Provider Readiness

> **System Status**: Engineering-Complete Prototype / Control-Plane Foundation  
> **Infrastructure Target**: Staging / Experimental Live Virtualization Environment  
> **Last Updated**: 2026-09-19  

---

## 1. Architectural Topology & Deployment Contract

VMotion AI operates as an external, out-of-band supervisory control plane. The software never interacts directly with underlying VM memory or hypervisor kernels; rather, it communicates exclusively via standardized provider interfaces.

```
+-------------------------------------------------------------------------+
|                  OPERATOR WORKSTATION / WEB CLIENT                      |
|                  (Interactive Topology, Safety Gate, Audit)             |
+-------------------------------------------------------------------------+
                                    │  HTTPS / WebSockets
                                    ▼
+-------------------------------------------------------------------------+
|                   VMOTION AI CONTROL PLANE BACKEND                      |
|  - Ingestion Engine (103 Features)     - PPO V5 Decision Engine         |
|  - Deterministic Safety Gate (8 Rules) - Migration Lifecycle FSM        |
|  - Telemetry Normalizer                - Append-Only Audit Ledger       |
+-------------------------------------------------------------------------+
                                    │
                                    ▼ Provider Abstraction Boundary
+-------------------------------------------------------------------------+
|                    VIRTUALIZATION PROVIDER ADAPTER                      |
|   ┌─────────────────────────────┐     ┌─────────────────────────────┐   |
|   │     ProxmoxVEProvider       │     │     LibvirtKVMProvider      │   |
|   │  (REST API v2 / HTTPS 8006) │     │  (QEMU+SSH 22 / RPC 16509)  │   |
|   └─────────────────────────────┘     └─────────────────────────────┘   |
+-------------------------------------------------------------------------+
                    │                                     │
                    ▼                                     ▼
+-------------------------------------+ +---------------------------------+
| REAL COMPUTE NODE A                 | | REAL COMPUTE NODE B             |
| - Hypervisor: PVE 8.x / Linux KVM   | | - Hypervisor: PVE 8.x / Linux   |
| - Bridge Interface: vmbr0 / br0     | | - Bridge Interface: vmbr0 / br0 |
| - Shared Storage: NFS / Ceph        | | - Shared Storage: NFS / Ceph    |
| - Active Workload: Linux Guest VM   | | - Target Host Capacity          |
+-------------------------------------+ +---------------------------------+
                    │                                     ▲
                    └─────── High-Speed Live Migration ───┘
                             (Memory Pre-Copy Stream)
```

---

## 2. Live Provider Capability & Readiness Matrix

Every live infrastructure operation is classified according to its empirical verification level:

| Capability | Proxmox VE Provider | Libvirt / KVM Provider | Description / Verification Status |
| :--- | :--- | :--- | :--- |
| **DISCOVERY** | **IMPLEMENTED** (Unit Tested) | **NOT VERIFIED** (Stubbed) | Enumeration of cluster compute nodes and VM inventory via hypervisor query APIs. |
| **TELEMETRY** | **IMPLEMENTED** (Unit Tested) | **NOT VERIFIED** (Stubbed) | Collection of CPU load, RAM allocation/utilization, network throughput, and disk storage. |
| **VM STATE** | **IMPLEMENTED** (Unit Tested) | **NOT VERIFIED** (Stubbed) | Detailed inspection of single guest state (running, stopped, paused, migrating, uptime). |
| **VALIDATION** | **IMPLEMENTED** (Unit Tested) | **IMPLEMENTED** (Unit Tested) | Pre-flight sanity checks (workload existence, distinct target, target host availability). |
| **PLANNING** | **IMPLEMENTED** (Unit Tested) | **IMPLEMENTED** (Unit Tested) | Generation of formal `MigrationPlan` schema with plan IDs and algorithmic rationales. |
| **EXECUTION** | **IMPLEMENTED** (Unit Tested) | **NOT IMPLEMENTED** | Dispatch of live migration job (POST to PVE migrate API returning UPID; `virDomainMigrate` RPC). |
| **TASK MONITORING** | **IMPLEMENTED** (Unit Tested) | **NOT IMPLEMENTED** | Asynchronous polling of migration task state until completion, failure, or timeout. |
| **PLACEMENT CHECK**| **IMPLEMENTED** (Unit Tested) | **NOT VERIFIED** (Stubbed) | Post-migration inventory query confirming workload actually resides on the target compute node. |
| **HEALTH CHECK** | **IMPLEMENTED** (Unit Tested) | **NOT VERIFIED** (Stubbed) | Post-migration verification that guest OS is operational and responsive. |

> [!WARNING]
> **Real Infrastructure Disclosure**: Neither Proxmox nor Libvirt has been tested against real physical hardware or live cloud VMs yet. All current test passing marks reflect contract adherence and unit/mock testing. Real hardware validation will be conducted during the dedicated live demonstration phase.

---

## 3. Real Data Contract Consistency

Both the `SimulationProvider` and live providers (`ProxmoxVEProvider`, `LibvirtKVMProvider`) output strictly identical normalized schemas:

- **`ClusterState`**:
  - `is_live`: `bool` (strictly `False` for simulation, `True` for live providers)
  - `connected`: `bool` (truthful connection indicator; never falls back silently)
  - `provider_name`: `Literal["simulation", "proxmox", "libvirt"]`
  - `nodes`: `Dict[str, NodeTelemetry]`
  - `vms`: `Dict[str, VMTelemetry]`
  - `error_message`: Optional error details when disconnected
- **`NodeTelemetry`**:
  - `id`, `name`, `status` (`online`, `offline`, `degraded`)
  - `cpu_cores`, `cpu_percent`, `ram_total_mb`, `ram_used_mb`, `ram_percent`
  - `net_rx_kbps`, `net_tx_kbps`, `disk_total_gb`, `disk_used_gb`
  - `shared_storage_accessible`, `quorum_healthy`, `active_vms`
- **`VMTelemetry`**:
  - `vmid`, `name`, `node_id`, `status` (`running`, `stopped`, `migrating`)
  - `cpu_cores`, `cpu_percent`, `ram_allocated_mb`, `ram_used_mb`, `ram_percent`
  - `sla_priority`, `sla_max_cpu_percent`, `last_migrated_at`, `uptime_seconds`
- **`MigrationTaskStatus`**:
  - `task_id`, `plan_id`, `vm_id`, `source_node`, `target_node`
  - `state` (`PREPARING`, `VALIDATING`, `MIGRATING`, `MONITORING`, `VERIFYING`, `VERIFIED`, `FAILED`, `BLOCKED`)
  - `progress_percent`, `started_at`, `completed_at`, `verified_at`, `verification_details`

---

## 4. Hardware, Network, and Port Requirements

### Proxmox VE Real Deployment
1. **Network Ports**:
   - `TCP 8006`: Proxmox VE Web GUI and REST API v2
   - `TCP 22`: Cluster inter-node SSH for storage synchronization
   - `TCP 60000-60050`: Live migration memory stream migration ports
2. **Authentication**:
   - API Token authentication via HTTP header:
     `Authorization: PVEAPIToken=USER@REALM!TOKENID=UUID_SECRET`
   - Permissions required: `VM.Migrate`, `VM.Audit`, `Sys.Audit`, `Datastore.Audit`
3. **Storage Prerequisites**:
   - Shared NFS export or Ceph RBD pool mounted with identical storage ID on all cluster nodes.
   - If local ZFS/LVM storage is used, `--with-local-disks 1` must be supported.

### Libvirt / KVM Real Deployment
1. **Network Ports**:
   - `TCP 22`: SSH tunnel transport (`qemu+ssh://root@node-ip/system`)
   - `TCP 16509`: Libvirt remote daemon (if TLS/TCP transport enabled)
   - `TCP 49152-49215`: QEMU live migration direct migration data ports
2. **Authentication**:
   - SSH Public Key authentication (passwordless root or sudoer with libvirt group membership)
   - Host key validation in `~/.ssh/known_hosts` on the control machine
3. **Prerequisites**:
   - Bridge interface configured (e.g. `br0` bridged to physical NIC)
   - Shared datastore path (e.g. `/var/lib/libvirt/images` NFS-mounted across all nodes)

---

## 5. Architectural Limitations & Scientific Boundaries

1. **Simulation vs Physical Hardware Fidelity**:
   - `SimulationProvider` uses mathematical load drift models. It does not measure physical PCI bus saturation, CPU cache thrashing during dirty page iteration, or physical top-of-rack network switch buffer drops.
2. **Topology Scope**:
   - The current 103-feature observation contract is structured for clusters of up to 3 compute nodes and 6 virtual machines. Larger enterprise topologies will require hierarchical or attention-based state embeddings.
3. **Control-Plane Locking**:
   - Migration locks and cooldowns are currently maintained in backend application memory. They do not yet integrate with a hypervisor-native Distributed Lock Manager (DLM) such as `corosync-dlm`.
4. **Validation Scope**:
   - While 67 backend tests pass and 10 safety invariants are verified, real-world hypervisor live migration has not yet been executed on physical or cloud nested hardware.
