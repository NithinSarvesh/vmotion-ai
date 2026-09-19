"""
Telemetry Engine for VMotion AI.
Collects, normalizes, and maintains rolling buffers of infrastructure telemetry.
Provides the single source of truth for backend AI reasoning, safety gates, and frontend display.
"""
import time
from collections import deque
from typing import Dict, List, Optional, Tuple
import numpy as np
from pydantic import BaseModel, Field

from app.providers.base import (
    BaseVirtualizationProvider,
    ClusterState,
    NodeTelemetry,
    VMTelemetry
)


class MetricHistoryPoint(BaseModel):
    timestamp: float
    value: float


class NodeTelemetryProfile(BaseModel):
    node_id: str
    current_cpu_percent: float
    cpu_moving_avg: float
    cpu_trend: str  # "rising" | "falling" | "stable"
    current_ram_percent: float
    ram_available_mb: float
    net_throughput_kbps: float
    hosted_vm_count: int
    cpu_history: List[MetricHistoryPoint] = Field(default_factory=list)


class VMTelemetryProfile(BaseModel):
    vm_id: str
    name: str
    node_id: str
    status: str
    current_cpu_percent: float
    cpu_moving_avg: float
    ram_allocated_mb: float
    ram_used_mb: float
    sla_priority: str
    sla_max_cpu_percent: float
    is_sla_breached: bool
    sla_breach_count: int
    last_migrated_at: Optional[float] = None
    migration_count: int
    cpu_history: List[MetricHistoryPoint] = Field(default_factory=list)


class AggregatedClusterTelemetry(BaseModel):
    timestamp: float
    provider_name: str
    is_live: bool
    connected: bool
    total_cpu_cores: int
    avg_cluster_cpu_percent: float
    cluster_cpu_imbalance_std: float
    jains_fairness_cpu: float
    total_ram_total_gb: float
    total_ram_used_gb: float
    active_vm_count: int
    migrating_vm_count: int
    total_sla_breaches: int
    node_profiles: Dict[str, NodeTelemetryProfile]
    vm_profiles: Dict[str, VMTelemetryProfile]


class TelemetryEngine:
    def __init__(self, provider: BaseVirtualizationProvider, max_history_points: int = 30):
        self.provider = provider
        self.max_history_points = max_history_points
        self._node_cpu_buffers: Dict[str, deque] = {}
        self._vm_cpu_buffers: Dict[str, deque] = {}
        self._vm_sla_breach_counts: Dict[str, int] = {}
        self.latest_cluster: Optional[ClusterState] = None
        self.latest_aggregated: Optional[AggregatedClusterTelemetry] = None

    async def sample_pulse(self) -> Tuple[ClusterState, AggregatedClusterTelemetry]:
        """
        Authoritative sampling step: collects provider telemetry once, computes
        aggregated moving averages and trends, and caches state so that AI and UI
        consistently observe the identical cluster snapshot.
        """
        cluster = await self.provider.collect_telemetry()
        now = cluster.timestamp or time.time()

        node_profiles: Dict[str, NodeTelemetryProfile] = {}
        vm_profiles: Dict[str, VMTelemetryProfile] = {}

        total_cores = 0
        cpu_percentages = []
        ram_totals = 0.0
        ram_useds = 0.0

        for nid, node in cluster.nodes.items():
            if nid not in self._node_cpu_buffers:
                self._node_cpu_buffers[nid] = deque(maxlen=self.max_history_points)
            self._node_cpu_buffers[nid].append((now, node.cpu_percent))

            buffer_vals = [val for _, val in self._node_cpu_buffers[nid]]
            moving_avg = float(np.mean(buffer_vals)) if buffer_vals else node.cpu_percent
            
            # Trend calculation
            if len(buffer_vals) >= 4:
                recent_delta = buffer_vals[-1] - buffer_vals[-4]
                if recent_delta > 2.0:
                    trend = "rising"
                elif recent_delta < -2.0:
                    trend = "falling"
                else:
                    trend = "stable"
            else:
                trend = "stable"

            total_cores += node.cpu_cores
            cpu_percentages.append(node.cpu_percent)
            ram_totals += node.ram_total_mb
            ram_useds += node.ram_used_mb

            node_profiles[nid] = NodeTelemetryProfile(
                node_id=nid,
                current_cpu_percent=round(node.cpu_percent, 1),
                cpu_moving_avg=round(moving_avg, 1),
                cpu_trend=trend,
                current_ram_percent=round(node.ram_percent, 1),
                ram_available_mb=round(max(0.0, node.ram_total_mb - node.ram_used_mb), 0),
                net_throughput_kbps=round(node.net_rx_kbps + node.net_tx_kbps, 1),
                hosted_vm_count=len(node.active_vms),
                cpu_history=[MetricHistoryPoint(timestamp=t, value=v) for t, v in self._node_cpu_buffers[nid]]
            )

        total_breaches = 0
        active_vms = 0
        migrating_vms = 0

        for vmid, vm in cluster.vms.items():
            if vmid not in self._vm_cpu_buffers:
                self._vm_cpu_buffers[vmid] = deque(maxlen=self.max_history_points)
            self._vm_cpu_buffers[vmid].append((now, vm.cpu_percent))

            buffer_vals = [val for _, val in self._vm_cpu_buffers[vmid]]
            moving_avg = float(np.mean(buffer_vals)) if buffer_vals else vm.cpu_percent

            is_breached = vm.cpu_percent > vm.sla_max_cpu_percent
            if is_breached:
                self._vm_sla_breach_counts[vmid] = self._vm_sla_breach_counts.get(vmid, 0) + 1
                total_breaches += 1

            if vm.status == "running":
                active_vms += 1
            elif vm.status == "migrating":
                migrating_vms += 1

            vm_profiles[vmid] = VMTelemetryProfile(
                vm_id=vmid,
                name=vm.name,
                node_id=vm.node_id,
                status=vm.status,
                current_cpu_percent=round(vm.cpu_percent, 1),
                cpu_moving_avg=round(moving_avg, 1),
                ram_allocated_mb=vm.ram_allocated_mb,
                ram_used_mb=vm.ram_used_mb,
                sla_priority=vm.sla_priority,
                sla_max_cpu_percent=vm.sla_max_cpu_percent,
                is_sla_breached=is_breached,
                sla_breach_count=self._vm_sla_breach_counts.get(vmid, 0),
                last_migrated_at=vm.last_migrated_at,
                migration_count=vm.migration_count,
                cpu_history=[MetricHistoryPoint(timestamp=t, value=v) for t, v in self._vm_cpu_buffers[vmid]]
            )

        # Global cluster stats
        cpu_arr = np.array(cpu_percentages) if cpu_percentages else np.array([0.0])
        avg_cpu = float(np.mean(cpu_arr))
        imbalance_std = float(np.std(cpu_arr))

        # Jain's fairness index: (sum(x))^2 / (n * sum(x^2))
        sum_x = np.sum(cpu_arr)
        sum_sq = np.sum(cpu_arr ** 2)
        jains = float((sum_x ** 2) / (len(cpu_arr) * sum_sq)) if sum_sq > 0 else 1.0

        agg = AggregatedClusterTelemetry(
            timestamp=now,
            provider_name=cluster.provider_name,
            is_live=cluster.is_live,
            connected=cluster.connected,
            total_cpu_cores=total_cores,
            avg_cluster_cpu_percent=round(avg_cpu, 1),
            cluster_cpu_imbalance_std=round(imbalance_std, 2),
            jains_fairness_cpu=round(jains, 4),
            total_ram_total_gb=round(ram_totals / 1024.0, 1),
            total_ram_used_gb=round(ram_useds / 1024.0, 1),
            active_vm_count=active_vms,
            migrating_vm_count=migrating_vms,
            total_sla_breaches=total_breaches,
            node_profiles=node_profiles,
            vm_profiles=vm_profiles
        )

        self.latest_cluster = cluster
        self.latest_aggregated = agg
        return cluster, agg

    async def sample_telemetry(self) -> AggregatedClusterTelemetry:
        """Backward-compatible helper returning solely the aggregated telemetry."""
        _, agg = await self.sample_pulse()
        return agg

    async def get_cluster_state(self, force_refresh: bool = False) -> ClusterState:
        """Returns the authoritative cluster state snapshot."""
        if self.latest_cluster is None or force_refresh:
            cluster, _ = await self.sample_pulse()
            return cluster
        return self.latest_cluster

    async def get_aggregated_telemetry(self, force_refresh: bool = False) -> AggregatedClusterTelemetry:
        """Returns the authoritative aggregated telemetry snapshot."""
        if self.latest_aggregated is None or force_refresh:
            _, agg = await self.sample_pulse()
            return agg
        return self.latest_aggregated
