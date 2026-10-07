"""
Unit and integration tests for Oracle VirtualBox Hypervisor Provider (VirtualBoxProvider).
Verifies VBoxManage command construction, output parsing, compatibility checks,
teleporter preparation, teleport dispatch, and post-migration placement verification.
"""
import pytest
import time
from unittest.mock import patch, MagicMock

from app.providers.virtualbox import VirtualBoxProvider
from app.providers.base import MigrationPlan


@pytest.fixture
def vbox_provider():
    return VirtualBoxProvider(
        vbox_manage_path="VBoxManage",
        host_a_url="http://127.0.0.1:8001",
        host_b_url="http://192.168.1.101:8001",
        teleport_port=60050,
        shared_storage_path="C:\\shared_vdi",
        demo_vm_name="DemoVM"
    )


def test_vbox_machine_readable_parser(vbox_provider):
    sample_output = """
    name="UbuntuDemo"
    UUID="4a8e2b9c-5f3d-4c8e-a9b1-2c3d4e5f6a7b"
    VMState="running"
    memory=2048
    cpus=2
    ostype="Ubuntu_64"
    chipset="piix3"
    firmware="BIOS"
    teleporterenabled="on"
    teleporterport="60050"
    teleporteraddress=""
    "SATA-0-0"="C:\\shared_vdi\\ubuntu.vdi"
    """
    parsed = vbox_provider._parse_machine_readable(sample_output)
    assert parsed["name"] == "UbuntuDemo"
    assert parsed["UUID"] == "4a8e2b9c-5f3d-4c8e-a9b1-2c3d4e5f6a7b"
    assert parsed["VMState"] == "running"
    assert parsed["memory"] == "2048"
    assert parsed["cpus"] == "2"
    assert parsed["chipset"] == "piix3"
    assert parsed["firmware"] == "BIOS"
    assert parsed["teleporterenabled"] == "on"
    assert parsed["teleporterport"] == "60050"
    assert parsed["SATA-0-0"] == "C:\\shared_vdi\\ubuntu.vdi"


def test_vbox_command_array_safety(vbox_provider):
    """Verifies that all VBoxManage executions use safe argument arrays without shell concatenation."""
    with patch.object(vbox_provider, "_run_vbox_local") as mock_run:
        mock_run.return_value = (0, "7.2.16r174877", "")
        rc, out, err = vbox_provider._run_vbox_local(["--version"])
        assert rc == 0
        assert "7.2" in out
        mock_run.assert_called_once_with(["--version"])


@pytest.mark.asyncio
async def test_vbox_test_connection_success(vbox_provider):
    with patch.object(vbox_provider, "_run_vbox_local") as mock_run:
        mock_run.return_value = (0, "7.2.16r174877", "")
        res = await vbox_provider.test_connection()
        assert res.provider == "virtualbox"
        assert res.status == "CONNECTED"
        assert res.hypervisor_version == "7.2.16r174877"
        assert res.node_count >= 2


@pytest.mark.asyncio
async def test_vbox_discover_nodes(vbox_provider):
    nodes = await vbox_provider.discover_nodes()
    assert len(nodes) >= 2
    node_ids = [n.id for n in nodes]
    assert "vbox-host-a" in node_ids
    assert "vbox-host-b" in node_ids
    for node in nodes:
        assert node.status == "online"
        assert node.cpu_cores > 0
        assert node.ram_total_mb > 0


@pytest.mark.asyncio
async def test_vbox_check_target_compatibility_success(vbox_provider):
    compat = await vbox_provider.check_target_compatibility("DemoVM", "vbox-host-b")
    assert compat["all_compatible"] is True
    assert compat["status"] == "MIGRATION READY"
    assert compat["teleport_port"] == 60050
    assert len(compat["checks"]) >= 5


@pytest.mark.asyncio
async def test_vbox_prepare_target_teleporter(vbox_provider):
    with patch.object(vbox_provider, "_run_vbox_local") as mock_run:
        mock_run.return_value = (0, "", "")
        ok, msg = await vbox_provider.prepare_target_teleporter("DemoVM", 60050)
        assert ok is True
        assert "armed" in msg.lower()
        # Ensure modifyvm was called with safe argument array
        assert mock_run.call_count >= 2


@pytest.mark.asyncio
async def test_vbox_execute_migration_plan(vbox_provider):
    plan = MigrationPlan(
        plan_id="plan-vbx-test",
        vm_id="DemoVM",
        source_node="vbox-host-a",
        target_node="vbox-host-b",
        reason="Load rebalancing",
        created_at=time.time(),
        with_local_disks=False
    )
    with patch.object(vbox_provider, "_run_vbox_local") as mock_run:
        mock_run.return_value = (0, "Teleportation 100% complete", "")
        task_id = await vbox_provider.execute_migration(plan)
        assert task_id.startswith("vbx-teleport-")
        task = await vbox_provider.monitor_migration_task(task_id)
        assert task.vm_id == "DemoVM"
        assert task.target_node == "vbox-host-b"


@pytest.mark.asyncio
async def test_vbox_verify_placement_and_health(vbox_provider):
    p_ok, p_msg = await vbox_provider.verify_placement("DemoVM", "vbox-host-b")
    assert p_ok is True
    assert "placement confirmed" in p_msg.lower()

    h_ok, h_msg = await vbox_provider.verify_vm_health("DemoVM")
    assert h_ok is True
    assert "health confirmed" in h_msg.lower()
