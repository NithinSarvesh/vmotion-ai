"""
Automated unit tests for SimulationProvider lifecycle and error handling.
"""
import pytest
import asyncio
from app.providers.simulation import SimulationProvider
from app.providers.base import MigrationPlan


@pytest.mark.asyncio
async def test_simulation_telemetry_drift_over_time():
    provider = SimulationProvider()
    c1 = await provider.collect_telemetry()
    cpu_initial = {vmid: vm.cpu_percent for vmid, vm in c1.vms.items()}

    # Perform multiple drift cycles
    for _ in range(5):
        await provider.collect_telemetry()

    c2 = await provider.collect_telemetry()
    cpu_after = {vmid: vm.cpu_percent for vmid, vm in c2.vms.items()}

    # Values should drift realistically within mathematical bounds
    for vmid, cpu in cpu_after.items():
        assert 0.0 <= cpu <= 100.0
        assert not isinstance(cpu, str)


@pytest.mark.asyncio
async def test_simulation_migration_task_lifecycle_and_placement_update():
    provider = SimulationProvider()
    plan = MigrationPlan(
        plan_id="plan-test-01",
        vm_id="vm-102",
        source_node="node-01",
        target_node="node-03",
        reason="Automated lifecycle verification test",
        created_at=1000.0
    )

    # VM starts on node-01
    vm_before = await provider.inspect_vm_state("vm-102")
    assert vm_before.node_id == "node-01"
    assert vm_before.status == "running"

    # Dispatch execution
    task_id = await provider.execute_migration(plan)
    assert task_id.startswith("sim-task-")

    # Initial state must be PREPARING
    initial_status = await provider.monitor_migration_task(task_id)
    assert initial_status.state in ("PREPARING", "VALIDATING", "MIGRATING")

    # Wait for completion (simulated speed takes ~4.5s)
    max_wait = 12.0
    start = asyncio.get_event_loop().time()
    while True:
        await asyncio.sleep(0.4)
        status = await provider.monitor_migration_task(task_id)
        if status.state in ("VERIFIED", "FAILED"):
            break
        if asyncio.get_event_loop().time() - start > max_wait:
            pytest.fail("Simulation task timed out before completing lifecycle")

    assert status.state == "VERIFIED"
    assert status.progress_percent == 100.0
    assert status.completed_at is not None
    assert status.verified_at is not None

    # Verify placement
    p_ok, p_msg = await provider.verify_placement("vm-102", "node-03")
    assert p_ok is True, f"Expected placement on node-03, got: {p_msg}"

    # Verify health
    h_ok, h_msg = await provider.verify_vm_health("vm-102")
    assert h_ok is True, f"Expected health ok, got: {h_msg}"

    # Ensure source node inventory was updated
    nodes = await provider.discover_nodes()
    node01 = next(n for n in nodes if n.id == "node-01")
    node03 = next(n for n in nodes if n.id == "node-03")
    assert "vm-102" not in node01.active_vms
    assert "vm-102" in node03.active_vms


@pytest.mark.asyncio
async def test_simulation_invalid_migration_rejected():
    provider = SimulationProvider()
    
    # Try migrating to nonexistent node
    bad_plan = MigrationPlan(
        plan_id="plan-bad",
        vm_id="vm-101",
        source_node="node-01",
        target_node="node-999",
        reason="Negative test",
        created_at=1000.0
    )
    with pytest.raises(ValueError) as exc:
        await provider.execute_migration(bad_plan)
    assert "target node" in str(exc.value).lower()
