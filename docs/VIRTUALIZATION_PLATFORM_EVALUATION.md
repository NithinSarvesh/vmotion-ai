# VMotion AI — Virtualization Platform Evaluation & Technical Justification

This document provides a comparative technical evaluation of virtualization platforms for VMotion AI's live migration demonstration, justifying our provider architecture and external deployment path.

---

## 1. Candidate Comparison Matrix

| Evaluation Criterion | Proxmox VE (QEMU/KVM Cluster) | Libvirt / KVM (Linux Native) | VMware vSphere / ESXi | KubeVirt (Kubernetes) |
| :--- | :--- | :--- | :--- | :--- |
| **Real Live Migration Support** | **Excellent**: Native QEMU live migration over cluster network; supports shared storage (NFS/Ceph) or online storage replication (`pvesm / zfs`). | **Excellent**: Direct `virDomainMigrate3` / `qemu+tcp` or `qemu+ssh` memory streaming. | **Industry Benchmark**: VMware vMotion with vCenter Server coordination. | **Fair**: Containerized VM live migration via Virt-Launcher pod handoff. |
| **API Architecture & Quality** | **Native HTTP REST API**: Complete HTTP REST interface (`/api2/json`), standardized task tracking with UPID strings, declarative tokens (`PVEAPIToken`). | **C / RPC Socket**: Python bindings require `libvirt-python` compiled against native shared libraries, or custom SSH agent wrapper. | **Complex SOAP / REST**: `pyVmomi` requires heavy WSDL bindings or modern REST with strict session tokens. | **Kubernetes CRD API**: Ingress through `kube-apiserver` and subresources. |
| **Task Monitoring & Streaming** | **First-Class UPID System**: Every operation generates an immutable `UPID:node:pid:starttime:...` with a dedicated streaming log endpoint (`/tasks/{upid}/log`). | **Callback / Event Loop**: Requires registering native domain event callbacks or polling domain job info (`virDomainGetJobInfo`). | **vCenter Task Ref**: Polling task MOID until state is `success` or `error`. | **Pod Phase Polling**: Watching migration CRD phase (`Running`, `Succeeded`). |
| **Telemetry Ingest** | **High-Frequency Aggregates**: REST `/cluster/resources` and `/nodes/{node}/status` return CPU, RAM, and disk utilization in single round-trips. | **Low-Level Domain Stats**: Granular CPU cycle counters, memory balloon metrics, and block I/O per domain. | **vCenter Performance Counters**: Historical rollup intervals, high query overhead. | **Prometheus Exporters**: Requires Prometheus operator integration. |
| **Development & Setup Practicality** | **High**: Can run on any physical mini-PC / homelab server or single bare-metal VPS with nested VMs. Web GUI allows immediate visual confirmation. | **High**: Can run on any Ubuntu/Debian Linux server with standard `qemu-kvm` and `libvirt-daemon-system`. | **Low / Prohibitive**: Requires commercial licensing and strict hardware HCL compatibility. | **Moderate**: High memory and CPU overhead to run k8s control plane + worker nodes. |

---

## 2. Technical Justification & Selection

### Primary Recommendation: **Proxmox VE (Option A)**
1. **Separation of Control and Compute**: The Proxmox VE REST API v2 allows our Windows workstation to serve as the development and control workstation, sending authenticated HTTPS requests to a remote Proxmox server or cluster without installing hypervisor software on the Windows laptop.
2. **Deterministic Task Life Cycle (UPID)**: When `/nodes/{node}/qemu/{vmid}/migrate` is invoked, Proxmox VE immediately returns a unique process identifier (UPID). This enables VMotion AI to track the lifecycle from `PREPARING` $\rightarrow$ `MIGRATING` $\rightarrow$ `MONITORING` $\rightarrow$ `VERIFYING` against real hypervisor process logs.
3. **No Local Firmware Virtualization Required**: The local Windows machine had hardware virtualization disabled in firmware; Proxmox VE runs on remote hardware, preserving the host environment.

### Secondary Supported Platform: **Libvirt / KVM (Option B)**
For environments with standard Linux hosts without Proxmox installed, our `LibvirtKVMProvider` interface provides direct QEMU migration dispatch.

---

## 3. Disconnected Cluster Guard Architecture

In accordance with VMotion AI principles:
- The system **never silently substitutes mock data** when a live provider is selected.
- If `ProxmoxVEProvider` or `LibvirtKVMProvider` cannot reach the cluster endpoint (e.g. host offline, bad token, network partition), the backend returns:
  ```json
  {
    "is_live": true,
    "connected": false,
    "error_message": "LIVE CLUSTER DISCONNECTED: Unable to reach hypervisor endpoint"
  }
  ```
- The frontend prominently renders **`LIVE CLUSTER DISCONNECTED`** in red and blocks migration execution until connectivity is established and verified.
