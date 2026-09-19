"""
Regression tests for VMotion AI ProxmoxVEProvider corrections:

1. Guest-agent ping — verify_vm_health() calls POST .../agent/ping and
   propagates success, HTTP failure, and exception correctly.
2. target_node propagation — execute_migration() stores target node and
   monitor_migration_task() returns it accurately; no hardcoded placeholder.
3. Quorum / storage fail-closed — discover_nodes() queries /cluster/status
   and /nodes/{node}/storage; defaults to False (not True) on any API error.

All tests are MOCK-TESTED ONLY.
Real Proxmox hardware connectivity remains UNVERIFIED.
"""
import pytest
import time
from unittest.mock import AsyncMock, patch, MagicMock

from app.providers.proxmox import ProxmoxVEProvider, parse_proxmox_upid
from app.providers.base import MigrationPlan, VMTelemetry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_vm(vmid: str = "101", node_id: str = "pve-node-1") -> VMTelemetry:
    return VMTelemetry(
        vmid=vmid,
        name=f"vm-{vmid}",
        node_id=node_id,
        status="running",
        cpu_cores=2,
        cpu_percent=40.0,
        ram_allocated_mb=2048.0,
        ram_used_mb=1024.0,
        ram_percent=50.0,
        uptime_seconds=3600,
    )


def _make_provider() -> ProxmoxVEProvider:
    return ProxmoxVEProvider(
        endpoint="https://10.0.0.1:8006/api2/json",
        user="vmotion-api@pve",
        token_id="automation",
        token_secret="test-secret",
    )


# ---------------------------------------------------------------------------
# 1. Guest-agent ping tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_verify_vm_health_guest_agent_ping_success():
    """
    When VM is running AND guest-agent ping returns HTTP 200,
    verify_vm_health() must return (True, message_containing_node).
    """
    provider = _make_provider()
    provider._connected = True
    vm = _make_vm()

    mock_ping_resp = MagicMock()
    mock_ping_resp.status_code = 200
    mock_ping_resp.text = "{}"

    with patch.object(provider, "inspect_vm_state", new=AsyncMock(return_value=vm)):
        with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_ping_resp)):
            ok, msg = await provider.verify_vm_health("101")

    assert ok is True
    assert "pve-node-1" in msg


@pytest.mark.asyncio
async def test_verify_vm_health_guest_agent_ping_http_failure():
    """
    When VM is running BUT guest-agent ping returns a non-200 status (e.g. 500),
    verify_vm_health() must return (False, message_with_status_code).
    """
    provider = _make_provider()
    provider._connected = True
    vm = _make_vm()

    mock_ping_resp = MagicMock()
    mock_ping_resp.status_code = 500
    mock_ping_resp.text = "agent not running"

    with patch.object(provider, "inspect_vm_state", new=AsyncMock(return_value=vm)):
        with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_ping_resp)):
            ok, msg = await provider.verify_vm_health("101")

    assert ok is False
    assert "500" in msg or "agent" in msg.lower()


@pytest.mark.asyncio
async def test_verify_vm_health_guest_agent_ping_network_exception():
    """
    When guest-agent ping raises a network exception,
    verify_vm_health() must return (False, error_message) — no silent success.
    """
    import httpx
    provider = _make_provider()
    provider._connected = True
    vm = _make_vm()

    with patch.object(provider, "inspect_vm_state", new=AsyncMock(return_value=vm)):
        with patch("httpx.AsyncClient.post", side_effect=httpx.ConnectError("Timeout")):
            ok, msg = await provider.verify_vm_health("101")

    assert ok is False
    assert len(msg) > 0


@pytest.mark.asyncio
async def test_verify_vm_health_stopped_vm_fails_before_ping():
    """
    When VM status is not 'running', verify_vm_health() must fail immediately
    without calling the guest-agent ping endpoint.
    """
    provider = _make_provider()
    provider._connected = True
    vm = _make_vm()
    vm.status = "stopped"

    with patch.object(provider, "inspect_vm_state", new=AsyncMock(return_value=vm)):
        with patch("httpx.AsyncClient.post", new=AsyncMock()) as mock_post:
            ok, msg = await provider.verify_vm_health("101")

    assert ok is False
    assert "stopped" in msg.lower() or "running" in msg.lower()
    mock_post.assert_not_called()


@pytest.mark.asyncio
async def test_verify_vm_health_vm_not_found():
    """
    When VM is not found in inventory, verify_vm_health() must return (False, message).
    """
    provider = _make_provider()
    provider._connected = True

    with patch.object(provider, "inspect_vm_state", new=AsyncMock(return_value=None)):
        ok, msg = await provider.verify_vm_health("999")

    assert ok is False
    assert "not found" in msg.lower() or "999" in msg


# ---------------------------------------------------------------------------
# 2. target_node propagation tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_execute_migration_stores_target_node():
    """
    execute_migration() must store plan.target_node in _task_target_map keyed
    by the returned UPID so monitor_migration_task() can look it up.
    """
    provider = _make_provider()
    provider._connected = True

    upid = "UPID:pve-node-1:001A2B3C:00000064:6123ABCD:qmigrate:101:vmotion-api@pve:"
    plan = MigrationPlan(
        plan_id="plan-test-001",
        vm_id="101",
        source_node="pve-node-1",
        target_node="pve-node-2",
        reason="Rebalance",
        created_at=time.time(),
    )

    mock_migrate_resp = MagicMock()
    mock_migrate_resp.status_code = 200
    mock_migrate_resp.json.return_value = {"data": upid}

    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_migrate_resp)):
        returned_upid = await provider.execute_migration(plan)

    assert returned_upid == upid
    assert provider._task_target_map.get(upid) == "pve-node-2", (
        "Target node must be stored in _task_target_map after execute_migration()"
    )


@pytest.mark.asyncio
async def test_monitor_migration_task_returns_real_target_node_running():
    """
    monitor_migration_task() must return the actual target_node (from _task_target_map)
    in the MIGRATING state, not the placeholder string 'target'.
    """
    provider = _make_provider()
    provider._connected = True

    upid = "UPID:pve-node-1:001A2B3C:00000064:6123ABCD:qmigrate:101:vmotion-api@pve:"
    provider._task_target_map[upid] = "pve-node-2"

    mock_status_resp = MagicMock()
    mock_status_resp.status_code = 200
    mock_status_resp.json.return_value = {"data": {"status": "running", "exitstatus": None}}

    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=mock_status_resp)):
        task_status = await provider.monitor_migration_task(upid)

    assert task_status.target_node == "pve-node-2"
    assert task_status.target_node != "target"


@pytest.mark.asyncio
async def test_monitor_migration_task_returns_real_target_node_verified():
    """
    monitor_migration_task() must return actual target_node in VERIFIED (stopped OK) state
    and clean up the map entry.
    """
    provider = _make_provider()
    provider._connected = True

    upid = "UPID:pve-node-1:001A2B3C:00000064:6123ABCD:qmigrate:101:vmotion-api@pve:"
    provider._task_target_map[upid] = "pve-node-2"

    mock_status_resp = MagicMock()
    mock_status_resp.status_code = 200
    mock_status_resp.json.return_value = {"data": {"status": "stopped", "exitstatus": "OK"}}

    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=mock_status_resp)):
        task_status = await provider.monitor_migration_task(upid)

    assert task_status.state == "VERIFIED"
    assert task_status.target_node == "pve-node-2"
    assert upid not in provider._task_target_map, (
        "Completed task UPID must be removed from _task_target_map"
    )


@pytest.mark.asyncio
async def test_monitor_migration_task_unknown_target_without_prior_execute():
    """
    If monitor_migration_task() is called for a UPID that was not dispatched
    via execute_migration() (map has no entry), target_node must be 'unknown',
    not the placeholder string 'target'.
    """
    provider = _make_provider()
    provider._connected = True

    upid = "UPID:pve-node-1:AABBCCDD:00000064:6123ABCD:qmigrate:101:vmotion-api@pve:"

    mock_status_resp = MagicMock()
    mock_status_resp.status_code = 200
    mock_status_resp.json.return_value = {"data": {"status": "running", "exitstatus": None}}

    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=mock_status_resp)):
        task_status = await provider.monitor_migration_task(upid)

    assert task_status.target_node == "unknown"
    assert task_status.target_node != "target"


# ---------------------------------------------------------------------------
# 3. Quorum / storage fail-closed tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_discover_nodes_quorum_healthy_and_storage_active():
    """
    When /cluster/status returns quorate=1 and /nodes/{node}/storage returns
    at least one active pool, NodeTelemetry must reflect quorum_healthy=True
    and shared_storage_accessible=True.
    """
    provider = _make_provider()
    provider._connected = True

    nodes_resp = MagicMock()
    nodes_resp.status_code = 200
    nodes_resp.json.return_value = {"data": [
        {"node": "pve-node-1", "status": "online", "cpu": 0.3, "maxcpu": 4,
         "mem": 2048 * 1024 * 1024, "maxmem": 8192 * 1024 * 1024,
         "disk": 0, "maxdisk": 0}
    ]}

    cluster_status_resp = MagicMock()
    cluster_status_resp.status_code = 200
    cluster_status_resp.json.return_value = {"data": [
        {"type": "cluster", "quorate": 1, "name": "pve-cluster"},
        {"type": "node", "name": "pve-node-1", "online": 1},
    ]}

    storage_resp = MagicMock()
    storage_resp.status_code = 200
    storage_resp.json.return_value = {"data": [
        {"storage": "local", "type": "dir", "active": 1, "shared": 0},
        {"storage": "nfs-shared", "type": "nfs", "active": 1, "shared": 1},
    ]}

    async def mock_get(url, **kwargs):
        if url.endswith("/nodes"):
            return nodes_resp
        if url.endswith("/cluster/status"):
            return cluster_status_resp
        if "/storage" in url:
            return storage_resp
        raise ValueError(f"Unexpected URL in mock: {url}")

    with patch("httpx.AsyncClient.get", side_effect=mock_get):
        nodes = await provider.discover_nodes()

    assert len(nodes) == 1
    assert nodes[0].quorum_healthy is True
    assert nodes[0].shared_storage_accessible is True


@pytest.mark.asyncio
async def test_discover_nodes_quorum_unhealthy():
    """
    When /cluster/status returns quorate=0, quorum_healthy must be False.
    Safety Gate Rule 7 will then block migrations.
    """
    provider = _make_provider()
    provider._connected = True

    nodes_resp = MagicMock()
    nodes_resp.status_code = 200
    nodes_resp.json.return_value = {"data": [
        {"node": "pve-node-1", "status": "online", "cpu": 0.1, "maxcpu": 4,
         "mem": 1024 * 1024 * 1024, "maxmem": 8192 * 1024 * 1024,
         "disk": 0, "maxdisk": 0}
    ]}

    cluster_status_resp = MagicMock()
    cluster_status_resp.status_code = 200
    cluster_status_resp.json.return_value = {"data": [
        {"type": "cluster", "quorate": 0, "name": "pve-cluster"},
    ]}

    storage_resp = MagicMock()
    storage_resp.status_code = 200
    storage_resp.json.return_value = {"data": [{"storage": "local", "active": 1}]}

    async def mock_get(url, **kwargs):
        if url.endswith("/nodes"):
            return nodes_resp
        if url.endswith("/cluster/status"):
            return cluster_status_resp
        if "/storage" in url:
            return storage_resp
        raise ValueError(f"Unexpected URL in mock: {url}")

    with patch("httpx.AsyncClient.get", side_effect=mock_get):
        nodes = await provider.discover_nodes()

    assert len(nodes) == 1
    assert nodes[0].quorum_healthy is False


@pytest.mark.asyncio
async def test_discover_nodes_quorum_api_error_fails_closed():
    """
    When /cluster/status raises an exception, quorum_healthy must default to
    False (fail-closed). An unverified quorum state must not become True.
    """
    import httpx as _httpx
    provider = _make_provider()
    provider._connected = True

    nodes_resp = MagicMock()
    nodes_resp.status_code = 200
    nodes_resp.json.return_value = {"data": [
        {"node": "pve-node-1", "status": "online", "cpu": 0.1, "maxcpu": 4,
         "mem": 1024 * 1024 * 1024, "maxmem": 8192 * 1024 * 1024,
         "disk": 0, "maxdisk": 0}
    ]}

    storage_resp = MagicMock()
    storage_resp.status_code = 200
    storage_resp.json.return_value = {"data": [{"storage": "local", "active": 1}]}

    async def mock_get(url, **kwargs):
        if url.endswith("/nodes"):
            return nodes_resp
        if url.endswith("/cluster/status"):
            raise _httpx.ConnectError("Cluster API unreachable")
        if "/storage" in url:
            return storage_resp
        raise ValueError(f"Unexpected URL in mock: {url}")

    with patch("httpx.AsyncClient.get", side_effect=mock_get):
        nodes = await provider.discover_nodes()

    assert len(nodes) == 1
    assert nodes[0].quorum_healthy is False, (
        "quorum_healthy must be False (fail-closed) when cluster/status API errors"
    )


@pytest.mark.asyncio
async def test_discover_nodes_storage_api_error_fails_closed():
    """
    When /nodes/{node}/storage raises an exception, shared_storage_accessible
    must default to False (fail-closed). Unverified storage must not become True.
    """
    import httpx as _httpx
    provider = _make_provider()
    provider._connected = True

    nodes_resp = MagicMock()
    nodes_resp.status_code = 200
    nodes_resp.json.return_value = {"data": [
        {"node": "pve-node-1", "status": "online", "cpu": 0.1, "maxcpu": 4,
         "mem": 1024 * 1024 * 1024, "maxmem": 8192 * 1024 * 1024,
         "disk": 0, "maxdisk": 0}
    ]}

    cluster_status_resp = MagicMock()
    cluster_status_resp.status_code = 200
    cluster_status_resp.json.return_value = {"data": [{"type": "cluster", "quorate": 1}]}

    async def mock_get(url, **kwargs):
        if url.endswith("/nodes"):
            return nodes_resp
        if url.endswith("/cluster/status"):
            return cluster_status_resp
        if "/storage" in url:
            raise _httpx.ConnectError("Storage endpoint unreachable")
        raise ValueError(f"Unexpected URL in mock: {url}")

    with patch("httpx.AsyncClient.get", side_effect=mock_get):
        nodes = await provider.discover_nodes()

    assert len(nodes) == 1
    assert nodes[0].shared_storage_accessible is False, (
        "shared_storage_accessible must be False (fail-closed) when storage API errors"
    )


@pytest.mark.asyncio
async def test_discover_nodes_no_active_storage_pools():
    """
    When /nodes/{node}/storage returns only inactive pools (active=0),
    shared_storage_accessible must be False.
    """
    provider = _make_provider()
    provider._connected = True

    nodes_resp = MagicMock()
    nodes_resp.status_code = 200
    nodes_resp.json.return_value = {"data": [
        {"node": "pve-node-1", "status": "online", "cpu": 0.1, "maxcpu": 4,
         "mem": 1024 * 1024 * 1024, "maxmem": 8192 * 1024 * 1024,
         "disk": 0, "maxdisk": 0}
    ]}

    cluster_status_resp = MagicMock()
    cluster_status_resp.status_code = 200
    cluster_status_resp.json.return_value = {"data": [{"type": "cluster", "quorate": 1}]}

    storage_resp = MagicMock()
    storage_resp.status_code = 200
    storage_resp.json.return_value = {"data": [
        {"storage": "local", "active": 0},
        {"storage": "nfs", "active": 0},
    ]}

    async def mock_get(url, **kwargs):
        if url.endswith("/nodes"):
            return nodes_resp
        if url.endswith("/cluster/status"):
            return cluster_status_resp
        if "/storage" in url:
            return storage_resp
        raise ValueError(f"Unexpected URL in mock: {url}")

    with patch("httpx.AsyncClient.get", side_effect=mock_get):
        nodes = await provider.discover_nodes()

    assert nodes[0].shared_storage_accessible is False


# ---------------------------------------------------------------------------
# 4. Storage Semantics & Precondition Verification Tests (Requirement 1 & 2)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_storage_verification_shared_datastore_both_nodes():
    """
    Scenario 1: Shared datastore available and active on both source and target.
    Shared migration (with_local_disks=False) MUST succeed with status HEALTHY.
    """
    provider = _make_provider()
    provider._connected = True

    vm_config_resp = MagicMock()
    vm_config_resp.status_code = 200
    vm_config_resp.json.return_value = {
        "data": {
            "scsi0": "nfs-shared:101/vm-101-disk-0.raw,size=20G",
            "boot": "order=scsi0"
        }
    }

    source_storage_resp = MagicMock()
    source_storage_resp.status_code = 200
    source_storage_resp.json.return_value = {
        "data": [
            {"storage": "local", "active": 1, "shared": 0},
            {"storage": "nfs-shared", "active": 1, "shared": 1},
        ]
    }

    target_storage_resp = MagicMock()
    target_storage_resp.status_code = 200
    target_storage_resp.json.return_value = {
        "data": [
            {"storage": "local", "active": 1, "shared": 0},
            {"storage": "nfs-shared", "active": 1, "shared": 1},
        ]
    }

    async def mock_get(url, **kwargs):
        if "/qemu/101/config" in url:
            return vm_config_resp
        if "/nodes/pve-node-1/storage" in url:
            return source_storage_resp
        if "/nodes/pve-node-2/storage" in url:
            return target_storage_resp
        raise ValueError(f"Unexpected URL: {url}")

    with patch("httpx.AsyncClient.get", side_effect=mock_get):
        ok, status, details = await provider.verify_migration_storage(
            vm_id="101",
            source_node="pve-node-1",
            target_node="pve-node-2",
            with_local_disks=False
        )

    assert ok is True
    assert status == "HEALTHY"
    assert "nfs-shared" in details


@pytest.mark.asyncio
async def test_storage_verification_datastore_only_on_source():
    """
    Scenario 2: VM datastore is present on source but NOT available on target.
    Shared migration (with_local_disks=False) MUST fail with status UNHEALTHY.
    """
    provider = _make_provider()
    provider._connected = True

    vm_config_resp = MagicMock()
    vm_config_resp.status_code = 200
    vm_config_resp.json.return_value = {
        "data": {
            "scsi0": "local-zfs:vm-101-disk-0,size=20G",
        }
    }

    source_storage_resp = MagicMock()
    source_storage_resp.status_code = 200
    source_storage_resp.json.return_value = {
        "data": [{"storage": "local-zfs", "active": 1, "shared": 0}]
    }

    target_storage_resp = MagicMock()
    target_storage_resp.status_code = 200
    target_storage_resp.json.return_value = {
        "data": [{"storage": "local-lvm", "active": 1, "shared": 0}]
    }

    async def mock_get(url, **kwargs):
        if "/qemu/101/config" in url:
            return vm_config_resp
        if "/nodes/pve-node-1/storage" in url:
            return source_storage_resp
        if "/nodes/pve-node-2/storage" in url:
            return target_storage_resp
        raise ValueError(f"Unexpected URL: {url}")

    with patch("httpx.AsyncClient.get", side_effect=mock_get):
        ok, status, details = await provider.verify_migration_storage(
            vm_id="101",
            source_node="pve-node-1",
            target_node="pve-node-2",
            with_local_disks=False
        )

    assert ok is False
    assert status == "UNHEALTHY"
    assert "missing on target node" in details or "not marked shared" in details or "local-zfs" in details


@pytest.mark.asyncio
async def test_storage_verification_local_disk_migration():
    """
    Scenario 3: Local-disk migration using --with-local-disks 1.
    MUST NOT require shared storage; passes as long as target has active storage.
    """
    provider = _make_provider()
    provider._connected = True

    vm_config_resp = MagicMock()
    vm_config_resp.status_code = 200
    vm_config_resp.json.return_value = {
        "data": {"virtio0": "local-lvm:vm-101-disk-0,size=32G"}
    }

    source_storage_resp = MagicMock()
    source_storage_resp.status_code = 200
    source_storage_resp.json.return_value = {
        "data": [{"storage": "local-lvm", "active": 1, "shared": 0}]
    }

    target_storage_resp = MagicMock()
    target_storage_resp.status_code = 200
    target_storage_resp.json.return_value = {
        "data": [{"storage": "local-zfs", "active": 1, "shared": 0}]
    }

    async def mock_get(url, **kwargs):
        if "/qemu/101/config" in url:
            return vm_config_resp
        if "/nodes/pve-node-1/storage" in url:
            return source_storage_resp
        if "/nodes/pve-node-2/storage" in url:
            return target_storage_resp
        raise ValueError(f"Unexpected URL: {url}")

    with patch("httpx.AsyncClient.get", side_effect=mock_get):
        ok, status, details = await provider.verify_migration_storage(
            vm_id="101",
            source_node="pve-node-1",
            target_node="pve-node-2",
            with_local_disks=True  # Local-disk migration path
        )

    assert ok is True
    assert status == "HEALTHY"
    assert "with-local-disks" in details


@pytest.mark.asyncio
async def test_storage_verification_api_unavailable_fails_closed_unknown():
    """
    Scenario 4: Storage API is unreachable or returns error.
    MUST fail closed with status UNKNOWN without inventing/guessing state.
    """
    import httpx
    provider = _make_provider()
    provider._connected = True

    with patch("httpx.AsyncClient.get", side_effect=httpx.ConnectError("Storage daemon down")):
        ok, status, details = await provider.verify_migration_storage(
            vm_id="101",
            source_node="pve-node-1",
            target_node="pve-node-2",
            with_local_disks=True
        )

    assert ok is False
    assert status == "UNKNOWN"
    assert "unavailable" in details.lower() or "down" in details.lower()


@pytest.mark.asyncio
async def test_storage_verification_vm_datastore_cannot_be_determined():
    """
    Scenario 5: VM config endpoint returns HTTP 500 or error.
    MUST fail closed with status UNKNOWN and explicit explanation.
    """
    provider = _make_provider()
    provider._connected = True

    target_storage_resp = MagicMock()
    target_storage_resp.status_code = 200
    target_storage_resp.json.return_value = {"data": [{"storage": "local", "active": 1}]}

    source_storage_resp = MagicMock()
    source_storage_resp.status_code = 200
    source_storage_resp.json.return_value = {"data": [{"storage": "local", "active": 1}]}

    vm_config_resp = MagicMock()
    vm_config_resp.status_code = 500
    vm_config_resp.text = "Internal error reading vm config"

    async def mock_get(url, **kwargs):
        if "/nodes/pve-node-2/storage" in url:
            return target_storage_resp
        if "/nodes/pve-node-1/storage" in url:
            return source_storage_resp
        if "/qemu/101/config" in url:
            return vm_config_resp
        raise ValueError(f"Unexpected URL: {url}")

    with patch("httpx.AsyncClient.get", side_effect=mock_get):
        ok, status, details = await provider.verify_migration_storage(
            vm_id="101",
            source_node="pve-node-1",
            target_node="pve-node-2",
            with_local_disks=False
        )

    assert ok is False
    assert status == "UNKNOWN"
    assert "cannot be determined" in details.lower() or "500" in details


# ---------------------------------------------------------------------------
# 5. UPID Robust Parsing & Context-Preserving Tests (Requirement 3 & 4)
# ---------------------------------------------------------------------------

def test_parse_proxmox_upid_valid_format():
    upid = "UPID:pve-node-1:0012A4B0:0034CD50:66EAE940:qmigrate:105:vmotion-api@pve!automation:"
    parsed = parse_proxmox_upid(upid)
    assert parsed["node"] == "pve-node-1"
    assert parsed["pid"] == "0012A4B0"
    assert parsed["type"] == "qmigrate"
    assert parsed["id"] == "105"
    assert parsed["user"] == "vmotion-api@pve!automation"


def test_parse_proxmox_upid_malformed_and_invalid():
    assert parse_proxmox_upid("") == {}
    assert parse_proxmox_upid("NOT_A_UPID:123") == {}
    assert parse_proxmox_upid("UPID:short:parts") == {}
    assert parse_proxmox_upid(None) == {}


@pytest.mark.asyncio
async def test_monitor_migration_task_uses_known_context_without_brittle_parsing():
    """
    execute_migration() populates _task_context_map with exact VM ID, source_node,
    target_node, and plan_id. monitor_migration_task() retrieves these directly
    from VMotion AI context without relying on brittle positional string splitting.
    """
    provider = _make_provider()
    provider._connected = True

    upid = "UPID:pve-node-1:0012A4B0:0034CD50:66EAE940:qmigrate:custom-workload-id:user:"
    plan = MigrationPlan(
        plan_id="plan-custom-888",
        vm_id="custom-vm-99",
        source_node="pve-node-1",
        target_node="pve-node-target-alpha",
        reason="Load balance",
        created_at=time.time(),
        with_local_disks=True
    )

    mock_migrate_resp = MagicMock()
    mock_migrate_resp.status_code = 200
    mock_migrate_resp.json.return_value = {"data": upid}

    mock_status_resp = MagicMock()
    mock_status_resp.status_code = 200
    mock_status_resp.json.return_value = {"data": {"status": "running", "exitstatus": None}}

    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_migrate_resp)):
        dispatched_upid = await provider.execute_migration(plan)

    assert dispatched_upid == upid
    assert dispatched_upid in provider._task_context_map
    ctx = provider._task_context_map[dispatched_upid]
    assert ctx["target_node"] == "pve-node-target-alpha"
    assert ctx["vm_id"] == "custom-vm-99"

    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=mock_status_resp)):
        status = await provider.monitor_migration_task(upid)

    assert status.target_node == "pve-node-target-alpha"
    assert status.vm_id == "custom-vm-99"
    assert status.plan_id == "plan-custom-888"
    assert status.source_node == "pve-node-1"


@pytest.mark.asyncio
async def test_verify_placement_detects_source_node_conflict():
    """
    verify_placement() must fail if the VM is still reported on the source
    or any non-target node in the cluster active workload inventory.
    """
    provider = _make_provider()
    provider._connected = True

    from app.providers.base import ClusterState, NodeTelemetry

    conflict_state = ClusterState(
        is_live=True,
        connected=True,
        provider_name="proxmox",
        timestamp=time.time(),
        nodes={
            "pve-node-1": NodeTelemetry(id="pve-node-1", name="pve1", active_vms=["vm-101"]),
            "pve-node-2": NodeTelemetry(id="pve-node-2", name="pve2", active_vms=["vm-101"]),
        },
        vms={
            "vm-101": _make_vm("vm-101", node_id="pve-node-2")
        }
    )

    with patch.object(provider, "collect_telemetry", new=AsyncMock(return_value=conflict_state)):
        ok, msg = await provider.verify_placement("vm-101", "pve-node-2")

    assert ok is False
    assert "Placement conflict" in msg
    assert "pve-node-1" in msg


@pytest.mark.asyncio
async def test_api_recommendation_safety_eval_matches_proposal():
    """
    In GET /api/ai/recommendation logic, the outer safety_evaluation must exactly
    match proposal.safety_evaluation, particularly on local-disk-only clusters.
    """
    provider = _make_provider()
    from app.engine.base import Recommendation
    from app.planner.planner import MigrationManager
    from app.providers.base import ClusterState, NodeTelemetry
    from app.safety.gate import deterministic_safety_gate

    cluster = ClusterState(
        is_live=True,
        connected=True,
        provider_name="proxmox",
        timestamp=time.time(),
        nodes={
            "pve-1": NodeTelemetry(id="pve-1", name="pve1", status="online", shared_storage_accessible=False, storage_status="HEALTHY", quorum_healthy=True, active_vms=["vm-101"]),
            "pve-2": NodeTelemetry(id="pve-2", name="pve2", status="online", shared_storage_accessible=False, storage_status="HEALTHY", quorum_healthy=True, active_vms=[]),
        },
        vms={
            "vm-101": _make_vm("vm-101", node_id="pve-1")
        }
    )

    rec = Recommendation(
        action_type="MIGRATE",
        action_index=1,
        vm_id="vm-101",
        vm_name="vm-101",
        source_node="pve-1",
        target_node="pve-2",
        reason="Test local-disk rebalance",
        engine_type="PPO_POLICY",
        confidence_score=0.95
    )

    mgr = MigrationManager(provider=provider, safety_gate=deterministic_safety_gate)
    prop = mgr.evaluate_and_propose(rec, cluster)
    assert prop is not None
    assert prop.with_local_disks is True
    assert prop.safety_evaluation.passed is True


