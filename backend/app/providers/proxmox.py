"""
Proxmox VE Virtualization Provider for VMotion AI.
Directly interfaces with Proxmox VE REST API v2 using API tokens.
Supports real cluster discovery, live VM migration dispatch, UPID streaming, and post-migration placement verification.
"""
import time
import httpx
from typing import Optional
from app.providers.base import (
    BaseVirtualizationProvider,
    NodeTelemetry,
    VMTelemetry,
    ClusterState,
    MigrationPlan,
    MigrationTaskStatus,
    MigrationState,
    ProviderConnectionResult
)
from app.config import settings


class ProxmoxVEProvider(BaseVirtualizationProvider):
    def __init__(
        self,
        endpoint: str = None,
        user: str = None,
        token_id: str = None,
        token_secret: str = None,
        verify_ssl: bool = False
    ):
        self.endpoint = (endpoint if endpoint is not None else settings.PROXMOX_ENDPOINT).rstrip('/')
        self.user = user if user is not None else settings.PROXMOX_USER
        self.token_id = token_id if token_id is not None else settings.PROXMOX_TOKEN_ID
        self.token_secret = token_secret if token_secret is not None else settings.PROXMOX_TOKEN_SECRET
        self.verify_ssl = verify_ssl
        self._connected = False
        self._connection_error = None
        self._client: Optional[httpx.AsyncClient] = None

    def update_config(
        self,
        endpoint: Optional[str] = None,
        user: Optional[str] = None,
        token_id: Optional[str] = None,
        token_secret: Optional[str] = None,
        verify_ssl: Optional[bool] = None
    ):
        if endpoint is not None:
            self.endpoint = endpoint.rstrip('/')
        if user is not None:
            self.user = user
        if token_id is not None:
            self.token_id = token_id
        if token_secret is not None and token_secret.strip():
            self.token_secret = token_secret
        if verify_ssl is not None:
            self.verify_ssl = verify_ssl
        self._connected = False
        self._client = None

    def _get_headers(self) -> dict:
        return {
            "Authorization": f"PVEAPIToken={self.user}!{self.token_id}={self.token_secret}",
            "Accept": "application/json"
        }

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                verify=self.verify_ssl,
                timeout=10.0,
                headers=self._get_headers()
            )
        return self._client

    async def test_connection(self) -> ProviderConnectionResult:
        t0 = time.perf_counter()
        if not self.endpoint:
            return ProviderConnectionResult(
                provider="proxmox",
                status="UNAVAILABLE",
                latency_ms=None,
                node_count=0,
                vm_count=0,
                message="Proxmox endpoint URL is not configured."
            )
        if not self.token_secret:
            return ProviderConnectionResult(
                provider="proxmox",
                status="UNAVAILABLE",
                latency_ms=None,
                node_count=0,
                vm_count=0,
                message="Proxmox API token secret is not configured. Provide credentials in Settings."
            )

        try:
            client = await self._ensure_client()
            resp = await client.get(f"{self.endpoint}/version")
            latency = round((time.perf_counter() - t0) * 1000.0, 2)
            
            if resp.status_code == 200:
                self._connected = True
                self._connection_error = None
                ver_data = resp.json().get("data", {})
                version_str = f"Proxmox VE {ver_data.get('version', '')} (release: {ver_data.get('release', '')})"
                
                nodes = await self.discover_nodes()
                vms = await self.discover_vms()
                return ProviderConnectionResult(
                    provider="proxmox",
                    status="CONNECTED",
                    latency_ms=latency,
                    hypervisor_version=version_str,
                    node_count=len(nodes),
                    vm_count=len(vms),
                    message=f"Successfully connected to Proxmox VE API at {self.endpoint}.",
                    details=ver_data
                )
            elif resp.status_code in (401, 403):
                self._connected = False
                self._connection_error = f"Authentication failed: HTTP {resp.status_code} ({resp.text})"
                return ProviderConnectionResult(
                    provider="proxmox",
                    status="AUTHENTICATION_ERROR",
                    latency_ms=latency,
                    node_count=0,
                    vm_count=0,
                    message=f"Authentication failed: HTTP {resp.status_code}. Verify User, Token ID, and Token Secret.",
                    details={"http_status": resp.status_code, "response": resp.text}
                )
            else:
                self._connected = False
                self._connection_error = f"HTTP {resp.status_code}: {resp.text}"
                return ProviderConnectionResult(
                    provider="proxmox",
                    status="DISCONNECTED",
                    latency_ms=latency,
                    node_count=0,
                    vm_count=0,
                    message=f"Proxmox endpoint returned HTTP {resp.status_code}: {resp.text[:180]}",
                    details={"http_status": resp.status_code}
                )
        except httpx.ConnectError as e:
            latency = round((time.perf_counter() - t0) * 1000.0, 2)
            self._connected = False
            self._connection_error = f"Connection refused or unreachable: {str(e)}"
            return ProviderConnectionResult(
                provider="proxmox",
                status="DISCONNECTED",
                latency_ms=latency,
                node_count=0,
                vm_count=0,
                message=f"Cannot reach Proxmox host at {self.endpoint}. Check IP, port 8006, and network connectivity.",
                details={"error": str(e)}
            )
        except httpx.TimeoutException:
            latency = round((time.perf_counter() - t0) * 1000.0, 2)
            self._connected = False
            self._connection_error = "Connection timed out (10s threshold)."
            return ProviderConnectionResult(
                provider="proxmox",
                status="DISCONNECTED",
                latency_ms=latency,
                node_count=0,
                vm_count=0,
                message=f"Connection to Proxmox host at {self.endpoint} timed out.",
                details={"error": "timeout"}
            )
        except Exception as e:
            latency = round((time.perf_counter() - t0) * 1000.0, 2)
            self._connected = False
            self._connection_error = str(e)
            return ProviderConnectionResult(
                provider="proxmox",
                status="DISCONNECTED",
                latency_ms=latency,
                node_count=0,
                vm_count=0,
                message=f"Connection attempt failed: {str(e)}",
                details={"error": str(e)}
            )

    async def connect(self) -> bool:
        if not self.token_secret:
            self._connected = False
            self._connection_error = "Proxmox API token secret is not configured."
            return False

        try:
            client = await self._ensure_client()
            resp = await client.get(f"{self.endpoint}/version")
            if resp.status_code == 200:
                self._connected = True
                self._connection_error = None
                return True
            else:
                self._connected = False
                self._connection_error = f"Authentication failed: HTTP {resp.status_code} ({resp.text})"
                return False
        except Exception as e:
            self._connected = False
            self._connection_error = f"Connection failed: {str(e)}"
            return False

    async def disconnect(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
        self._connected = False

    async def is_connected(self) -> bool:
        return self._connected

    async def discover_nodes(self) -> list[NodeTelemetry]:
        if not self._connected:
            return []
        try:
            client = await self._ensure_client()
            resp = await client.get(f"{self.endpoint}/nodes")
            if resp.status_code != 200:
                return []
            
            raw_nodes = resp.json().get("data", [])
            nodes = []
            for n in raw_nodes:
                node_id = n.get("node")
                status = "online" if n.get("status") == "online" else "offline"
                cpu_pct = round(n.get("cpu", 0.0) * 100.0, 1)
                mem_total = round(n.get("maxmem", 0) / (1024 * 1024), 1)
                mem_used = round(n.get("mem", 0) / (1024 * 1024), 1)
                mem_pct = round((mem_used / max(1.0, mem_total)) * 100.0, 1)
                
                nodes.append(NodeTelemetry(
                    id=node_id,
                    name=f"{node_id}.pve",
                    status=status,
                    cpu_cores=n.get("maxcpu", 16),
                    cpu_percent=cpu_pct,
                    ram_total_mb=mem_total,
                    ram_used_mb=mem_used,
                    ram_percent=mem_pct,
                    disk_total_gb=round(n.get("maxdisk", 0) / (1024 * 1024 * 1024), 1),
                    disk_used_gb=round(n.get("disk", 0) / (1024 * 1024 * 1024), 1),
                    shared_storage_accessible=True,
                    quorum_healthy=True
                ))
            return nodes
        except Exception as e:
            self._connected = False
            self._connection_error = str(e)
            return []

    async def discover_vms(self) -> list[VMTelemetry]:
        if not self._connected:
            return []
        try:
            client = await self._ensure_client()
            resp = await client.get(f"{self.endpoint}/cluster/resources?type=vm")
            if resp.status_code != 200:
                return []
            
            raw_vms = resp.json().get("data", [])
            vms = []
            for v in raw_vms:
                vmid = str(v.get("vmid"))
                node_id = v.get("node")
                status = "running" if v.get("status") == "running" else "stopped"
                cpu_pct = round(v.get("cpu", 0.0) * 100.0, 1)
                mem_alloc = round(v.get("maxmem", 0) / (1024 * 1024), 1)
                mem_used = round(v.get("mem", 0) / (1024 * 1024), 1)
                mem_pct = round((mem_used / max(1.0, mem_alloc)) * 100.0, 1)

                vms.append(VMTelemetry(
                    vmid=vmid,
                    name=v.get("name", f"vm-{vmid}"),
                    node_id=node_id,
                    status=status,
                    cpu_cores=v.get("maxcpu", 4),
                    cpu_percent=cpu_pct,
                    ram_allocated_mb=mem_alloc,
                    ram_used_mb=mem_used,
                    ram_percent=mem_pct,
                    disk_allocated_gb=round(v.get("maxdisk", 0) / (1024 * 1024 * 1024), 1),
                    uptime_seconds=int(v.get("uptime", 0))
                ))
            return vms
        except Exception as e:
            self._connected = False
            self._connection_error = str(e)
            return []

    async def collect_telemetry(self) -> ClusterState:
        is_conn = await self.is_connected()
        if not is_conn:
            is_conn = await self.connect()

        if not is_conn:
            return ClusterState(
                is_live=True,
                connected=False,
                provider_name="proxmox",
                timestamp=time.time(),
                nodes={},
                vms={},
                error_message=f"LIVE CLUSTER DISCONNECTED: {self._connection_error or 'Endpoint unreachable'}"
            )

        nodes_list = await self.discover_nodes()
        vms_list = await self.discover_vms()
        nodes_dict = {n.id: n for n in nodes_list}
        vms_dict = {v.vmid: v for v in vms_list}

        for v in vms_list:
            if v.node_id in nodes_dict:
                nodes_dict[v.node_id].active_vms.append(v.vmid)

        return ClusterState(
            is_live=True,
            connected=True,
            provider_name="proxmox",
            timestamp=time.time(),
            nodes=nodes_dict,
            vms=vms_dict
        )

    async def inspect_vm_state(self, vm_id: str) -> Optional[VMTelemetry]:
        vms = await self.discover_vms()
        for v in vms:
            if v.vmid == vm_id:
                return v
        return None

    async def validate_migration(self, vm_id: str, target_node: str) -> tuple[bool, str]:
        state = await self.collect_telemetry()
        if not state.connected:
            return False, "Proxmox cluster is disconnected."
        if vm_id not in state.vms:
            return False, f"VM {vm_id} not found."
        if target_node not in state.nodes:
            return False, f"Target node {target_node} not found."
        return True, "Proxmox validation passed."

    async def plan_migration(self, vm_id: str, target_node: str, reason: str = "Rebalance") -> MigrationPlan:
        vm = await self.inspect_vm_state(vm_id)
        if not vm:
            raise KeyError(f"VM '{vm_id}' not found in Proxmox cluster.")
        return MigrationPlan(
            plan_id=f"plan-pve-{int(time.time())}",
            vm_id=vm_id,
            source_node=vm.node_id,
            target_node=target_node,
            reason=reason,
            created_at=time.time()
        )

    async def execute_migration(self, plan: MigrationPlan) -> str:
        client = await self._ensure_client()
        payload = {
            "target": plan.target_node,
            "online": 1,
            "with-local-disks": 1
        }
        url = f"{self.endpoint}/nodes/{plan.source_node}/qemu/{plan.vm_id}/migrate"
        resp = await client.post(url, data=payload)
        
        if resp.status_code != 200:
            raise RuntimeError(f"Proxmox migration dispatch failed: HTTP {resp.status_code} - {resp.text}")
        
        upid = resp.json().get("data")
        return upid

    async def monitor_migration_task(self, task_id: str) -> MigrationTaskStatus:
        parts = task_id.split(":")
        node = parts[1] if len(parts) > 1 else "unknown"

        client = await self._ensure_client()
        url = f"{self.endpoint}/nodes/{node}/tasks/{task_id}/status"
        resp = await client.get(url)

        if resp.status_code != 200:
            raise RuntimeError(f"Failed to query Proxmox task status: {resp.text}")

        data = resp.json().get("data", {})
        is_stopped = data.get("status") == "stopped"
        exitstatus = data.get("exitstatus")

        if is_stopped:
            if exitstatus == "OK":
                return MigrationTaskStatus(
                    task_id=task_id,
                    plan_id="pve",
                    vm_id=parts[6] if len(parts) > 6 else "unknown",
                    source_node=node,
                    target_node="target",
                    state="VERIFIED",
                    progress_percent=100.0,
                    completed_at=time.time(),
                    verified_at=time.time(),
                    verification_details={"exitstatus": "OK", "upid": task_id}
                )
            else:
                return MigrationTaskStatus(
                    task_id=task_id,
                    plan_id="pve",
                    vm_id=parts[6] if len(parts) > 6 else "unknown",
                    source_node=node,
                    target_node="target",
                    state="FAILED",
                    progress_percent=100.0,
                    error=f"Task exited with error: {exitstatus}"
                )

        return MigrationTaskStatus(
            task_id=task_id,
            plan_id="pve",
            vm_id=parts[6] if len(parts) > 6 else "unknown",
            source_node=node,
            target_node="target",
            state="MIGRATING",
            progress_percent=50.0
        )

    async def verify_placement(self, vm_id: str, expected_node: str) -> tuple[bool, str]:
        state = await self.collect_telemetry()
        if not state.connected:
            return False, "Cannot verify: cluster disconnected."
        
        vm = state.vms.get(vm_id)
        if not vm:
            return False, f"VM {vm_id} disappeared from inventory post-migration."
        if vm.node_id != expected_node:
            return False, f"Placement mismatch: VM resides on '{vm.node_id}', expected '{expected_node}'."
        return True, f"Verified: VM {vm_id} is residing on {expected_node}."

    async def verify_vm_health(self, vm_id: str) -> tuple[bool, str]:
        vm = await self.inspect_vm_state(vm_id)
        if not vm:
            return False, f"VM '{vm_id}' not found."
        if vm.status != "running":
            return False, f"VM health check failed: status is '{vm.status}', expected 'running'."
        return True, f"Workload '{vm_id}' is running and healthy."
