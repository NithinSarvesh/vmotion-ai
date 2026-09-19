"""
Libvirt / Linux KVM Virtualization Provider for VMotion AI.
Directly interfaces with QEMU/KVM hypervisors via Libvirt remote URIs (e.g. qemu+ssh:// or qemu+tcp://).
"""
import time
from typing import Optional
from app.providers.base import (
    BaseVirtualizationProvider,
    NodeTelemetry,
    VMTelemetry,
    ClusterState,
    MigrationPlan,
    MigrationTaskStatus,
    ProviderConnectionResult
)
from app.config import settings


class LibvirtKVMProvider(BaseVirtualizationProvider):
    def __init__(self, uri: str = None):
        self.uri = uri if uri is not None else settings.LIBVIRT_URI
        self._connected = False
        self._connection_error = None
        self._conn = None

    def update_config(self, uri: Optional[str] = None):
        if uri is not None:
            self.uri = uri
        self._connected = False
        self._conn = None

    async def test_connection(self) -> ProviderConnectionResult:
        t0 = time.perf_counter()
        if not self.uri:
            return ProviderConnectionResult(
                provider="libvirt",
                status="UNAVAILABLE",
                latency_ms=None,
                node_count=0,
                vm_count=0,
                message="Libvirt connection URI is not configured."
            )

        try:
            import libvirt
        except ImportError:
            return ProviderConnectionResult(
                provider="libvirt",
                status="UNAVAILABLE",
                latency_ms=None,
                node_count=0,
                vm_count=0,
                message="libvirt-python bindings are not installed in the control plane environment (requires Linux host or native libvirt C libraries)."
            )

        try:
            conn = libvirt.open(self.uri)
            latency = round((time.perf_counter() - t0) * 1000.0, 2)
            if conn is None:
                return ProviderConnectionResult(
                    provider="libvirt",
                    status="DISCONNECTED",
                    latency_ms=latency,
                    node_count=0,
                    vm_count=0,
                    message=f"Failed to open connection to libvirt URI '{self.uri}'."
                )

            ver = conn.getVersion()
            lib_ver = conn.getLibVersion()
            hostname = conn.getHostname()
            num_vms = conn.numOfDomains()
            conn.close()

            return ProviderConnectionResult(
                provider="libvirt",
                status="CONNECTED",
                latency_ms=latency,
                hypervisor_version=f"Libvirt {lib_ver} / Hypervisor {ver} on {hostname}",
                node_count=1,
                vm_count=num_vms,
                message=f"Successfully connected to Libvirt daemon at '{self.uri}'."
            )
        except Exception as e:
            latency = round((time.perf_counter() - t0) * 1000.0, 2)
            err_str = str(e).lower()
            status = "AUTHENTICATION_ERROR" if ("auth" in err_str or "permission" in err_str or "denied" in err_str) else "DISCONNECTED"
            return ProviderConnectionResult(
                provider="libvirt",
                status=status,
                latency_ms=latency,
                node_count=0,
                vm_count=0,
                message=f"Libvirt connection failed: {str(e)}",
                details={"error": str(e)}
            )

    async def connect(self) -> bool:
        try:
            import libvirt
            self._conn = libvirt.open(self.uri)
            if self._conn:
                self._connected = True
                self._connection_error = None
                return True
        except ImportError:
            self._connected = False
            self._connection_error = "libvirt-python bindings are not installed in the environment."
            return False
        except Exception as e:
            self._connected = False
            self._connection_error = f"Libvirt connection failed to '{self.uri}': {str(e)}"
            return False

    async def disconnect(self) -> None:
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
        self._connected = False

    async def is_connected(self) -> bool:
        return self._connected

    async def discover_nodes(self) -> list[NodeTelemetry]:
        if not self._connected:
            return []
        return []

    async def discover_vms(self) -> list[VMTelemetry]:
        if not self._connected:
            return []
        return []

    async def collect_telemetry(self) -> ClusterState:
        is_conn = await self.is_connected()
        if not is_conn:
            is_conn = await self.connect()

        if not is_conn:
            return ClusterState(
                is_live=True,
                connected=False,
                provider_name="libvirt",
                timestamp=time.time(),
                nodes={},
                vms={},
                error_message=f"LIVE CLUSTER DISCONNECTED: {self._connection_error or 'Host unreachable'}"
            )

        return ClusterState(
            is_live=True,
            connected=True,
            provider_name="libvirt",
            timestamp=time.time(),
            nodes={},
            vms={}
        )

    async def inspect_vm_state(self, vm_id: str) -> Optional[VMTelemetry]:
        return None

    async def validate_migration(self, vm_id: str, target_node: str) -> tuple[bool, str]:
        return False, "Libvirt cluster validation not active."

    async def plan_migration(self, vm_id: str, target_node: str, reason: str = "Rebalance") -> MigrationPlan:
        return MigrationPlan(
            plan_id=f"plan-libvirt-{int(time.time())}",
            vm_id=vm_id,
            source_node="source",
            target_node=target_node,
            reason=reason,
            created_at=time.time()
        )

    async def execute_migration(self, plan: MigrationPlan) -> str:
        raise NotImplementedError("Libvirt live migration requires active libvirt daemon session.")

    async def monitor_migration_task(self, task_id: str) -> MigrationTaskStatus:
        raise NotImplementedError()

    async def verify_placement(self, vm_id: str, expected_node: str) -> tuple[bool, str]:
        return False, "Verification requires active libvirt connection."

    async def verify_vm_health(self, vm_id: str) -> tuple[bool, str]:
        return False, "Health verification requires active libvirt connection."
