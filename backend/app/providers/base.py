"""
Abstract Virtualization Provider Definition for VMotion AI.
Defines the unified interface for hypervisor and cluster interactions.
Supports Live (Proxmox, Libvirt) and Simulation modes without coupling.
"""
from abc import ABC, abstractmethod
from typing import Optional, Literal
from pydantic import BaseModel, Field


class NodeTelemetry(BaseModel):
    id: str
    name: str
    status: Literal["online", "offline", "degraded"] = "online"
    cpu_cores: int = 16
    cpu_percent: float = Field(0.0, ge=0.0, le=100.0)
    ram_total_mb: float = 65536.0
    ram_used_mb: float = 16384.0
    ram_percent: float = Field(0.0, ge=0.0, le=100.0)
    net_rx_kbps: float = 0.0
    net_tx_kbps: float = 0.0
    disk_total_gb: float = 1000.0
    disk_used_gb: float = 350.0
    shared_storage_accessible: bool = True
    quorum_healthy: bool = True
    quorum_status: Literal["HEALTHY", "UNHEALTHY", "UNKNOWN"] = "HEALTHY"
    storage_status: Literal["HEALTHY", "UNHEALTHY", "UNKNOWN"] = "HEALTHY"
    active_vms: list[str] = Field(default_factory=list)


class VMTelemetry(BaseModel):
    vmid: str
    name: str
    node_id: str
    status: Literal["running", "stopped", "paused", "migrating"] = "running"
    cpu_cores: int = 4
    cpu_percent: float = Field(0.0, ge=0.0, le=100.0)
    ram_allocated_mb: float = 8192.0
    ram_used_mb: float = 4096.0
    ram_percent: float = Field(0.0, ge=0.0, le=100.0)
    net_io_kbps: float = 120.0
    disk_allocated_gb: float = 50.0
    sla_priority: Literal["critical", "high", "standard", "batch"] = "standard"
    sla_max_cpu_percent: float = 80.0
    last_migrated_at: Optional[float] = None
    migration_count: int = 0
    uptime_seconds: int = 3600


class ClusterState(BaseModel):
    is_live: bool = False
    connected: bool = True
    provider_name: str = "simulation"
    timestamp: float = 0.0
    nodes: dict[str, NodeTelemetry] = Field(default_factory=dict)
    vms: dict[str, VMTelemetry] = Field(default_factory=dict)
    error_message: Optional[str] = None


class MigrationPlan(BaseModel):
    plan_id: str
    vm_id: str
    source_node: str
    target_node: str
    reason: str
    created_at: float
    estimated_duration_seconds: float = 12.0
    recommended_by: Literal["AI_PPO", "BASELINE_RULE", "MANUAL"] = "AI_PPO"
    with_local_disks: bool = True


MigrationState = Literal[
    "PREPARING",
    "VALIDATING",
    "MIGRATING",
    "MONITORING",
    "VERIFYING",
    "VERIFIED",
    "FAILED",
    "BLOCKED"
]


class MigrationTaskStatus(BaseModel):
    task_id: str
    plan_id: str
    vm_id: str
    source_node: str
    target_node: str
    state: MigrationState = "PREPARING"
    progress_percent: float = 0.0
    started_at: float = 0.0
    updated_at: float = 0.0
    completed_at: Optional[float] = None
    verified_at: Optional[float] = None
    error: Optional[str] = None
    verification_details: Optional[dict] = None


class ProviderConnectionResult(BaseModel):
    provider: Literal["simulation", "proxmox", "libvirt"]
    status: Literal["CONNECTED", "AUTHENTICATION_ERROR", "DISCONNECTED", "UNAVAILABLE"]
    latency_ms: Optional[float] = None
    hypervisor_version: Optional[str] = None
    node_count: int = 0
    vm_count: int = 0
    message: str
    details: Optional[dict] = None


class BaseVirtualizationProvider(ABC):
    """
    Unified contract for all infrastructure backends.
    All real and simulated hypervisors must adhere to this interface.
    """

    @abstractmethod
    async def test_connection(self) -> ProviderConnectionResult:
        """Run diagnostic health check and return structured status."""
        pass

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection / session to cluster API."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Tear down connection."""
        pass

    @abstractmethod
    async def is_connected(self) -> bool:
        """Check whether infrastructure is reachable."""
        pass

    @abstractmethod
    async def discover_nodes(self) -> list[NodeTelemetry]:
        """Discover and return all compute nodes in the cluster."""
        pass

    @abstractmethod
    async def discover_vms(self) -> list[VMTelemetry]:
        """Discover and return all virtual machines in the cluster."""
        pass

    @abstractmethod
    async def collect_telemetry(self) -> ClusterState:
        """Retrieve aggregated cluster snapshot and normalized telemetry."""
        pass

    async def get_cluster_state(self) -> ClusterState:
        """Alias for collect_telemetry for backwards compatibility."""
        return await self.collect_telemetry()

    @abstractmethod
    async def inspect_vm_state(self, vm_id: str) -> Optional[VMTelemetry]:
        """Inspect detailed operational state of a single virtual machine."""
        pass

    @abstractmethod
    async def validate_migration(self, vm_id: str, target_node: str) -> tuple[bool, str]:
        """Check hypervisor-level preconditions prior to execution."""
        pass

    @abstractmethod
    async def plan_migration(self, vm_id: str, target_node: str, reason: str = "Rebalance") -> MigrationPlan:
        """Generate a formal MigrationPlan for a given workload and destination."""
        pass

    @abstractmethod
    async def execute_migration(self, plan: MigrationPlan) -> str:
        """Initiate asynchronous live migration and return task/job identifier."""
        pass

    @abstractmethod
    async def monitor_migration_task(self, task_id: str) -> MigrationTaskStatus:
        """Poll the ongoing migration task status directly from hypervisor."""
        pass

    async def monitor_task(self, task_id: str) -> MigrationTaskStatus:
        """Alias for monitor_migration_task."""
        return await self.monitor_migration_task(task_id)

    @abstractmethod
    async def verify_placement(self, vm_id: str, expected_node: str) -> tuple[bool, str]:
        """Query physical host placement to confirm workload resides on expected node."""
        pass

    @abstractmethod
    async def verify_vm_health(self, vm_id: str) -> tuple[bool, str]:
        """Verify workload post-migration health and responsiveness."""
        pass

    async def verify_migration(self, vm_id: str, expected_node: str) -> tuple[bool, str]:
        """Combined verification of placement and health."""
        p_ok, p_msg = await self.verify_placement(vm_id, expected_node)
        if not p_ok:
            return False, p_msg
        h_ok, h_msg = await self.verify_vm_health(vm_id)
        if not h_ok:
            return False, h_msg
        return True, f"Placement on '{expected_node}' and workload health verified."
