"""
Automated unit tests for Virtualization Provider Abstraction and SimulationProvider contract.
"""
import pytest
from app.providers.simulation import SimulationProvider
from app.providers.base import BaseVirtualizationProvider, ClusterState, MigrationPlan


@pytest.mark.asyncio
async def test_provider_contract_adherence():
    provider = SimulationProvider()
    assert isinstance(provider, BaseVirtualizationProvider)

    # 1. Connection lifecycle
    assert await provider.is_connected() is True
    await provider.disconnect()
    assert await provider.is_connected() is False
    await provider.connect()
    assert await provider.is_connected() is True

    # 2. Node & VM discovery
    nodes = await provider.discover_nodes()
    assert len(nodes) >= 3, "Expected at least 3 compute nodes"
    for node in nodes:
        assert node.id in ("node-01", "node-02", "node-03")
        assert 0.0 <= node.cpu_percent <= 100.0
        assert node.ram_total_mb > 0.0

    vms = await provider.discover_vms()
    assert len(vms) >= 6, "Expected at least 6 workloads"
    for vm in vms:
        assert vm.status in ("running", "stopped", "paused", "migrating")
        assert vm.node_id in [n.id for n in nodes]

    # 3. Telemetry collection
    cluster = await provider.collect_telemetry()
    assert isinstance(cluster, ClusterState)
    assert cluster.is_live is False, "Simulation provider must declare is_live=False"
    assert cluster.provider_name == "simulation"
    assert len(cluster.nodes) == len(nodes)
    assert len(cluster.vms) == len(vms)

    # 4. VM state inspection
    vm_state = await provider.inspect_vm_state("vm-101")
    assert vm_state is not None
    assert vm_state.vmid == "vm-101"
    assert vm_state.name == "core-db-primary"

    missing_vm = await provider.inspect_vm_state("vm-nonexistent")
    assert missing_vm is None

    # 5. Migration planning
    plan = await provider.plan_migration("vm-101", "node-02", "Load rebalance test")
    assert isinstance(plan, MigrationPlan)
    assert plan.vm_id == "vm-101"
    assert plan.source_node == "node-01"
    assert plan.target_node == "node-02"

    # 6. Pre-migration validation
    val_ok, msg = await provider.validate_migration("vm-101", "node-02")
    assert val_ok is True

    # Invalid: same node
    same_ok, same_msg = await provider.validate_migration("vm-101", "node-01")
    assert same_ok is False
    assert "already hosted" in same_msg.lower()
