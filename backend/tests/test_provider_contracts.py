"""
Automated Provider Semantic Contract Tests for VMotion AI.
Verifies contract adherence for SimulationProvider, ProxmoxVEProvider, and LibvirtKVMProvider:
- Schema conformity for ClusterState, NodeTelemetry, VMTelemetry, and ProviderConnectionResult
- Graceful error handling for missing/invalid credentials and unreachable endpoints
- Truthful disconnected status without silent fallback
- Validation and rejection of malformed migration requests
"""
import pytest
import time
from unittest.mock import AsyncMock, patch, MagicMock

from app.providers.base import (
    BaseVirtualizationProvider,
    ClusterState,
    NodeTelemetry,
    VMTelemetry,
    MigrationPlan,
    ProviderConnectionResult
)
from app.providers.simulation import SimulationProvider
from app.providers.proxmox import ProxmoxVEProvider
from app.providers.libvirt import LibvirtKVMProvider


# ---------------------------------------------------------------------------
# 1. SIMULATION PROVIDER CONTRACT TESTS
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_simulation_provider_schema_conformity():
    provider = SimulationProvider()
    assert isinstance(provider, BaseVirtualizationProvider)

    cluster = await provider.get_cluster_state()
    assert isinstance(cluster, ClusterState)
    assert cluster.is_live is False, "Simulation must declare is_live=False"
    assert cluster.provider_name == "simulation"
    assert cluster.connected is True
    assert len(cluster.nodes) >= 3
    assert len(cluster.vms) >= 6

    for node_id, node in cluster.nodes.items():
        assert isinstance(node, NodeTelemetry)
        assert node.id == node_id
        assert 0.0 <= node.cpu_percent <= 100.0
        assert 0.0 <= node.ram_percent <= 100.0
        assert node.ram_total_mb > 0.0
        assert node.status in ("online", "offline", "degraded")

    for vm_id, vm in cluster.vms.items():
        assert isinstance(vm, VMTelemetry)
        assert vm.vmid == vm_id
        assert vm.status in ("running", "stopped", "paused", "migrating")
        assert vm.node_id in cluster.nodes


@pytest.mark.asyncio
async def test_simulation_provider_disconnected_truthfulness():
    provider = SimulationProvider()
    await provider.disconnect()
    assert await provider.is_connected() is False

    cluster = await provider.get_cluster_state()
    assert cluster.connected is False
    assert cluster.is_live is False
    assert cluster.error_message is not None
    assert "disconnected" in cluster.error_message.lower()

    # Reconnect
    await provider.connect()
    assert await provider.is_connected() is True


@pytest.mark.asyncio
async def test_simulation_provider_migration_validation():
    provider = SimulationProvider()

    # Valid migration: vm-101 (on node-01) -> node-02
    ok, msg = await provider.validate_migration("vm-101", "node-02")
    assert ok is True

    # Invalid: Same node
    ok, msg = await provider.validate_migration("vm-101", "node-01")
    assert ok is False
    assert "already hosted" in msg.lower()

    # Invalid: Nonexistent VM
    ok, msg = await provider.validate_migration("vm-9999", "node-02")
    assert ok is False
    assert "not found" in msg.lower()

    # Invalid: Nonexistent target node
    ok, msg = await provider.validate_migration("vm-101", "node-nonexistent")
    assert ok is False
    assert "target node" in msg.lower()


# ---------------------------------------------------------------------------
# 2. PROXMOX VE PROVIDER CONTRACT TESTS
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_proxmox_provider_unconfigured_diagnostics():
    """Proxmox provider returns UNAVAILABLE when credentials or endpoint are missing."""
    pve = ProxmoxVEProvider(endpoint="", token_secret="")
    res = await pve.test_connection()

    assert isinstance(res, ProviderConnectionResult)
    assert res.provider == "proxmox"
    assert res.status == "UNAVAILABLE"
    assert "endpoint" in res.message.lower()

    pve_no_secret = ProxmoxVEProvider(endpoint="https://192.168.1.50:8006/api2/json", token_secret="")
    res2 = await pve_no_secret.test_connection()
    assert res2.status == "UNAVAILABLE"
    assert "token secret" in res2.message.lower()


@pytest.mark.asyncio
async def test_proxmox_provider_disconnected_truthfulness():
    """
    When Proxmox cluster is unreachable or disconnected, provider truthfully declares
    connected=False and is_live=True. It MUST NEVER silently fall back to simulation.
    """
    import httpx
    pve = ProxmoxVEProvider(
        endpoint="https://192.0.2.1:8006/api2/json",
        token_secret="test-token"
    )
    with patch("httpx.AsyncClient.get", side_effect=httpx.ConnectError("Network unreachable")):
        cluster = await pve.get_cluster_state()

        assert isinstance(cluster, ClusterState)
        assert cluster.connected is False
        assert cluster.is_live is True, "Proxmox provider must always declare is_live=True"
        assert cluster.provider_name == "proxmox"
        assert cluster.error_message is not None
        assert len(cluster.nodes) == 0
        assert len(cluster.vms) == 0


@pytest.mark.asyncio
async def test_proxmox_provider_validation_rejections():
    import httpx
    pve = ProxmoxVEProvider(
        endpoint="https://192.0.2.1:8006/api2/json",
        token_secret="test-token"
    )
    with patch("httpx.AsyncClient.get", side_effect=httpx.ConnectError("Network unreachable")):
        # Validate migration on disconnected provider returns False with error
        ok, msg = await pve.validate_migration("vm-101", "pve-node-2")
        assert ok is False
        assert "disconnected" in msg.lower() or "cannot validate" in msg.lower()


@pytest.mark.asyncio
async def test_proxmox_provider_test_connection_auth_error_handling():
    """Simulate a 401 Unauthorized response from Proxmox REST API."""
    pve = ProxmoxVEProvider(
        endpoint="https://10.0.0.1:8006/api2/json",
        user="root@pam",
        token_id="vmotion",
        token_secret="invalid-secret"
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = "permission check failed"

    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=mock_resp)):
        res = await pve.test_connection()
        assert res.status == "AUTHENTICATION_ERROR"
        assert "401" in res.message or "authentication" in res.message.lower()


# ---------------------------------------------------------------------------
# 3. LIBVIRT / KVM PROVIDER CONTRACT TESTS
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_libvirt_provider_unconfigured_diagnostics():
    libvirt_prov = LibvirtKVMProvider(uri="")
    res = await libvirt_prov.test_connection()

    assert isinstance(res, ProviderConnectionResult)
    assert res.provider == "libvirt"
    assert res.status == "UNAVAILABLE"
    assert "not configured" in res.message.lower()


@pytest.mark.asyncio
async def test_libvirt_provider_disconnected_truthfulness():
    """
    When Libvirt URI is unreachable or libvirt is not connected, provider declares
    connected=False and is_live=True. NEVER silently falls back to simulation.
    """
    libvirt_prov = LibvirtKVMProvider(uri="qemu+ssh://nonexistent.local/system")
    cluster = await libvirt_prov.get_cluster_state()

    assert isinstance(cluster, ClusterState)
    assert cluster.connected is False
    assert cluster.is_live is True, "Libvirt provider must declare is_live=True"
    assert cluster.provider_name == "libvirt"
    assert cluster.error_message is not None


@pytest.mark.asyncio
async def test_libvirt_provider_validation_rejections():
    libvirt_prov = LibvirtKVMProvider(uri="qemu+ssh://nonexistent.local/system")
    ok, msg = await libvirt_prov.validate_migration("vm-101", "node-02")
    assert ok is False
    assert "not active" in msg.lower() or "disconnected" in msg.lower() or "cannot validate" in msg.lower()
