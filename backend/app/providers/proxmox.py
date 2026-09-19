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


def parse_proxmox_upid(upid: str) -> dict[str, str]:
    """
    Explicitly validates and parses a Proxmox VE UPID string.
    Standard format: UPID:<node>:<pid>:<pstart>:<starttime>:<type>:<id>:<user>:
    Returns empty dict if the string does not match the valid UPID structure.
    """
    if not isinstance(upid, str) or not upid.startswith("UPID:"):
        return {}
    parts = upid.split(":")
    # A standard Proxmox UPID has at least 8 parts (or 9 including trailing empty element)
    if len(parts) < 8:
        return {}
    return {
        "node": parts[1],
        "pid": parts[2],
        "pstart": parts[3],
        "starttime": parts[4],
        "type": parts[5],
        "id": parts[6],
        "user": parts[7]
    }


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
        # Maps dispatched UPID -> full task context dict:
        # {"plan_id": str, "vm_id": str, "source_node": str, "target_node": str}
        self._task_context_map: dict[str, dict[str, str]] = {}
        # Backwards-compatible alias for target_node tracking:
        self._task_target_map: dict[str, str] = {}

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

            # --- Cluster quorum status (HEALTHY / UNHEALTHY / UNKNOWN) ---
            # GET /cluster/status returns a list where type=="cluster" has "quorate" field.
            quorum_ok = False
            quorum_status = "UNKNOWN"
            try:
                cstatus_resp = await client.get(f"{self.endpoint}/cluster/status")
                if cstatus_resp.status_code == 200:
                    cdata = cstatus_resp.json().get("data")
                    if isinstance(cdata, list):
                        cluster_entry = next((item for item in cdata if item.get("type") == "cluster"), None)
                        if cluster_entry is not None and "quorate" in cluster_entry:
                            q_val = cluster_entry.get("quorate")
                            if q_val == 1 or q_val is True:
                                quorum_status = "HEALTHY"
                                quorum_ok = True
                            elif q_val == 0 or q_val is False:
                                quorum_status = "UNHEALTHY"
                                quorum_ok = False
                            else:
                                quorum_status = "UNKNOWN"
                                quorum_ok = False
                        else:
                            # Malformed entry or no quorate field
                            quorum_status = "UNKNOWN"
                            quorum_ok = False
                    else:
                        quorum_status = "UNKNOWN"
                        quorum_ok = False
                else:
                    quorum_status = "UNKNOWN"
                    quorum_ok = False
            except Exception:
                quorum_status = "UNKNOWN"
                quorum_ok = False  # Fail-closed: unverified quorum treated as unhealthy

            raw_nodes = resp.json().get("data", [])
            nodes = []
            for n in raw_nodes:
                node_id = n.get("node")
                status = "online" if n.get("status") == "online" else "offline"
                cpu_pct = round(n.get("cpu", 0.0) * 100.0, 1)
                mem_total = round(n.get("maxmem", 0) / (1024 * 1024), 1)
                mem_used = round(n.get("mem", 0) / (1024 * 1024), 1)
                mem_pct = round((mem_used / max(1.0, mem_total)) * 100.0, 1)

                # --- Per-node storage accessibility (HEALTHY / UNHEALTHY / UNKNOWN) ---
                # GET /nodes/{node}/storage returns storage pools with "active" and "shared" fields.
                # shared_storage_accessible is True ONLY if at least one active pool is explicitly marked shared=1.
                storage_ok = False
                storage_status = "UNKNOWN"
                if status == "online":
                    try:
                        stor_resp = await client.get(f"{self.endpoint}/nodes/{node_id}/storage")
                        if stor_resp.status_code == 200:
                            storages = stor_resp.json().get("data", [])
                            if isinstance(storages, list):
                                has_shared_active = any(
                                    bool(s.get("active", 0)) and bool(s.get("shared", 0))
                                    for s in storages
                                )
                                has_any_active = any(bool(s.get("active", 0)) for s in storages)
                                if has_any_active:
                                    storage_status = "HEALTHY"
                                    storage_ok = has_shared_active
                                else:
                                    # No active storage pool on node
                                    storage_status = "UNHEALTHY"
                                    storage_ok = False
                            else:
                                storage_status = "UNKNOWN"
                                storage_ok = False
                        else:
                            storage_status = "UNKNOWN"
                            storage_ok = False
                    except Exception:
                        storage_status = "UNKNOWN"
                        storage_ok = False  # Fail-closed: unverified storage = inaccessible
                else:
                    storage_status = "UNHEALTHY"
                    storage_ok = False

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
                    shared_storage_accessible=storage_ok,
                    quorum_healthy=quorum_ok,
                    quorum_status=quorum_status,
                    storage_status=storage_status
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

    async def get_vm_disk_storage_ids(self, source_node: str, vm_id: str) -> tuple[Optional[list[str]], str]:
        """
        Queries Proxmox VM configuration (GET /nodes/{source_node}/qemu/{vm_id}/config)
        to extract the datastore / storage IDs assigned to the VM's disk drives.
        Returns:
            (storage_ids, message) where storage_ids is None on failure, or list of unique storage IDs.
        """
        try:
            client = await self._ensure_client()
            url = f"{self.endpoint}/nodes/{source_node}/qemu/{vm_id}/config"
            resp = await client.get(url)
            if resp.status_code != 200:
                return None, f"Failed to retrieve VM config from Proxmox (HTTP {resp.status_code}: {resp.text[:120]})"

            config_data = resp.json().get("data", {})
            storage_ids: list[str] = []
            # Proxmox disk device keys: scsi0..30, virtio0..15, ide0..3, sata0..5, efidisk0
            disk_prefixes = ("scsi", "virtio", "ide", "sata", "efidisk")
            for k, v in config_data.items():
                if isinstance(v, str) and any(k.startswith(p) for p in disk_prefixes):
                    if ":" in v:
                        sid = v.split(":", 1)[0].strip()
                        if sid and sid not in storage_ids:
                            storage_ids.append(sid)
            return storage_ids, f"Identified {len(storage_ids)} datastore(s) for VM {vm_id}: {', '.join(storage_ids) if storage_ids else 'none (diskless)'}"
        except Exception as e:
            return None, f"Exception querying VM config for {vm_id}: {str(e)}"

    async def verify_migration_storage(
        self,
        vm_id: str,
        source_node: str,
        target_node: str,
        with_local_disks: bool = True
    ) -> tuple[bool, str, str]:
        """
        Verifies storage prerequisites for migration:
        - If with_local_disks=True (Local-disk migration path):
          Does NOT require shared storage. Verifies that the destination node's
          storage subsystem is reachable and contains active storage to receive disks.
        - If with_local_disks=False (Shared-storage migration path):
          Verifies that every datastore required by the VM's disks exists, is active,
          and is marked shared=1 on BOTH source and destination nodes.
        - If hypervisor APIs fail or VM datastores cannot be determined:
          Fails closed with status 'UNKNOWN' (no guessing).

        Returns:
            (allowed: bool, status: Literal["HEALTHY", "UNHEALTHY", "UNKNOWN"], details: str)
        """
        client = await self._ensure_client()

        # Step 1: Query target node storage
        try:
            target_resp = await client.get(f"{self.endpoint}/nodes/{target_node}/storage")
            if target_resp.status_code != 200:
                return False, "UNKNOWN", f"Storage API returned HTTP {target_resp.status_code} for target node '{target_node}'."
            target_storages = {s.get("storage"): s for s in target_resp.json().get("data", [])}
        except Exception as e:
            return False, "UNKNOWN", f"Storage API unavailable for target node '{target_node}': {str(e)}"

        # Step 2: Query source node storage
        try:
            source_resp = await client.get(f"{self.endpoint}/nodes/{source_node}/storage")
            if source_resp.status_code != 200:
                return False, "UNKNOWN", f"Storage API returned HTTP {source_resp.status_code} for source node '{source_node}'."
            source_storages = {s.get("storage"): s for s in source_resp.json().get("data", [])}
        except Exception as e:
            return False, "UNKNOWN", f"Storage API unavailable for source node '{source_node}': {str(e)}"

        # Step 3: Determine VM's required datastores
        vm_stores, store_msg = await self.get_vm_disk_storage_ids(source_node, vm_id)
        if vm_stores is None:
            return False, "UNKNOWN", f"VM datastore cannot be determined: {store_msg}"

        # Step 4: Evaluate according to migration strategy
        if with_local_disks:
            # Local-disk migration (--with-local-disks 1)
            # Local disks are live-mirrored via QEMU NBD stream; does NOT require shared storage.
            active_target_pools = [s for s in target_storages.values() if bool(s.get("active", 0))]
            if not active_target_pools:
                return False, "UNHEALTHY", f"Target node '{target_node}' has no active storage pools to receive local disk mirror."
            return True, "HEALTHY", f"Local-disk migration supported with --with-local-disks 1 ({len(active_target_pools)} active storage pool(s) on '{target_node}')."
        else:
            # Shared-storage migration (without --with-local-disks)
            # Every datastore used by VM disks MUST be active and marked shared on both source and target.
            if not vm_stores:
                return True, "HEALTHY", f"VM '{vm_id}' has no virtual disks; shared storage prerequisite satisfied."

            for ds in vm_stores:
                src_ds = source_storages.get(ds)
                tgt_ds = target_storages.get(ds)

                if not src_ds or not bool(src_ds.get("active", 0)):
                    return False, "UNHEALTHY", f"Datastore '{ds}' required by VM '{vm_id}' is not active on source node '{source_node}'."

                if not tgt_ds:
                    return False, "UNHEALTHY", f"Datastore '{ds}' required by VM '{vm_id}' is available on source node '{source_node}' but missing on target node '{target_node}'."

                if not bool(tgt_ds.get("active", 0)):
                    return False, "UNHEALTHY", f"Datastore '{ds}' required by VM '{vm_id}' is inactive on target node '{target_node}'."

                if not bool(src_ds.get("shared", 0)) or not bool(tgt_ds.get("shared", 0)):
                    return False, "UNHEALTHY", f"Datastore '{ds}' is not marked shared on source or target node; requires local-disk migration (--with-local-disks 1)."

            return True, "HEALTHY", f"Shared datastore(s) {vm_stores} verified active and shared on both '{source_node}' and '{target_node}'."

    async def validate_migration(self, vm_id: str, target_node: str, with_local_disks: bool = True) -> tuple[bool, str]:
        state = await self.collect_telemetry()
        if not state.connected:
            return False, "Proxmox cluster is disconnected."
        if vm_id not in state.vms:
            return False, f"VM {vm_id} not found."
        if target_node not in state.nodes:
            return False, f"Target node {target_node} not found."

        vm = state.vms[vm_id]
        if vm.node_id == target_node:
            return False, f"VM '{vm_id}' is already hosted on target node '{target_node}'."

        allowed, status, reason = await self.verify_migration_storage(
            vm_id=vm_id,
            source_node=vm.node_id,
            target_node=target_node,
            with_local_disks=with_local_disks
        )
        if not allowed:
            return False, f"Storage validation failed ({status}): {reason}"

        return True, f"Proxmox validation passed ({status}): {reason}"

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
            created_at=time.time(),
            with_local_disks=True
        )

    async def execute_migration(self, plan: MigrationPlan) -> str:
        client = await self._ensure_client()
        with_local = 1 if getattr(plan, "with_local_disks", True) else 0
        payload = {
            "target": plan.target_node,
            "online": 1,
            "with-local-disks": with_local
        }
        url = f"{self.endpoint}/nodes/{plan.source_node}/qemu/{plan.vm_id}/migrate"
        resp = await client.post(url, data=payload)

        if resp.status_code != 200:
            raise RuntimeError(f"Proxmox migration dispatch failed: HTTP {resp.status_code} - {resp.text}")

        upid = resp.json().get("data")
        # Record migration task context so monitor_migration_task() can propagate exact metadata
        if upid:
            self._task_context_map[upid] = {
                "plan_id": plan.plan_id,
                "vm_id": plan.vm_id,
                "source_node": plan.source_node,
                "target_node": plan.target_node
            }
            self._task_target_map[upid] = plan.target_node
        return upid

    async def monitor_migration_task(self, task_id: str) -> MigrationTaskStatus:
        # 1. Prefer known migration task context established during execute_migration()
        if task_id in self._task_context_map:
            ctx = self._task_context_map[task_id]
            node = ctx["source_node"]
            target_node = ctx["target_node"]
            vm_id = ctx["vm_id"]
            plan_id = ctx["plan_id"]
        elif task_id in self._task_target_map:
            # Backwards compatibility for tests directly populating _task_target_map
            target_node = self._task_target_map[task_id]
            parsed = parse_proxmox_upid(task_id)
            node = parsed.get("node", "unknown")
            vm_id = parsed.get("id", "unknown")
            plan_id = "pve"
        else:
            # External or untracked task: parse validated UPID
            parsed = parse_proxmox_upid(task_id)
            node = parsed.get("node", "unknown")
            vm_id = parsed.get("id", "unknown")
            target_node = "unknown"
            plan_id = "external"

        if node == "unknown":
            raise RuntimeError(f"Cannot query Proxmox task status for '{task_id}': unknown or invalid UPID source node.")

        client = await self._ensure_client()
        url = f"{self.endpoint}/nodes/{node}/tasks/{task_id}/status"
        resp = await client.get(url)

        if resp.status_code != 200:
            raise RuntimeError(f"Failed to query Proxmox task status: {resp.text}")

        data = resp.json().get("data", {})
        is_stopped = data.get("status") == "stopped"
        exitstatus = data.get("exitstatus")

        if is_stopped:
            # Clean up context maps once terminal state is reached
            self._task_context_map.pop(task_id, None)
            self._task_target_map.pop(task_id, None)
            if exitstatus == "OK":
                return MigrationTaskStatus(
                    task_id=task_id,
                    plan_id=plan_id,
                    vm_id=vm_id,
                    source_node=node,
                    target_node=target_node,
                    state="VERIFIED",
                    progress_percent=100.0,
                    completed_at=time.time(),
                    verified_at=time.time(),
                    verification_details={"exitstatus": "OK", "upid": task_id}
                )
            else:
                return MigrationTaskStatus(
                    task_id=task_id,
                    plan_id=plan_id,
                    vm_id=vm_id,
                    source_node=node,
                    target_node=target_node,
                    state="FAILED",
                    progress_percent=100.0,
                    error=f"Task exited with error: {exitstatus}"
                )

        return MigrationTaskStatus(
            task_id=task_id,
            plan_id=plan_id,
            vm_id=vm_id,
            source_node=node,
            target_node=target_node,
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
        # Verify VM is not still listed on any other node's active list
        for nid, node in state.nodes.items():
            if nid != expected_node and vm_id in node.active_vms:
                return False, f"Placement conflict: VM '{vm_id}' is still reported on source/other node '{nid}'."
        return True, f"Verified: VM {vm_id} is residing on {expected_node}."

    async def verify_vm_health(self, vm_id: str) -> tuple[bool, str]:
        """
        Verifies post-migration guest health using two independent checks:
        1. Hypervisor-reported VM status must be 'running'.
        2. QEMU guest-agent ping: POST /nodes/{node}/qemu/{vmid}/agent/ping
           This call is an action (POST) per the Proxmox VE REST API specification.
           A successful 200 response confirms the virtio-serial guest-agent channel
           is alive and the guest kernel is responsive.
        Requires the VM.GuestAgent.Audit privilege on the API token.
        NOTE: This path remains UNVERIFIED on real hardware until a live Proxmox cluster
              is provisioned and the guest agent is running inside the test VM.
        """
        vm = await self.inspect_vm_state(vm_id)
        if not vm:
            return False, f"VM '{vm_id}' not found in cluster inventory."
        if vm.status != "running":
            return False, (
                f"VM health check failed: hypervisor reports status '{vm.status}', expected 'running'."
            )

        # Guest-agent ping — POST because it triggers an agent action, not a data read.
        try:
            client = await self._ensure_client()
            url = f"{self.endpoint}/nodes/{vm.node_id}/qemu/{vm_id}/agent/ping"
            resp = await client.post(url)
            if resp.status_code == 200:
                return True, (
                    f"Workload '{vm_id}' is running and guest agent responded to ping "
                    f"on '{vm.node_id}'."
                )
            else:
                return False, (
                    f"Guest agent ping failed for VM '{vm_id}' on '{vm.node_id}': "
                    f"HTTP {resp.status_code} — {resp.text[:200]}"
                )
        except Exception as e:
            return False, (
                f"Guest agent ping error for VM '{vm_id}' on '{vm.node_id}': {str(e)}"
            )
