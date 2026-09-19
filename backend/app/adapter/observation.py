"""
Observation / Feature Adapter for VMotion AI.
Transforms raw telemetry from ClusterState into the exact 103-dimensional feature vector
expected by the MaskablePPO / sb3-contrib reinforcement learning model.

Complies strictly with docs/OBSERVATION_SPEC_103.md.
"""
import numpy as np
import time
import math
from app.providers.base import ClusterState


class ObservationAdapter:
    def __init__(self, node_ids: list[str] = None, max_vms: int = 6):
        self._explicit_node_ids = node_ids
        self.node_ids = node_ids or ["node-01", "node-02", "node-03"]
        self.max_vms = max_vms
        self.cooldown_seconds = 60.0

    def get_effective_node_ids(self, cluster: ClusterState) -> list[str]:
        """Resolves up to 3 node identifiers deterministically from cluster state."""
        if self._explicit_node_ids:
            return self._explicit_node_ids[:3]
        if cluster.nodes:
            return sorted(cluster.nodes.keys())[:3]
        return self.node_ids[:3]

    def extract_features(self, cluster: ClusterState) -> np.ndarray:
        """
        Builds the 103-element normalized floating point vector.
        All values are strictly bounded in range [0.0, 1.0] (or [-1.0, 1.0] for node indices).
        Guarantees: No NaN, No Inf, deterministic indexing.
        """
        now = time.time()
        features = []
        effective_nodes = self.get_effective_node_ids(cluster)
        self.node_ids = effective_nodes

        # --- 1. Node Telemetry Features (Indices 0..23, 3 nodes * 8 features) ---
        node_cpus = []
        node_rams = []
        total_rx = 0.0
        total_tx = 0.0
        total_disk_used = 0.0
        total_disk_cap = 0.0
        quorum_all = True
        storage_all = True

        for i in range(3):
            nid = effective_nodes[i] if i < len(effective_nodes) else None
            node = cluster.nodes.get(nid) if nid else None
            if node:
                cpu_norm = float(np.clip(node.cpu_percent / 100.0, 0.0, 1.0))
                ram_norm = float(np.clip(node.ram_percent / 100.0, 0.0, 1.0))
                rx_norm = float(np.clip(node.net_rx_kbps / 100000.0, 0.0, 1.0))
                tx_norm = float(np.clip(node.net_tx_kbps / 100000.0, 0.0, 1.0))
                disk_norm = float(np.clip(node.disk_used_gb / max(1.0, node.disk_total_gb), 0.0, 1.0))
                vm_count_norm = float(np.clip(len(node.active_vms) / 10.0, 0.0, 1.0))
                status_flag = 1.0 if node.status == "online" else 0.0
                headroom = float(np.clip(1.0 - cpu_norm, 0.0, 1.0))

                node_cpus.append(cpu_norm)
                node_rams.append(ram_norm)
                total_rx += node.net_rx_kbps
                total_tx += node.net_tx_kbps
                total_disk_used += node.disk_used_gb
                total_disk_cap += node.disk_total_gb

                if not node.quorum_healthy:
                    quorum_all = False
                if not node.shared_storage_accessible:
                    storage_all = False

                features.extend([cpu_norm, ram_norm, rx_norm, tx_norm, disk_norm, vm_count_norm, status_flag, headroom])
            else:
                node_cpus.append(0.0)
                node_rams.append(0.0)
                features.extend([0.0] * 8)

        # --- 2. VM Telemetry Features (Indices 24..83, 6 VMs * 10 features) ---
        vms_sorted = sorted(cluster.vms.values(), key=lambda v: v.vmid)[:self.max_vms]
        sla_map = {"critical": 1.0, "high": 0.75, "standard": 0.5, "batch": 0.25}

        for i in range(self.max_vms):
            if i < len(vms_sorted):
                vm = vms_sorted[i]
                cpu_util = float(np.clip(vm.cpu_percent / 100.0, 0.0, 1.0))
                ram_alloc = float(np.clip(vm.ram_allocated_mb / 65536.0, 0.0, 1.0))
                ram_util = float(np.clip(vm.ram_percent / 100.0, 0.0, 1.0))
                net_io = float(np.clip(vm.net_io_kbps / 50000.0, 0.0, 1.0))
                sla_weight = sla_map.get(vm.sla_priority, 0.5)

                elapsed = (now - vm.last_migrated_at) if vm.last_migrated_at else 999.0
                cooldown_norm = float(np.clip((self.cooldown_seconds - elapsed) / self.cooldown_seconds, 0.0, 1.0))

                mig_count_norm = float(np.clip(vm.migration_count / 10.0, 0.0, 1.0))
                uptime_norm = float(np.clip(vm.uptime_seconds / 604800.0, 0.0, 1.0))

                hosted_node = cluster.nodes.get(vm.node_id)
                contention = float(np.clip((hosted_node.cpu_percent / 100.0) * cpu_util, 0.0, 1.0)) if hosted_node else 0.0

                if vm.node_id in effective_nodes:
                    node_idx = effective_nodes.index(vm.node_id) / 2.0
                else:
                    node_idx = -1.0

                features.extend([
                    cpu_util, ram_alloc, ram_util, net_io, sla_weight,
                    cooldown_norm, mig_count_norm, uptime_norm, contention, node_idx
                ])
            else:
                features.extend([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -1.0])

        # --- 3. Global Cluster, Power & Fairness Features (Indices 84..102, 19 features) ---
        cpu_arr = np.array(node_cpus) if node_cpus else np.array([0.0])
        ram_arr = np.array(node_rams) if node_rams else np.array([0.0])

        # Index 84: CPU load standard deviation
        load_std = float(np.std(cpu_arr))

        # Index 85 & 86: Jain's Fairness Indexes
        sum_cpu = np.sum(cpu_arr)
        sum_sq_cpu = np.sum(cpu_arr ** 2)
        jains_cpu = float((sum_cpu ** 2) / (len(cpu_arr) * sum_sq_cpu)) if sum_sq_cpu > 0 else 1.0

        sum_ram = np.sum(ram_arr)
        sum_sq_ram = np.sum(ram_arr ** 2)
        jains_ram = float((sum_ram ** 2) / (len(ram_arr) * sum_sq_ram)) if sum_sq_ram > 0 else 1.0

        # Index 87 & 88: Means
        avg_cluster_cpu = float(np.mean(cpu_arr))
        avg_cluster_ram = float(np.mean(ram_arr))

        # Index 89: Quadratic server power curve model
        cluster_energy = float(np.mean(0.10 + 0.90 * (cpu_arr ** 2)))

        # Index 90: VM density
        vm_density = float(np.clip(len(cluster.vms) / 20.0, 0.0, 1.0))

        # Index 91: Active migrating ratio
        migrating_count = sum(1 for v in cluster.vms.values() if v.status == "migrating")
        active_mig_ratio = float(migrating_count / max(1, len(cluster.vms)))

        # Index 92: SLA breach ratio
        breached_count = sum(1 for v in cluster.vms.values() if v.cpu_percent > v.sla_max_cpu_percent)
        sla_breach_ratio = float(breached_count / max(1, len(cluster.vms)))

        # Index 93: Overload penalty flag
        overload_flag = 1.0 if any(c > 0.85 for c in node_cpus) else 0.0

        # Indices 94, 95, 96: Node headroom ratios
        avail_rams = []
        for i in range(3):
            nid = effective_nodes[i] if i < len(effective_nodes) else None
            n = cluster.nodes.get(nid) if nid else None
            if n and n.ram_total_mb > 0:
                avail_rams.append(float(np.clip((n.ram_total_mb - n.ram_used_mb) / n.ram_total_mb, 0.0, 1.0)))
            else:
                avail_rams.append(0.0)

        # Index 97: Cluster network saturation
        net_sat = float(np.clip((total_rx + total_tx) / 300000.0, 0.0, 1.0))

        # Index 98: Cluster disk capacity utilization
        disk_sat = float(np.clip(total_disk_used / max(1.0, total_disk_cap), 0.0, 1.0))

        # Index 99: Quorum healthy flag
        quorum_flag = 1.0 if quorum_all else 0.0

        # Index 100: Shared storage accessible flag
        storage_flag = 1.0 if storage_all else 0.0

        # Index 101: Migration usefulness heuristic
        cpu_spread = float(np.max(cpu_arr) - np.min(cpu_arr))
        usefulness = float(np.clip(cpu_spread - 0.15, 0.0, 1.0))

        # Index 102: Temporal cyclical phase index
        t_phase = float((math.sin(now / 60.0) + 1.0) / 2.0)

        features.extend([
            load_std, jains_cpu, jains_ram, avg_cluster_cpu, avg_cluster_ram,
            cluster_energy, vm_density, active_mig_ratio, sla_breach_ratio, overload_flag,
            avail_rams[0], avail_rams[1], avail_rams[2],
            net_sat, disk_sat, quorum_flag, storage_flag, usefulness, t_phase
        ])

        arr = np.array(features, dtype=np.float32)
        assert len(arr) == 103, f"Expected exactly 103 observation features, got {len(arr)}"
        assert not np.isnan(arr).any(), "Observation vector contains NaN!"
        assert not np.isinf(arr).any(), "Observation vector contains Inf!"
        return arr
