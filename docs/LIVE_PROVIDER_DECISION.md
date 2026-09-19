# VMotion AI — Live Virtualization Provider Decision Document

This document provides a factual, comparative evaluation of live virtualization platforms to determine the authoritative path for connecting VMotion AI to genuine hypervisor infrastructure.

---

## 1. Candidate Virtualization Platforms

We evaluate four primary candidate architectures:
1. **Proxmox Virtual Environment (Proxmox VE)**: Debian-based open-source enterprise hypervisor cluster bundling QEMU/KVM, Linux containers (LXC), Corosync cluster clustering, and a native REST API.
2. **Linux Native KVM / Libvirt**: Standard Linux distribution (Ubuntu/Debian) running `qemu-kvm` and `libvirtd`, controlled via RPC sockets, libvirt C bindings, or SSH.
3. **VMware vSphere (ESXi + vCenter)**: Commercial enterprise hypervisor managed via vCenter Server and the VMware vSphere Web Services API.
4. **KubeVirt (Kubernetes Virtualization)**: Cloud-native virtualization addon extending Kubernetes to schedule and manage QEMU/KVM virtual machines alongside containers.

---

## 2. Comparative Evaluation Matrix

| Technical Domain | Proxmox VE | Linux Native KVM / Libvirt | VMware vSphere | KubeVirt |
| :--- | :--- | :--- | :--- | :--- |
| **DISCOVERY** | Native HTTP REST: `GET /api2/json/nodes` enumerates all clustered hosts; `GET /cluster/resources?type=vm` enumerates all cluster VMs in a single request. | Local/RPC Socket: Requires enumerating domains across separate host connection handles (`virConnectListAllDomains`). | REST / SOAP: Requires vCenter session and `ContainerView` object traversal for hosts and VMs. | Kubernetes API: `kubectl get vmi -A` via `kube-apiserver` subresources. |
| **TELEMETRY** | Built-in aggregated RRD metrics: Real-time CPU %, RAM total/used, network I/O, and disk load available via REST endpoint without external daemons. | Granular per-domain counters (`virDomainGetCPUStats`, `virDomainMemoryStats`); no unified cluster aggregate without deploying Prometheus/Collectd. | Built-in Performance Manager: Historical rollup intervals and counter queries via vCenter API. | Prometheus Metrics: Requires Prometheus Operator and `kube-state-metrics` integration. |
| **VM STATE** | Instant query via `GET /nodes/{node}/qemu/{vmid}/status/current` returning run status, PID, uptime, memory, CPU, and QEMU lock state. | Query via `virDomainGetState` and `virDomainGetInfo` per individual domain handle. | Managed Object Reference (MoRef) inspection via PropertyCollector. | Status subresource on `VirtualMachineInstance` (`Running`, `Scheduling`, `Paused`). |
| **VALIDATION** | Central cluster validates quorum status (`/cluster/status`), destination host existence, shared storage attachment, and VM locking. | Custom validation required: Control plane must manually check network reachability, disk path existence, and remote storage pool state. | vCenter DRS engine automatically validates compatibility, networks, and datastores. | KubeVirt admission webhooks validate PVC attachment, CPU topology, and node selector. |
| **MIGRATION** | Dedicated endpoint: `POST /nodes/{node}/qemu/{vmid}/migrate` with parameters `target`, `online=1`, and `with-local-disks=1`. Supports live pre-copy with shared or replicated storage. | `virDomainMigrate3` or `virDomainMigrateToURI3` with flags `VIR_MIGRATE_LIVE \| VIR_MIGRATE_PEER2PEER`. Requires direct host-to-host TCP stream. | `VirtualMachine.RelocateVM_Task` via vCenter triggering proprietary vMotion. | `VirtualMachineInstanceMigration` custom resource creation triggering virt-handler handoff. |
| **TASK MONITORING** | **First-class UPID system**: Every migration yields a Unique Process ID (`UPID:node:pid:starttime:...`). Real-time progress and logs are streamed via `GET /nodes/{node}/tasks/{upid}/status`. | Callback / Polling: Requires polling `virDomainGetJobInfo` / `virDomainGetJobStats` over active libvirt handle. | Task MoRef polling: Inspecting task `info.state` (`running`, `success`, `error`) and `info.progress`. | Watching status of the `VirtualMachineInstanceMigration` object. |
| **PLACEMENT VERIFICATION** | Instant cluster inventory update: Post-migration, the VM's assigned node updates across the cluster resource table and on the destination node endpoint. | Requires querying destination host libvirt handle with `virDomainLookupByName` to confirm active domain presence. | vCenter inventory reflects new host placement immediately upon task completion. | `vmi.status.nodeName` reflects target Kubernetes node. |
| **HEALTH VERIFICATION** | Built-in QEMU Guest Agent integration (`/nodes/{node}/qemu/{vmid}/agent/ping` and `/agent/info`) confirming guest kernel responsiveness. | `virDomainQemuAgentCommand` issuing `{"execute":"guest-ping"}` over QEMU guest channel. | VMware Tools status query (`guest.toolsStatus == "toolsOk"`). | KubeVirt readiness/liveness probes querying guest agent or TCP socket. |
| **SECURITY** | Standard TLS (port 8006). Scoped API tokens (`PVEAPIToken=user@realm!tokenid=secret`). No plain root password or SSH keys required by the control plane. | Requires SSH private key deployment (`qemu+ssh://`) or TLS client certificate management with SASL authentication. | User credentials or OAuth tokens against vCenter Single Sign-On (SSO). | Kubernetes RBAC service account tokens with scoped CRD permissions. |
| **NETWORKING** | Standard bridged networking (`vmbr0`). Migration stream uses TCP 60000–60050 directly between nodes; API uses HTTPS 8006. | Standard bridged networking (`br0`). Migration stream uses TCP 49152–49215 between nodes; control uses SSH (22) or TCP (16509). | Dedicated vMotion VMkernel port group; control uses HTTPS 443. | Overlay network (Calico, Cilium) with dedicated migration network secondary interface. |
| **STORAGE** | Supports shared NFS, iSCSI, Ceph, OR live block migration of local disks (`with-local-disks=1`) via QEMU NBD streaming. | Requires shared NFS/iSCSI directory mounted at identical paths on both nodes, or explicit non-shared block copy (`VIR_MIGRATE_NON_SHARED_DISK`). | Requires shared VMFS datastore (FC, iSCSI) or vSAN for standard live vMotion. | Requires shared ReadWriteMany (RWX) Persistent Volume or storage migration. |
| **SETUP COMPLEXITY** | **Low–Moderate**: ISO or Debian 12 package install (`apt install proxmox-ve`). Immediate Web GUI and API available out of the box. Single or multi-node. | **Moderate**: Requires manual installation of `qemu-kvm`, `libvirt-daemon-system`, SSH key exchanges, NFS exports, and AppArmor tuning. | **High / Prohibitive**: Requires commercial licensing, dedicated vCenter Server VM, and strict hardware HCL compatibility. | **High**: Requires full multi-node Kubernetes cluster + Container Runtime + KubeVirt Operator + CDI. |
| **WINDOWS CONTROL PLANE INTEGRATION** | **Seamless**: Communicates over standard HTTPS REST using Python `httpx`. Requires zero native OS libraries or compile steps on Windows. | **High Friction**: Python `libvirt` bindings require native C libraries (`libvirt.dll`) not bundled on Windows PyPI. Requires Linux host or WSL2 bridge. | High friction: Heavy `pyVmomi` dependency and WSDL schema parsing. | Moderate: `kubernetes` Python client works over HTTPS, but setup overhead of underlying k8s is massive. |
| **VMOTION AI IMPLEMENTATION STATUS** | **100% Code-Complete**: Implemented in `backend/app/providers/proxmox.py` (442 lines), unit-tested in `test_provider_contracts.py`. | **Stubbed**: 8 of 14 operational methods in `backend/app/providers/libvirt.py` return empty lists or raise `NotImplementedError`. | Not implemented. | Not implemented. |

---

## 3. Decision & Technical Justification

### Primary Live Provider: **Proxmox VE**

The factual comparison establishes **Proxmox VE** as the optimal real-infrastructure hypervisor for VMotion AI based on four concrete engineering realities:

1. **Clean Architectural Separation (Control Plane vs. Hypervisor)**:
   - VMotion AI runs on the development Windows workstation.
   - Proxmox VE exposes an HTTP REST API v2 over port 8006.
   - VMotion AI controls the cluster using standard HTTPS requests via `httpx`, completely decoupling the Windows control plane from hypervisor kernel modules.
2. **First-Class Asynchronous Task Tracking (UPID)**:
   - When migration is dispatched, Proxmox VE returns a deterministic UPID string.
   - The VMotion AI state machine (`PREPARING` $\to$ `MIGRATING` $\to$ `MONITORING` $\to$ `VERIFYING`) maps directly to Proxmox's native task status transitions and log output.
3. **Storage Flexibility**:
   - Proxmox VE natively supports live migration with shared storage (NFS) AND live block migration without shared storage (`with-local-disks=1` using QEMU NBD mirroring). This drastically simplifies laboratory infrastructure requirements.
4. **Implementation Maturity**:
   - The `ProxmoxVEProvider` is already 100% written, schema-aligned, and unit-tested in the VMotion AI codebase.

### Secondary / Future Alternative: **Linux KVM / Libvirt (via Remote REST Agent)**

Linux KVM remains an attractive hypervisor, but direct integration from a Windows control machine is obstructed by the absence of native Windows `libvirt-python` wheels. 

If KVM is pursued in the future, the architectural path must **NOT** attempt compiling native libvirt C libraries on Windows. Instead:
- Deploy a lightweight REST/FastAPI agent on the Linux KVM host (`vmotion-kvm-agent`).
- Have VMotion AI communicate with the KVM agent over HTTPS, mirroring the Proxmox provider design.
