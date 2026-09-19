# VMotion AI — 103-Dimensional Observation Space Specification

This document provides the mathematical specification, ordering, source telemetry, and normalization bounds for the **103-dimensional observation vector** ingested by the MaskablePPO decision engine and baseline heuristic.

---

## Dimension Breakdown

| Block | Category | Count | Dimension Range | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Block 1** | Node Telemetry | 24 | `[0 .. 23]` | 3 Compute Nodes $\times$ 8 features each |
| **Block 2** | Workload (VM) Telemetry | 60 | `[24 .. 83]` | 6 Virtual Machines $\times$ 10 features each |
| **Block 3** | Global Cluster & Fairness | 19 | `[84 .. 102]` | Entropy, Jain's Fairness, Power, SLA, Storage |
| **Total** | **Observation Vector** | **103** | `[0 .. 102]` | **Strict fixed-length vector** |

---

## Block 1: Node Telemetry Features (24 Features, Indices 0..23)

Iterates over 3 nodes in fixed deterministic order: `["node-01", "node-02", "node-03"]`.  
For each node $i \in \{0, 1, 2\}$:

| Index | Feature Key | Source Telemetry | Normalization Formula | Bounds | Handling of Missing Node |
| :--- | :--- | :--- | :--- | :--- | :--- |
| $8i + 0$ | `node_cpu_util` | `node.cpu_percent` | $\text{cpu\_percent} / 100.0$ | $[0.0, 1.0]$ | $0.0$ |
| $8i + 1$ | `node_ram_util` | `node.ram_percent` | $\text{ram\_percent} / 100.0$ | $[0.0, 1.0]$ | $0.0$ |
| $8i + 2$ | `node_net_rx` | `node.net_rx_kbps` | $\min(1.0, \text{rx\_kbps} / 100000.0)$ | $[0.0, 1.0]$ | $0.0$ |
| $8i + 3$ | `node_net_tx` | `node.net_tx_kbps` | $\min(1.0, \text{tx\_kbps} / 100000.0)$ | $[0.0, 1.0]$ | $0.0$ |
| $8i + 4$ | `node_disk_util`| `node.disk_used / disk_total` | $\text{disk\_used} / \max(1.0, \text{disk\_total})$ | $[0.0, 1.0]$ | $0.0$ |
| $8i + 5$ | `node_vm_density`| `len(node.active_vms)` | $\min(1.0, \|\text{active\_vms}\| / 10.0)$ | $[0.0, 1.0]$ | $0.0$ |
| $8i + 6$ | `node_status_flag`| `node.status` | $1.0 \text{ if online else } 0.0$ | $\{0.0, 1.0\}$ | $0.0$ |
| $8i + 7$ | `node_cpu_headroom`| Derived | $\max(0.0, 1.0 - \text{node\_cpu\_util})$ | $[0.0, 1.0]$ | $0.0$ |

---

## Block 2: Workload (VM) Telemetry Features (60 Features, Indices 24..83)

Iterates over 6 VMs in fixed alphanumeric sort order by `vmid`.  
For each VM $j \in \{0, 1, 2, 3, 4, 5\}$:

| Index | Feature Key | Source Telemetry | Normalization Formula | Bounds | Handling of Missing VM |
| :--- | :--- | :--- | :--- | :--- | :--- |
| $24 + 10j + 0$ | `vm_cpu_util` | `vm.cpu_percent` | $\text{cpu\_percent} / 100.0$ | $[0.0, 1.0]$ | $0.0$ |
| $24 + 10j + 1$ | `vm_ram_alloc` | `vm.ram_allocated_mb` | $\min(1.0, \text{ram\_alloc} / 65536.0)$ | $[0.0, 1.0]$ | $0.0$ |
| $24 + 10j + 2$ | `vm_ram_util` | `vm.ram_percent` | $\text{ram\_percent} / 100.0$ | $[0.0, 1.0]$ | $0.0$ |
| $24 + 10j + 3$ | `vm_net_io` | `vm.net_io_kbps` | $\min(1.0, \text{net\_io} / 50000.0)$ | $[0.0, 1.0]$ | $0.0$ |
| $24 + 10j + 4$ | `vm_sla_weight` | `vm.sla_priority` | $\text{critical}=1.0, \text{high}=0.75, \text{std}=0.5, \text{batch}=0.25$ | $[0.25, 1.0]$ | $0.0$ |
| $24 + 10j + 5$ | `vm_cooldown` | `vm.last_migrated_at` | $\max(0.0, \min(1.0, (60.0 - \Delta t) / 60.0))$ | $[0.0, 1.0]$ | $0.0$ |
| $24 + 10j + 6$ | `vm_mig_count` | `vm.migration_count` | $\min(1.0, \text{count} / 10.0)$ | $[0.0, 1.0]$ | $0.0$ |
| $24 + 10j + 7$ | `vm_uptime` | `vm.uptime_seconds` | $\min(1.0, \text{uptime} / 604800.0)$ | $[0.0, 1.0]$ | $0.0$ |
| $24 + 10j + 8$ | `vm_contention` | Host node CPU $\times$ VM CPU | $\text{host\_cpu\_util} \times \text{vm\_cpu\_util}$ | $[0.0, 1.0]$ | $0.0$ |
| $24 + 10j + 9$ | `vm_node_idx` | Host node ID in list | $0.0 \text{ for node-01}, 0.5 \text{ for node-02}, 1.0 \text{ for node-03}$ | $[-1.0, 1.0]$ | $-1.0$ |

---

## Block 3: Global Cluster, Power & Fairness Features (19 Features, Indices 84..102)

| Index | Feature Key | Mathematical Definition | Bounds | Description |
| :--- | :--- | :--- | :--- | :--- |
| **84** | `cluster_cpu_std` | $\sigma(\text{cpu\_utils}) = \sqrt{\frac{1}{N}\sum (\text{cpu}_i - \mu)^2}$ | $[0.0, 1.0]$ | Cluster compute imbalance standard deviation |
| **85** | `jains_fairness_cpu`| $\frac{(\sum \text{cpu}_i)^2}{N \sum \text{cpu}_i^2}$ | $[0.0, 1.0]$ | Jain's fairness index across compute hosts |
| **86** | `jains_fairness_ram`| $\frac{(\sum \text{ram}_i)^2}{N \sum \text{ram}_i^2}$ | $[0.0, 1.0]$ | Jain's fairness index across memory pools |
| **87** | `avg_cluster_cpu` | $\frac{1}{N} \sum \text{cpu}_i$ | $[0.0, 1.0]$ | Mean CPU utilization across cluster |
| **88** | `avg_cluster_ram` | $\frac{1}{N} \sum \text{ram}_i$ | $[0.0, 1.0]$ | Mean RAM utilization across cluster |
| **89** | `cluster_power_idx`| $\frac{1}{N} \sum (0.10 + 0.90 \cdot \text{cpu}_i^2)$ | $[0.1, 1.0]$ | Quadratic server dynamic power curve model |
| **90** | `cluster_vm_density`| $\|\text{vms}\| / 20.0$ | $[0.0, 1.0]$ | Workload packaging density |
| **91** | `active_mig_ratio` | $\text{migrating\_vms} / \max(1, \|\text{vms}\|)$ | $[0.0, 1.0]$ | Proportion of workloads in transient state |
| **92** | `sla_breach_ratio` | $\text{breached\_vms} / \max(1, \|\text{vms}\|)$ | $[0.0, 1.0]$ | Proportion of workloads violating SLA ceilings |
| **93** | `overload_penalty` | $1.0 \text{ if any}(\text{cpu}_i > 0.85) \text{ else } 0.0$ | $\{0.0, 1.0\}$ | Binary cluster contention threshold trigger |
| **94** | `node01_ram_headroom`| $(\text{ram\_total}_1 - \text{ram\_used}_1) / \text{ram\_total}_1$ | $[0.0, 1.0]$ | Memory availability on Node 01 |
| **95** | `node02_ram_headroom`| $(\text{ram\_total}_2 - \text{ram\_used}_2) / \text{ram\_total}_2$ | $[0.0, 1.0]$ | Memory availability on Node 02 |
| **96** | `node03_ram_headroom`| $(\text{ram\_total}_3 - \text{ram\_used}_3) / \text{ram\_total}_3$ | $[0.0, 1.0]$ | Memory availability on Node 03 |
| **97** | `cluster_net_sat` | $\sum (\text{rx}_i + \text{tx}_i) / (3 \times 100000.0)$ | $[0.0, 1.0]$ | Overall cluster network saturation |
| **98** | `cluster_disk_util`| $\sum \text{disk\_used}_i / \sum \text{disk\_total}_i$ | $[0.0, 1.0]$ | Aggregate datastore utilization |
| **99** | `quorum_healthy` | $1.0 \text{ if all nodes in quorum else } 0.0$ | $\{0.0, 1.0\}$ | Hypervisor cluster quorum consensus |
| **100**| `shared_storage_ok`| $1.0 \text{ if shared datastore accessible else } 0.0$ | $\{0.0, 1.0\}$ | Storage live-migration capability |
| **101**| `mig_usefulness` | $\max(0.0, \text{cpu\_max} - \text{cpu\_min} - 0.15)$ | $[0.0, 1.0]$ | Rebalancing dividend heuristic |
| **102**| `time_phase_idx` | $(\sin(t / 60.0) + 1.0) / 2.0$ | $[0.0, 1.0]$ | Temporal cyclical phase signal |
